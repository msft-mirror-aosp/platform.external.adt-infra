"""Test for ADB push/pull commands."""

import os
import unittest
import subprocess
import time

import testcase_base
import adb_util

TEMP_FILE = '__push_file.txt'

# Number of lines in push/pull'd file.
FILE_SIZE = 100

class PushPullTest(testcase_base.BaseAdbTest):
    """This class aims to test ADB push/pull commands."""

    def __init__(self, method_name=None):
        if method_name:
            super(PushPullTest, self).__init__(method_name)
        else:
            super(PushPullTest, self).__init__()

    def setUp(self):
        """There is nothing to do in setUp()."""
        pass

    def tearDown(self):
        """There is nothing to do in tearDown()."""
        pass

    def create_temp_files(self):
        """Setup for push test.

        Creates all temporary files created used in push test."""
        file = open(TEMP_FILE, 'w')
        for i in range(FILE_SIZE):
            file.write('lorem ipsum\n')
        file.close()


    def delete_temp_files(self):
        """Teardown for push test.

        Deletes all temporary files created for push test.
        """
        try:
            os.remove(TEMP_FILE)
        except OSError:
            pass

    def adb_test_push(self, dut):
        """Verify that pushing a file is successful.

        File size is determined by FILE_SIZE constant.

        Args:
          dut: Device to test against.

        Returns:
          True if successful, else False.
        """
        arg = self.adb_binary + ' -s ' + str(dut) + ' push ' + TEMP_FILE + ' /sdcard/'
        process = subprocess.Popen(arg.split(), stdout=subprocess.PIPE)
        output, error = process.communicate()
        success = True
        for line in output.split('\n'):
            if line.startswith('adb: error'):
                success = False
                print('\nERROR:\nEPush FAILED for: ' + str(dut))
                print(output)

        return success

    def adb_test_pull(self, dut):
        """Verify that pulling a file is successful.

        File size is determined by FILE_SIZE constant.

        Returns:
          True if successful, else False.
        """
        arg = self.adb_binary + ' -s ' + str(dut) + ' pull /sdcard/' + TEMP_FILE
        process = subprocess.Popen(arg.split(), stdout=subprocess.PIPE)
        output, error = process.communicate()
        success = True
        for line in output.split('\n'):
            if line.startswith('adb: error'):
                print('\nERROR:\nEPush FAILED for: ' + str(dut))
                print(output)
                success = False

        return success

    def adb_push_pull(self, dut):
        """Runs single push/pull against a single device.

        Args:
            dut: device under test
        """
        time.sleep(1)
        success = self.adb_test_push(dut)
        time.sleep(1)
        success = self.adb_test_pull(dut) and success
        return success

    def test_adb_push_pull_stress(self):
        print 'Running test: ADB Push Pull stress'
        status = adb_util.launcher(self.adb_push_pull, 0.05, 1,
                                   setup=self.create_temp_files, cleanup=self.delete_temp_files,
                                   is_print_progress=True)
        self.assertTrue(status, "ADB Push/Pull failed")

if __name__ == '__main__':
  print '======= auth Test ======='
  unittest.main()
