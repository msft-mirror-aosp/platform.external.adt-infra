"""Derived class of unittest.TestCase which has contains console and file handler

   This class is intented to be a base class of specific test case classes
"""

import os
import re
import sys
import unittest
import logging
import time
import psutil
import csv
import platform
import threading
import shutil
import ConfigParser
from emu_error import *
import emu_test.utils.emu_argparser as emu_argparser
from subprocess import PIPE, STDOUT
from collections import namedtuple

class AVDConfig(namedtuple('AVDConfig', 'api, tag, abi, device, ram, gpu, classic, port, cts, ori')):
    __slots__ = ()
    def __str__(self):
        device = self.device if self.device != '' else 'defdev'
        for ch in [' ', '(', ')']:
            device = device.replace(ch, '_')
        suffix = ""
        if emu_argparser.emu_args.is_gts:
          suffix = "-GTS"
        elif self.cts:
          suffix = "-CTS"
        return str("%s-%s-%s-%s-gpu_%s-api%s%s" % (self.tag, self.abi,
                                                 device, self.ram, self.gpu,
                                                 self.api, suffix))
    def name(self):
        return str(self)
class LoggedTestCase(unittest.TestCase):
    # Two logger are provided for each class
    # m_logger, used for script message, that are indicating the status of script
    # simple_logger, used for message from external process, keep their original format
    m_logger = None
    simple_logger = None

    def __init__(self, *args, **kwargs):
        super(LoggedTestCase, self).__init__(*args, **kwargs)

    @classmethod
    def setUpClass(cls):
        log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        simple_formatter = logging.Formatter('%(message)s')

        file_name = '%s_%s.log' % (cls.__name__, time.strftime("%Y%m%d-%H%M%S"))

        cls.m_logger = cls.setupLogger(cls.__name__, file_name, log_formatter)
        cls.simple_logger = cls.setupLogger(cls.__name__+'_simple', file_name, simple_formatter)

    @classmethod
    def setupLogger(cls, logger_name, file_name, formatter):

        file_handler = logging.FileHandler(os.path.join(emu_argparser.emu_args.session_dir, file_name))
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        # Redirect message to standard out, these messages indicate test progress, they don't belong to stderr
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(getattr(logging, emu_argparser.emu_args.loglevel.upper()))

        logger = logging.getLogger(logger_name)
        logger.propagate = False
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        logger.setLevel(logging.DEBUG)

        return logger

    @classmethod
    def tearDownClass(cls):
        # clear up log handlers
        def cleanup(logger):
            for x in list(logger.handlers):
                logger.removeHandler(x)
                x.flush()
                x.close()
        cleanup(cls.m_logger)
        cleanup(cls.simple_logger)

