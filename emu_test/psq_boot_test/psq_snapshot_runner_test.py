"""Class for PSQ Snapshot Test Runner Tests"""

import os
import subprocess
import psutil

from emu_test.utils import path_utils
from psq_boot_test import PsqBootTestBase

class PsqSnapshotRunnerTestCase(PsqBootTestBase):
    def __init__(self, *args, **kwargs):
        super(PsqBootTestBase, self).__init__(*args, **kwargs)

    @classmethod
    def setUpClass(cls):
        super(PsqBootTestBase, cls).setUpClass()

    def run_and_log(self, cmd):
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        self.m_logger.info(out)
        return out

    def run_snapshot_runner_test(self, avd_config):
        avd = self.create_avd(avd_config)
        launcher_emu, boot_time = self.launch_emu_no_kill(avd_config,
                ["-feature", "SnapshotAdb,Offworld"])
        prebuilts_path = os.path.join(path_utils.get_emu_test_path(), "prebuilts")
        self.run_and_log(["adb", "install", os.path.join(prebuilts_path,
                                                         "AndroidOffworld.apk")])
        self.run_and_log(["adb", "install", os.path.join(prebuilts_path,
                                                         "AndroidOffworld_unittests.apk")])
        # We need to run SaveLoadTest and ForkTest. ForkTest is flaky so we disable it for now.
        out = self.run_and_log(["adb", "shell", "am", "instrument", "-w", "-r", "-e", "debug",
            "false", "-e", "class", "'com.google.android.offworld.examples.snapshot.SaveLoadTest'",
            "com.google.android.offworld.examples.snapshot.test/"
            + "androidx.test.runner.AndroidJUnitRunner"])

        launcher_emu.join(10)
        self.kill_emulator()

        assert "OK (1 test)" in out
