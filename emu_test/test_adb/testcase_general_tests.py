"""Run adb/device integration tests from general-tests"""

import os
import unittest
import subprocess

import testcase_base
import adb_util

@unittest.skip("These tests are running in presubmit for Linux on aosp")
class GeneralTest(testcase_base.BaseAdbTest):
    """This class aims to run adb/device integration tests from general-tests."""

    def __init__(self, method_name=None):
        if method_name:
            super(GeneralTest, self).__init__(method_name)
        else:
            super(GeneralTest, self).__init__()

    def setUp(self):
        """There is nothing to do in setUp()."""
        pass

    def tearDown(self):
        """There is nothing to do in tearDown()."""
        pass

    def test_adb_integration_device(self):
        try:
            print 'Running test: Device integration tests'
            test_dir = os.environ["GENERAL_TESTS_DIR"]
            test = os.path.join(test_dir,
                                "adb_integration_test_device",
                                "x86_64",
                                "adb_integration_test_device")
            adbCmd = subprocess.Popen(["python", test],
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT)

            stdout, stderr = adbCmd.communicate()
            print stdout
            print stderr
        except KeyError:
            print 'Define GENERAL_TESTS_DIR to point to directory containing adb_integration_test_device'

    def test_adb_integration_adb(self):
        try:
            print 'Running test: ADB integration tests'
            test_dir = os.environ["GENERAL_TESTS_DIR"]
            test = os.path.join(test_dir,
                                "adb_integration_test_adb",
                                "x86_64",
                                "adb_integration_test_adb")
            adbCmd = subprocess.Popen(["python", test],
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT)

            stdout, stderr = adbCmd.communicate()
            print stdout
            print stderr
        except KeyError:
            print 'Define GENERAL_TESTS_DIR to point to directory containing adb_integration_test_adb'

if __name__ == '__main__':
  print '======= Integration Tests ======='
  unittest.main()