class EmuBaseTestCase(LoggedTestCase):
    """Base class for Emulator TestCase class

    Provide common base functions that will be used in derived emu test classes
    """
    def __init__(self, *args, **kwargs):
        super(EmuBaseTestCase, self).__init__(*args, **kwargs)
        self.boot_time = 0

    @classmethod
    def setUpClass(cls):
        super(EmuBaseTestCase, cls).setUpClass()

    def setUp(self):
        self.m_logger.info('Running - %s', self._testMethodName)

    def term_check(self, timeout):
        """Check if emulator process has terminated, return True if terminated else False"""
        for x in range(timeout):
            time.sleep(1)
            if self.find_emu_proc() is None:
                return True
        return False

    def find_emu_proc(self):
        """Return the first active emulator process, None if not found"""
        for proc in psutil.process_iter():
            try:
                if proc.name() != "emulator.exe" and "crash-service" not in proc.name() and ("emulator" in proc.name() or "qemu-system" in proc.name()):
                    self.m_logger.debug("Found - %s, pid - %d, status - %s", proc.name(), proc.pid, proc.status())
                    if proc.status() != psutil.STATUS_ZOMBIE:
                        return proc
            except psutil.NoSuchProcess:
                pass
        return None

    def kill_proc_by_name(self, proc_names):
        for x in psutil.process_iter():
            try:
                proc = psutil.Process(x.pid)
                # mips 64 use qemu-system-mipsel64, others emulator-[arch]
                if any([x in proc.name() for x in proc_names]):
                    if proc.status() != psutil.STATUS_ZOMBIE:
                        self.m_logger.info("kill_proc_by_name - %s, %s" % (proc.name(), proc.status()))
                        proc.kill()
            except psutil.NoSuchProcess:
                pass

    def launch_emu(self, avd):
        """Launch given avd and return immediately"""
        self.m_logger.info('call Launching AVD, ...: %s', str(avd))
        exec_path = emu_argparser.emu_args.emulator_exec
        launch_cmd = [exec_path, "-avd", str(avd), "-verbose", "-show-kernel", "-wipe-data"]
        if avd.classic == "yes":
            launch_cmd += ["-engine", "classic"]
        if avd.gpu == "swiftshader":
            launch_cmd += ["-gpu", "swiftshader"]
        else:
            launch_cmd += ["-gpu", "host"]
        # Launch emulator with "-dns-server 8.8.8.8" for CTS test
        # to make test_getByName in android.core.tests.libcore.package.libcore pass
        if avd.cts:
            launch_cmd += ["-dns-server", "8.8.8.8"]
        # The following flag is only in emu-master-dev
        # TODO: change it when https://android-review.googlesource.com/#/c/266872/ is merged to release branch or published.
        if "emu-master-dev" in exec_path:
            launch_cmd += ["-skip-adb-auth"]

        def launch_logcat_in_thread():
            local_test_name = self.id().rsplit('.', 1)[-1]
            logcat_path = os.path.join(emu_argparser.emu_args.session_dir, "%s_logcat.txt" % local_test_name)

            with open(logcat_path, 'a') as output:
                logcat_proc = None
                while (True):
                    if (logcat_proc is None or logcat_proc.poll() is not None):
                        self.m_logger.info('Launching logcat')
                        output.flush()
                        output.write("----Starting logcat----\n")
                        output.flush()
                        logcat_proc = psutil.Popen(["adb", "logcat"], stdout=output, stderr=STDOUT)
                    time.sleep(10)
                    if (not self.find_emu_proc()):
                        self.m_logger.info('No emulator found, stopping logcat')
                        break
                if (logcat_proc):
                  try:
                    logcat_proc.terminate()
                  except:
                    # Could not terminate logcat; probably already dead.
                    pass

        def readoutput_in_thread():
            with open(verbose_log_path, 'a') as verb_output:
                lines_iterator = iter(self.start_proc.stdout.readline, b"")
                for line in lines_iterator:
                    verb_output.write(line)
                    # Just write everything back to master builder as a heart-beat signal to avoid being killed
                    self.m_logger.info(line)
                    if any(x in line for x in ["ERROR", "FAIL", "error", "failed", "FATAL"]) and not line.startswith('['):
                        self.m_logger.error(line)


        test_name  = self.id().rsplit('.', 1)[-1]
        verbose_log_path = os.path.join(emu_argparser.emu_args.session_dir, "%s_verbose.txt" % test_name)
        self.m_logger.info('Launching AVD, cmd: %s', ' '.join(launch_cmd))
        self.start_proc = psutil.Popen(launch_cmd, stdout=PIPE, stderr=STDOUT)
        self.m_logger.info('done Launching AVD, cmd: %s', ' '.join(launch_cmd))

        self.m_logger.info('create thread to read output of AVD, cmd: %s', str(avd))
        t_launch = threading.Thread(target=readoutput_in_thread)
        t_launch.start()
        self.m_logger.info('done create thread to read output of AVD, cmd: %s', str(avd))

        self.m_logger.info('create thread to read logcat of AVD, cmd: %s', str(avd))
        logcat_thread = threading.Thread(target=launch_logcat_in_thread)
        logcat_thread.start()
        self.m_logger.info('done create thread to read logcat of AVD, cmd: %s', str(avd))
        # TODO: decrease the wait time
        # It is noticed that it takes a 'long time' for process to quit in some failure cases
        # But if the boot up time improves to be under 60 seconds, we will need to fine tune this wait time
        #time.sleep(60)
        #if self.start_proc.poll() or not self.find_emu_proc():
        #    raise LaunchError(str(avd))
        self.m_logger.info('return Launching AVD, ...: %s', str(avd))

    def run_with_timeout(self, cmd, timeout):
        vars = {'output': "",
                'err': "",
                'process': None}

        def run_cmd():
            vars['process'] = psutil.Popen(cmd, stdout=PIPE, stderr=PIPE)
            (vars['output'], vars['err']) = vars['process'].communicate()

        thread = threading.Thread(target=run_cmd)
        thread.start()

        thread.join(timeout)
        if thread.is_alive():
            self.m_logger.info('cmd %s timeout, force terminate', ' '.join(cmd))
            try:
                vars['process'].terminate()
                self.kill_proc_by_name(["adb"])
            except Exception as e:
                self.m_logger.error('exception terminate adb getprop process: %r', e)
        thread.join(timeout)
        return vars['process'].returncode, vars['output'], vars['err']

    def launch_emu_and_wait(self, avd):
        """Launch given avd and wait for boot completion, return boot time"""
        #self.launch_emu(avd)
        self.run_with_timeout(["adb", "kill-server"], 20)
        self.run_with_timeout(["adb", "start-server"], 20)
        launcher_emu = threading.Thread(target=self.launch_emu, args=[avd])
        launcher_emu.start()
        start_time = time.time()
        completed = "0"
        counter = 0
        real_time_out = emu_argparser.emu_args.timeout_in_seconds;
        if 'swiftshader' in str(avd):
            real_time_out = real_time_out + emu_argparser.emu_args.timeout_in_seconds
        if 'arm' in str(avd):
            real_time_out = real_time_out + emu_argparser.emu_args.timeout_in_seconds;
        if 'mips' in str(avd):
            real_time_out = real_time_out + emu_argparser.emu_args.timeout_in_seconds;
        while time.time()-start_time < real_time_out:
            cmd = ["adb", "shell", "getprop", "sys.boot_completed"]
            try:
                (exit_code, output, err) = self.run_with_timeout(cmd, 10)
            except Exception as e:
                self.m_logger.error('exception run_with_timeout adb getprop: %r', e)
                continue
            if counter % 60 is 0 or counter < 60:
                self.m_logger.info('timeout is %s seconds', real_time_out)
                self.m_logger.info('ping AVD %s for boot completion, output: %s error: %s', avd, output, err)
            counter = counter + 1
            if exit_code is 0:
                completed = output.strip()
            if completed is "1":
                self.m_logger.info('AVD %s is fully booted', avd)
                break
            time.sleep(1)
        if completed is not "1":
            self.m_logger.info('command output - %s %s', output, err)
            self.m_logger.error('AVD %s didn\'t boot up within %s seconds', avd,
                                real_time_out)
            self.boot_time = -1
            raise TimeoutError(avd, real_time_out)
        self.boot_time = time.time() - start_time
        self.m_logger.info('AVD %s, boot time is %s', avd, self.boot_time)
        launcher_emu.join(10)
        if not emu_argparser.emu_args.skip_adb_perf:
            self.run_adb_perf(avd)
        return self.boot_time

    def run_adb_perf(self, avd):
        test_file = "small_file.zip" if avd.classic == "yes" else "large_file.zip"
        local_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "adb_test_data", test_file)
        file_size = os.path.getsize(local_path)
        device_path = "/data/local/tmp/%s" % test_file
        push_cmd = ["adb", "push", local_path, device_path]
        pull_cmd = ["adb", "pull", device_path, "."]
        run_time = []
        for cmd in [push_cmd, pull_cmd]:
            try:
                start_time = time.time()
                (exit_code, output, err) = self.run_with_timeout(cmd, 600)
                # deduct 0.015 seconds for the overhead of sending adb command
                elapsed_time = time.time() - start_time - 0.015

                calculated_speed = (file_size/1024)/elapsed_time
                speed = "%.0f KB/s" % calculated_speed

                self.m_logger.info('Time elapsed: %s, File size: %s, speed: %s', elapsed_time, file_size, speed)

                if exit_code == 0:
                  run_time.append(speed)
                else:
                  self.m_logger.info('Fails to run adb performance test, exit_code: %s', exit_code)
                  return
            except Exception as e:
                self.m_logger.error('exception run_with_timeout %s: %r', ' '.join(cmd), e)
                return
        self.m_logger.info('AVD %s, adb push: %s, adb pull: %s', avd, run_time[0], run_time[1])

    def update_config(self, avd_config):
        # avd should be found $HOME/.android/avd/
        avd_dir = os.path.join(os.path.expanduser('~'), '.android', 'avd',
                               '%s.avd' % avd_config.name())
        dst_path = os.path.join(avd_dir, 'config.ini')
        class AVDIniConverter:
            output_file = None
            def __init__(self, file_path):
                self.output_file = file_path
            def write(self, what):
                self.output_file.write(what.replace(" = ", "="))
        config = ConfigParser.ConfigParser()
        config.optionxform = str
        file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                 '..', 'config', 'avd_template.ini')
        config.read(file_path)
        def set_val(key, val):
            if val != "":
                config.set('Common', key, val)

        tag_id_to_display = {
                             'android-tv': 'Android TV',
                             'android-wear': 'Android Wear',
                             'default': 'Default',
                             'google_apis': 'Google APIs'
                            }
        abi_to_cpu_arch = {
                           'x86': 'x86',
                           'x86_64': 'x86_64',
                           'arm64-v8a': 'arm64',
                           'armeabi-v7a': 'arm',
                           'mips': 'mips',
                           'mips64': 'mips64'
                          }
        def loadSection(section):
            for conf in config.options(section):
                set_val(conf, config.get(section, conf))
        loadSection(avd_config.device)
        if avd_config.cts:
            loadSection('cts')
        set_val('AvdId', avd_config.name())
        set_val('abi.type', avd_config.abi)
        set_val('avd.ini.displayname', avd_config.name())
        set_val('hw.cpu.arch', abi_to_cpu_arch[avd_config.abi])
        if avd_config.abi == 'armeabi-v7a':
            set_val('hw.cpu.model', 'cortex-a8')
        gpu = "no" if avd_config.gpu == "no" else "yes"
        set_val('hw.gpu.enabled', gpu)
        set_val('hw.ramSize', avd_config.ram)
        api_target = avd_config.api if avd_config.api != "26" else "O"
        set_val('image.sysdir.1',
                'system-images/android-%s/%s/%s/' % (api_target, avd_config.tag, avd_config.abi))
        set_val('tag.display', tag_id_to_display[avd_config.tag])
        set_val('tag.id', avd_config.tag)

        self.m_logger.info("Update device settings at %s", dst_path)
        for section in config.sections():
            if section != 'Common':
                config.remove_section(section)

        # remove space around equal sign and header
        with open(dst_path, 'w') as fout:
            config.write(AVDIniConverter(fout))
        with open(dst_path, 'r') as fin:
            data = fin.read().splitlines(True)
        with open(dst_path, 'w') as fout:
            fout.writelines(data[1:])
        # create sdcard.img
        try:
            img_path = os.path.join(avd_dir, 'sdcard.img')
            create_img_cmd = ['mksdcard', config.get('Common', 'sdcard.size'), img_path]
            self.m_logger.info('Create sdcard.img, cmd: %s', ' '.join(create_img_cmd))
            psutil.Popen(create_img_cmd, stdout=PIPE, stderr=PIPE).communicate()
        except ConfigParser.NoOptionError:
            self.m_logger.exception('Check avd_template.ini')
            pass
        except:
            self.m_logger.exception('Failed to create sdcard.img, make sure you have mksdcard on your path ($ANDROID_SDK_ROOT/tools/mksdcard)')
            pass

    def create_avd(self, avd_config):
        """Create avd if doesn't exist

           return 0 if avd exist or creation succeeded
           otherwise, return value of creation process.
        """
        avd_name = str(avd_config)

        def try_create_with_sdk():
            android_exec = "android.bat" if os.name == "nt" else "android"
            avd_abi = "%s/%s" % (avd_config.tag, avd_config.abi)
            api_target = avd_config.api if avd_config.api != "26" else "O"
            if "google" in avd_config.tag:
                avd_target = "Google Inc.:Google APIs:%s" % (api_target)
            else:
                avd_target = "android-%s" % (api_target)
            create_cmd = [android_exec, "create", "avd", "--force",
                          "--name", avd_name, "--target", avd_target,
                          "--abi", avd_abi]
            self.m_logger.info("Create AVD, cmd: %s" % ' '.join(create_cmd))
            avd_proc = psutil.Popen(create_cmd,
                                    stdout=PIPE, stdin=PIPE, stderr=PIPE)
            output, err = avd_proc.communicate(input='\n')
            self.simple_logger.debug(output)
            self.simple_logger.debug(err)
            if 'Error' in err:
                return -1
            return avd_proc.poll()

        def try_create_with_config():
            """ Create a new AVD based on avd_config
                Returns 0 if succeeds, non-zero if fails
                Steps:
                1. Check system image installed userdata.img
                2. If there is existing AVD with this name, remove existing directory
                3. Create [AVD NAME].ini file
                4. Create AVD directory
                config.ini is created if above steps pass
            """
            # avd directory $HOME/.android/avd/
            avd_base_dir = os.path.join(os.path.expanduser('~'), ".android", "avd")
            avd_dir = os.path.join(avd_base_dir, '%s.avd' % avd_name)

            api_target = avd_config.api
            if "google" in avd_config.tag:
                avd_target = "Google Inc.:Google APIs:%s" % (api_target)
            else:
                avd_target = "android-%s" % (api_target)

            # 1. check userdata.img exists
            userimg_name = "userdata.img"
            userdata_src = os.path.join(os.environ['ANDROID_SDK_ROOT'],
                                        "system-images", "android-%s" % api_target,
                                        avd_config.tag, avd_config.abi, userimg_name)
            if not os.path.isfile(userdata_src):
              self.m_logger.error("userdata image %s does not exist! Try install system image." % userdata_src)
              return 1

            # 2. if destination directory exists, remove it
            shutil.rmtree(avd_dir, ignore_errors=True)

            # 3. create ini file
            ini_path = os.path.join(avd_base_dir, '%s.ini' % avd_name)
            self.m_logger.info("ini file path: %s" % ini_path)
            with open(ini_path, "w") as ini_file:
              ini_file.write('avd.ini.encoding=UTF-8\n')
              ini_file.write('path=%s\n' % avd_dir)
              ini_file.write('path.rel=%s\n' % os.path.join('avd', '%s.avd' % avd_name))
              ini_file.write('target=%s\n' % avd_target)

            # 4. create avd directory
            try:
               os.makedirs(avd_dir)
            except OSError:
               assert os.path.isdir(avd_dir),"Unable to create avd directory %s, %r" % (avd_dir, OSError)
            return 0

        ret = try_create_with_config()
        if ret != 0:
            # try to download the system image
            api = avd_config.api
            self.update_sdk("android-%s" % api)
            if "google" in avd_config.tag:
                self.update_sdk("addon-google_apis-google-%s" % api)
                self.update_sdk("sys-img-%s-google_apis-%s"
                                % (avd_config.abi, api))
            elif "wear" in avd_config.tag:
                self.update_sdk("sys-img-%s-android-wear-%s" % (avd_config.abi, api))
            elif "tv" in avd_config.tag:
                self.update_sdk("sys-img-%s-android-tv-%s" % (avd_config.abi, api))
            else:
                self.update_sdk("sys-img-%s-android-%s" % (avd_config.abi, api))
            self.m_logger.debug("try create avd again after update sdk")
            ret = try_create_with_config()
        # last step, create config.ini
        if ret == 0:
            self.update_config(avd_config)

        return ret

    def update_sdk(self, filter):
        """Update sdk from command line with given filter"""

        android_exec = "android.bat" if os.name == "nt" else "android"
        cmd = [android_exec, "update", "sdk", "--no-ui", "--all", "--filter", filter]
        self.m_logger.debug("update sdk %s", ' '.join(cmd))
        update_proc = psutil.Popen(cmd, stdout=PIPE, stdin=PIPE, stderr=PIPE)
        output, err = update_proc.communicate(input='y\n')
        self.simple_logger.debug(output)
        self.simple_logger.debug(err)
        self.m_logger.debug('return value of update proc: %s', update_proc.poll())
        return update_proc.poll()

