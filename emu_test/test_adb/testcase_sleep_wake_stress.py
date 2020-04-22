"""Test for ADB sleep/wake commands."""

import os
import unittest
import subprocess

import testcase_base
import adb_util

class SleepWakeTest(testcase_base.BaseAdbTest):
    """This class aims to test ADB sleep/wake commands."""

    def __init__(self, method_name=None, avd=None):
        if method_name:
            super(SleepWakeTest, self).__init__(method_name)
        else:
            super(SleepWakeTest, self).__init__()
        self.avd = avd

    def setUp(self):
        """There is nothing to do in setUp()."""
        pass

    def tearDown(self):
        """There is nothing to do in tearDown()."""
        pass

    def adb_test_sleep(self, dut):
        """Verify that putting the device to sleep is successful.

        Args:
          dut: Serial number of device to connect to.

        Returns:
          True if the device was successfully put to sleep, else False
        """
        # Simulate power button press.
        # It would be good if we verified the device was currently awake.
        # Otherwise, this will actually wake up the device.
        arg = self.adb_binary + ' -s ' + str(dut) + ' shell input keyevent POWER'
        process = subprocess.Popen(arg.split(), stdout=subprocess.PIPE)
        output, error = process.communicate()
        success = True
        for line in output.split('\n'):
            if line.startswith('adb: error'):
                success = False
                print('\nERROR:\nFAILED to put device to sleep: ' + str(dut))
                print(output)

        return success

    def adb_test_wake(self, dut):
        """Verify that the device can be woken up.

        Args:
          dut: Serial number of device under test.

        Returns:
          True if the device was successfully woken up, else False.
        """
        arg = self.adb_binary + ' -s ' + str(dut) + ' shell input keyevent POWER'
        process = subprocess.Popen(arg.split(), stdout=subprocess.PIPE)
        output, error = process.communicate()
        success = True
        for line in output.split('\n'):
            if line.startswith('adb: error'):
                print('\nERROR:\nFAILED to wake device: ' + str(dut))
                print(output)
                success = False

        return success

    def adb_sleep_wake(self, dut):
        time.sleep(1)
        success = self.adb_test_sleep(dut)
        time.sleep(1)
        success = self.adb_test_wake(dut) and success
        return success

    def test_adb_sleep_wake_stress(self):
        print 'Running test: ADB Sleep Wake stress'
        status = adb_util.launcher(self.adb_sleep_wake, 0.25, 1,
                                   is_print_progress=True)
        self.assertTrue(status, "ADB Sleep/Wake failed")

if __name__ == '__main__':
  print '======= auth Test ======='
  unittest.main()
