"""Class for PSQ Snapshot Test Runner Tests"""

import os
import time
import psutil
import shutil
import subprocess

import emu_test.utils.emu_testcase
from emu_test.utils.emu_argparser import emu_args
from emu_test.utils import path_utils
from emu_test.utils import emu_argparser
from emu_test.utils.emu_testcase import EmuBaseTestCase, AVDConfig
from emu_test.utils.emu_error import *

adb_binary = path_utils.get_adb_binary()

class PsqSnapshotRunnerTestCase(EmuBaseTestCase):
    def __init__(self, *args, **kwargs):
        super(PsqSnapshotRunnerTestCase, self).__init__(*args, **kwargs)
        self.avd_config = None

    @classmethod
    def setUpClass(cls):
        super(PsqSnapshotRunnerTestCase, cls).setUpClass()

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
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        self.m_logger.info(out)
        return out

    def run_snapshot_runner_test(self, avd_config):
        self.avd_config = avd_config
        avd = self.create_avd(avd_config)
        launcher_emu, boot_time = self.launch_emu_no_kill(avd_config,
                ["-feature", "SnapshotAdb,Offworld"])
        prebuilts_path = os.path.join(path_utils.get_emu_test_path(), "prebuilts")
        self.run_and_log([adb_binary, "install", os.path.join(prebuilts_path,
                                                         "AndroidOffworld.apk")])
        self.run_and_log([adb_binary, "install", os.path.join(prebuilts_path,
                                                         "AndroidOffworld_unittests.apk")])
        # We need to run SaveLoadTest and ForkTest. ForkTest is flaky so we disable it for now.
        out = self.run_and_log([adb_binary, "shell", "am", "instrument", "-w", "-r", "-e", "debug",
            "false", "-e", "class", "'com.google.android.offworld.examples.snapshot.SaveLoadTest'",
            "com.google.android.offworld.examples.snapshot.test/"
            + "androidx.test.runner.AndroidJUnitRunner"])

        launcher_emu.join(10)
        self.kill_emulator()

        assert "OK (1 test)" in out

if emu_args.config_file is not None:
    emu_test.utils.emu_testcase.create_test_case_from_file("SnapshotRunner", PsqSnapshotRunnerTestCase, PsqSnapshotRunnerTestCase.run_snapshot_runner_test)

if __name__ == '__main__':
    os.environ["SHELL"] = "/bin/bash"
    emu_argparser.emu_args = emu_argparser.get_parser().parse_args()
    print emu_argparser.emu_args
    sys.argv[1:] = emu_args.unittest_args
    unittest.main()