def create_test_case_from_file(desc, testcase_class, test_func):
    """ Create test case based on test configuration file. """

    is_cts = True if desc == "cts" else False
    def get_port():
        if not hasattr(get_port, '_port'):
            get_port._port = 5552
        get_port._port += 2
        return str(get_port._port)

    def valid_case(avd_config):
        def fn_leq(x,y): return x <= y
        def fn_less(x,y): return x < y
        def fn_geq(x,y): return x >= y
        def fn_greater(x,y): return x > y
        def fn_eq(x,y): return x == y
        def fn_neq(x,y): return x != y

        op_lookup = {
            "==": fn_eq,
            "=": fn_eq,
            "!=": fn_neq,
            "<>": fn_neq,
            ">": fn_greater,
            "<": fn_less,
            ">=": fn_geq,
            "<=": fn_leq
            }
        if emu_argparser.emu_args.filter_dict is not None:
            for key, value in emu_argparser.emu_args.filter_dict.iteritems():
                if any([value.startswith(x) for x in ["==", "!=", "<>", ">=", "<="]]):
                    cmp_op = value[:2]
                    cmp_val = value[2:]
                elif any([value.startswith(x) for x in ["=", ">", "<"]]):
                    cmp_op = value[:1]
                    cmp_val = value[1:]
                else:
                    cmp_op = "=="
                    cmp_val = value
                if not op_lookup[cmp_op](getattr(avd_config, key), cmp_val):
                    return False
        return True

    def create_test_case(avd_config, op):
        """ Swiftshader GPU rendering is currently only available within the emu-master-dev branch. """
        if not is_cts and avd_config.gpu == "yes" and "emu-master-dev" in emu_argparser.emu_args.emulator_exec:
            avd_config_swiftshader = avd_config._replace(gpu = "swiftshader")
            create_test_case(avd_config_swiftshader, op)

        if op == "S" or op == "" or not valid_case(avd_config):
            return

        func = lambda self: test_func(self, avd_config)
        if op == "X":
            func = unittest.expectedFailure(func)
        # TODO: handle flakey tests
        elif op == "F":
            func = func
        qemu_str = "_qemu2" if avd_config.classic == "no" else "_qemu1"
        setattr(testcase_class, "test_%s_%s%s" % (desc, str(avd_config), qemu_str), func)

    with open(emu_argparser.emu_args.config_file, "rb") as file:
        reader = csv.reader(file)
        for row in reader:
            #skip the first line
            if reader.line_num == 1:
                continue
            if reader.line_num == 2:
                idx = [i for i, j in enumerate(row) if j in emu_argparser.emu_args.builder_name]
                assert len(idx) == 1, "Unexpected builder name {0} in line {1}, config file: {1}".format(
                    emu_argparser.emu_args.builder_name, row, emu_argparser.emu_args.config_file)
                builder_idx = idx[0]
            else:
                if(row[0].strip() != ""):
                    api = row[0].split("API", 1)[1].strip()
                if(row[1].strip() != ""):
                    tag = row[1].strip()
                if(row[2].strip() != ""):
                    abi = row[2].strip()

                # P - config should be passing
                # X - config is expected to fail
                # S and everything else - Skip this config
                op = row[builder_idx].strip().upper()
                if op in ["P", "X", "F"]:
                    device = row[3]
                    if row[4] != "":
                        ram = row[4]
                    else:
                        ram = "512" if device == "" else "1536"
                    if row[5] != "":
                        gpu = row[5]
                    else:
                        gpu = "yes" if api > "15" else "no"
                    ori = row[6].strip()
                    ori = "public" if ori == "" else ori
                    # For 32 bit machine, ram should be less than 768MB
                    if not platform.machine().endswith('64'):
                        ram = str(min([int(ram), 768]))
                    # use qemu2 for top of tree images and public images above api 19
                    # arm use qemu1 regardless of origin and api level
                    if (ori != "public" or api >= "19") and abi != "armeabi-v7a":
                      classic = "no"
                    else:
                      classic = "yes"
                    if device == "":
                      device = "default"
                    avd_config = AVDConfig(api, tag, abi, device, ram, gpu, classic, get_port(), is_cts, ori)
                    create_test_case(avd_config, op)
