"""Class for PSQ Snapshot Test Runner Tests"""

import os
import time
import psutil
import shutil
import subprocess
import threading

import emu_test.utils.emu_testcase
from emu_test.utils.emu_argparser import emu_args
from emu_test.utils import path_utils
from emu_test.utils import emu_argparser
from emu_test.utils.emu_testcase import EmuBaseTestCase, AVDConfig
from emu_test.utils.emu_error import *

adb_binary = path_utils.get_adb_binary()

class IceboxTestCase(EmuBaseTestCase):
    def __init__(self, *args, **kwargs):
        super(IceboxTestCase, self).__init__(*args, **kwargs)
        self.avd_config = None

    @classmethod
    def setUpClass(cls):
        super(IceboxTestCase, cls).setUpClass()

    def kill_emulator(self):
        self.m_logger.debug('First try - quit emulator by adb emu kill')
        kill_proc = psutil.Popen([adb_binary, "emu", "kill"])
        # check emulator process is terminated
        result = self.term_check(timeout=5)
        if not result:
            self.m_logger.debug('Second try - quit emulator by psutil')
            self.kill_proc_by_name(["emulator", "qemu-system"])
            result = self.term_check(timeout=10)
            self.m_logger.debug("term_check after psutil.kill - %s", result)
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
            self.m_logger.error("Error in cleanup - %r", e)
            pass

    def run_and_log(self, cmd):
        self.m_logger.info(cmd)
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        self.m_logger.info(out)
        return out

    def am_thread_run(self, cmd):
        self.m_logger.info(cmd)
        self.test_result = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        self.m_logger.info(self.test_result)
        self.m_logger.info("Note: instrumentation test failure is expected")

    def run_icebox_test(self, avd_config):
        """
        Run icebox test. Note: the test does not work when Android Studio is
        running in background.
        """
        self.avd_config = avd_config
        avd = self.create_avd(avd_config)
        self.launch_emu_and_wait(avd_config)
        prebuilts_path = os.path.join(path_utils.get_emu_test_path(), "prebuilts", "icebox")
        tries = 0
        while tries < 5:
            try:
                # the first install might fail on api 29
                self.run_and_log([adb_binary, "install", os.path.join(prebuilts_path,
                                                                "app-debug.apk")])
                break
            except:
                self.m_logger.info("Apk install failed, retrying %d" % tries)
                tries = tries + 1
        # app-debug-androidTest.apk is just a sample test APK with one assert failure
        self.run_and_log([adb_binary, "install", os.path.join(prebuilts_path,
                                                         "app-debug-androidTest.apk")])
        test_run_cmd = [adb_binary, "shell", "am", "instrument", "-w", "-r", "-e", "debug",
            "true", "-e", "class", "'com.example.myapplication.ExampleInstrumentedTest'",
            "com.example.myapplication.test/androidx.test.runner.AndroidJUnitRunner"]
        test_thread = threading.Thread(target=self.am_thread_run, args=(test_run_cmd,))
        test_thread.start()
        # wait for the app to launch
        time.sleep(5)
        tries = 0
        while tries < 20:
            try:
                pid = self.run_and_log([adb_binary, "shell", "pidof", "com.example.myapplication"])
                break
            except:
                self.m_logger.info("Get pid failed, retrying %d times in 1 sec" % tries)
                time.sleep(1)
                tries = tries + 1
        assert tries < 20, "Maximum retries exceeded when getting pid"

        pid = pid.rstrip()
        time.sleep(5)
        self.run_and_log([adb_binary, "emu", "icebox", "track", pid])
        test_thread.join(60)
        assert "FAILURES!!!" in self.test_result
        snapshot_list = self.run_and_log([adb_binary, "emu", "avd", "snapshot", "list"])
        snapshot_name = "test_failure_snapshot"
        # BUG: 148689571
        # adb emu command does not list the snapshots on buildbot
        assert 'ANDROID_AVD_HOME' in os.environ, "ANDROID_AVD_HOME not set"
        snapshot_folder = os.path.join(os.environ['ANDROID_AVD_HOME'],
                         '%s.avd' % self.avd_config.name(),
                         'snapshots')
        self.run_and_log(['ls', snapshot_folder])
        self.run_and_log(['df', '-h'])
        assert snapshot_name in snapshot_list or os.path.isdir(
            os.path.join(snapshot_folder,
                         snapshot_name))

if emu_args.config_file is not None:
    emu_test.utils.emu_testcase.create_test_case_from_file("Icebox", IceboxTestCase, IceboxTestCase.run_icebox_test)

if __name__ == '__main__':
    os.environ["SHELL"] = "/bin/bash"
    emu_argparser.emu_args = emu_argparser.get_parser().parse_args()
    print emu_argparser.emu_args
    sys.argv[1:] = emu_args.unittest_args
    unittest.main()
