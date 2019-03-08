"""AVD Launch test.

Verify an AVD can be created with avdmanager command line interface and then launched.

usage: create_and_launch_avd.py [-h] [-t TIMEOUT_IN_SECONDS] --avd AVD
                                [--exec EMULATOR_EXEC]
"""
import os
import sys
import time
import util
import psutil
import logging
import unittest
import threading
import subprocess
import multiprocessing.pool
from subprocess import PIPE

import emu_test
import emu_test.utils.path_utils as path_utils
from emu_test.utils import emu_argparser
from emu_test.utils.emu_testcase import EmuBaseTestCase, AVDConfig

log = logging.getLogger('launch_avd_no_window')

class CreateAndLaunchAVDTest(EmuBaseTestCase):
    """Tests for creating an AVD via AVD Manager command line interface and launching it."""

    def kill_emulator(self):
        self.m_logger.debug('First try - quit emulator by adb emu kill')
        adb_binary = path_utils.get_adb_binary()
        kill_proc = psutil.Popen([adb_binary, "emu", "kill"]).communicate()
        # check emulator process is terminated
        result = self.term_check(timeout=5)
        if not result:
            self.m_logger.info('Second try - quit emulator by psutil')
            self.kill_proc_by_name(["emulator", "qemu-system"])
            result = self.term_check(timeout=10)
            self.m_logger.info("term_check after psutil.kill - %s" % result)
        return result

    def tearDown(self):
        result = self.kill_emulator()
        self.m_logger.info("Remove AVD inside of tear down")
        # avd should be found $HOME/.android/avd/
        avd_dir = os.path.join(os.path.expanduser('~'), '.android', 'avd')
        try:
            if result and self.start_proc:
                self.start_proc.wait()
            time.sleep(1)
            self.kill_proc_by_name(["crash-service", "adb"])
            os.remove(os.path.join(avd_dir, '%s.ini' % self.avd_config.name()))
            shutil.rmtree(os.path.join(avd_dir, '%s.avd' % self.avd_config.name()), ignore_errors=True)
        except Exception, e:
            self.m_logger.error("Error in cleanup - %r" % e)
            pass

    def launch_emu(self, avd, emu_args, emu_log_stream, additional_args=None):
       """Launch given avd and return immediately"""
       log.debug('call Launching AVD, ...: %s' % str(avd))
       exec_path = emu_args.emulator_exec
       launch_cmd = [exec_path, "-avd", str(avd), "-verbose", "-show-kernel"]
       if additional_args:
           launch_cmd.extend(additional_args)

       if "emu-master-dev" in exec_path:
           launch_cmd += ["-skip-adb-auth"]

       log.info('Launching AVD, cmd: %s' % ' '.join(launch_cmd))
       start_proc = subprocess.Popen(launch_cmd,
                                     stderr=subprocess.STDOUT,
                                     stdout=emu_log_stream)
       log.info('done Launching AVD, cmd: %s' % ' '.join(launch_cmd))

       if start_proc.poll():
           raise LaunchError(str(avd))
       log.debug('return Launching AVD, ...: %s' % str(avd))
       return start_proc

    def run_with_timeout(self, cmd, timeout):
       """Run command with specified timeout.
       Args:
         cmd     - Required  : command to run
         timeout - Required  : timeout (in seconds)
       Returns:
         Tuple of form (returncode, output, err), where:
         * returncode is the exit code of the command
         * output is the stdout output of the command, collected into a string
         * err is the stderr output of the command, collected into a string
       """
       vars = {'output': "",
               'err': "",
               'process': None}

       def run_cmd():
           vars['process'] = subprocess.Popen(cmd, stdout=PIPE, stderr=PIPE)
           (vars['output'], vars['err']) = vars['process'].communicate()

       thread = threading.Thread(target=run_cmd)
       thread.start()

       thread.join(timeout)
       if thread.is_alive():
           log.debug('cmd %s timeout, force terminate' % ' '.join(cmd))
           try:
               vars['process'].terminate()
           except Exception as e:
               log.error('exception terminating adb getprop process: %r' % e)
       thread.join(timeout)
       return vars['process'].returncode, vars['output'], vars['err']

    def launch_emu_and_wait(self, avd, emu_args, emu_log_stream, additional_args=None):
       """Launch given avd and wait for boot completion, return boot time"""
       adb_binary = path_utils.get_adb_binary()
       self.run_with_timeout([adb_binary, "kill-server"], 20)
       self.run_with_timeout([adb_binary, "start-server"], 20)
       pool = multiprocessing.pool.ThreadPool(processes = 1)
       launcher_emu = pool.apply_async(self.launch_emu, [avd, emu_args, emu_log_stream, additional_args])
       start_time = time.time()
       completed = "0"
       real_time_out = emu_args.timeout_in_seconds;
       if 'swiftshader' in str(avd):
           real_time_out = real_time_out + emu_args.timeout_in_seconds
       if 'arm' in str(avd):
           real_time_out = real_time_out + emu_args.timeout_in_seconds;
       if 'mips' in str(avd):
           real_time_out = real_time_out + emu_args.timeout_in_seconds;

       # Initialize these to None, in case try block fails.
       output = None
       err = None

       while time.time()-start_time < real_time_out:
           cmd = [adb_binary, "shell", "getprop", "sys.boot_completed"]
           if launcher_emu.ready():
               emu_proc = launcher_emu.get()
               if emu_proc.poll():
                   msg = 'Emulator process terminated with exit code {} before boot completed.'
                   raise LaunchError(msg.format(emu_proc.returncode))

           try:
               (exit_code, output, err) = self.run_with_timeout(cmd, 10)
           except Exception as e:
               log.error('exception run_with_timeout adb getprop: %r' % e)
               continue
           if exit_code is 0:
               completed = output.strip()
           if completed == "1":
               log.info('AVD %s is fully booted' % str(avd))
               break
           time.sleep(1)
       if completed is not "1":
           log.debug('command output - %s %s' % (output,err))
           log.error('AVD %s didn\'t boot up within %s seconds' % (avd,real_time_out))
           raise TimeoutError(avd, real_time_out)
       boot_time = time.time() - start_time
       log.debug('AVD %s, boot time is %s' % (avd, boot_time))
       emu_proc = launcher_emu.get(10)
       if util.get_connected_devices():
           success = True
       else:
           success = False
       emu_proc.terminate()
       return success

    def launch_avd(self, avd_config):
        """Launch AVD with given config."""
        self.avd_config = avd_config
        self.assertEqual(self.create_avd(avd_config), 0)
        test_name  = self.id().rsplit('.', 1)[-1]
        emu_log_path = os.path.join(emu_argparser.emu_args.session_dir,
                                    emu_argparser.emu_args.test_dir,
                                    '%s_verbose.txt' % test_name)

        args = ['-port', '5554', '-wipe-data', '-no-boot-anim', '-no-snapshot',
                '-no-window', '-qemu', '-enable-kvm']
        with open(emu_log_path, 'wb') as emu_log:
            return self.launch_emu_and_wait(avd_config,
                                            emu_argparser.emu_args,
                                            emu_log,
                                            additional_args = args)

    def create_avd(self, avd_config):
        """
        Create AVD, overwriting old AVD if it exists.

        This method overrides the implementation in `EmuBaseTestCase`
        to use the `avdmanager` command-line interface.

        :param avd_config: Configuration representing the AVD we wish to create.
        :return: Return code of the AVD create process.
        """
        def try_create_with_sdk():
            """
            Create AVD using the avdmanager command line tool.

            :return: Return code of android command line tool.
            """
            avdmanager_binary = path_utils.get_avdmanager_binary()
            avd_abi = '%s/%s' % (avd_config.tag, avd_config.abi)
            api_target = avd_config.api
            avd_target = ';'.join(['system-images',
                                   'android-%s' % api_target,
                                   avd_config.tag,
                                   avd_config.abi])
            create_cmd = [avdmanager_binary, 'create', 'avd', '--force',
                          '--name', avd_name,
                          '-k', avd_target,
                          '-d', avd_config.device,
                          '-c', '20M']
            self.m_logger.info('Create AVD, cmd: %s' % ' '.join(create_cmd))
            avd_proc = psutil.Popen(create_cmd, stdout=PIPE, stdin=PIPE, stderr=PIPE)
            stdout, stderr = avd_proc.communicate(input='\n')
            self.simple_logger.debug(stdout)
            self.simple_logger.debug(stderr)
            if 'Error' in stderr:
                return -1
            return avd_proc.poll()

        # Function execution starts here.
        avd_name = str(avd_config)
        self.m_logger.info('Attempt to create AVD %s.' % avd_name)
        ret = try_create_with_sdk()
        if ret == 1:
            # If we failed to create the AVD with a return of 1, we may be missing the required image.
            # Try to download it.
            api = avd_config.api
            self.install_sdk_package('platforms;android-%s' % api)
            if 'google_apis_playstore' in avd_config.tag:
                self.install_sdk_package('system-images;android-%s;google_apis_playstore;%s'
                                         % (api, avd_config.abi))
            elif 'google' in avd_config.tag:
                self.install_sdk_package('add-ons;addon-google_apis-google-%s' % api)
                self.install_sdk_package('system-images;android-%s;google_apis;%s'
                                         % (api, avd_config.abi))
            elif 'wear' in avd_config.tag:
                self.install_sdk_package('system-images;android-%s;android-wear;%s'
                                         % (api, avd_config.abi))
            elif 'tv' in avd_config.tag:
                self.install_sdk_package('system-images;android-%s;android-tv;%s'
                                         % (api, avd_config.abi))
            elif 'car' in avd_config.tag:
                self.install_sdk_package('system-images;android-%s;android-car;%s'
                                         % (api, avd_config.abi))
            elif 'chromeos' in avd_config.tag:
                self.update_chromeos(avd_config.alt_version)
            else:
                self.install_sdk_package('system-images;android-%s;default;%s'
                                         % (api, avd_config.abi))
            self.m_logger.info('Attempt number 2 at AVD creation now that package has been attempted to be installed.')
            ret = try_create_with_sdk()
        # last step, create config.ini
        if ret != 0:
            self.m_logger.error('Failed to create AVD, even after attempting package install.')
        return ret

if emu_argparser.emu_args.config_file is None:
    sys.exit(-1)
else:
    emu_test.utils.emu_testcase.create_test_case_from_file(
        'create_and_launch_avd', CreateAndLaunchAVDTest, CreateAndLaunchAVDTest.launch_avd)


if __name__ == '__main__':
    os.environ['SHELL'] = '/bin/bash'
    emu_argparser.emu_args = emu_argparser.get_parser().parse_args()
    log.info(emu_argparser.emu_args)
    sys.argv[1:] = emu_argparser.emu_args.unittest_args
    unittest.main()
