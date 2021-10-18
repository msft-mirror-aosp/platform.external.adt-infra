"""Tests for geo-related commands."""

import os
import time
import unittest
import subprocess
import sys
from . import testcase_base
from .utils import util

CMD_GEO_FIX = 'geo fix {} {} {}\n'
COORDINATES_MATCHING_STRING = 'Longitude:{} || Latitude:{} || Altitude:{}'
SF_LONGITUDE = -122.0
SF_LATITUDE = 37.0
SF_ALTITUDE = 0.0

SF_INVALID_LONGITUDE = 200
SF_INVALID_LATITUDE = 100
SF_INVALID_ALTITUDE = 100

CONSOLE_TEST_PACKAGE_NAME = 'com.example.ConsoleTest'
ASSERT_MSG = 'Location Co-ordinates cannot be pushed'
ASSERT_MSG_MATCH_FAILURE = 'Location Co-ordinates do not match'
RESPONSE_FOR_INVALID_CMD = 'KO'


class GeoTest(testcase_base.BaseConsoleTest):
  """This class aims to test geo-related emulator console commands."""

  def __init__(self, method_name=None):
    if method_name:
      super(GeoTest, self).__init__(method_name)
    else:
      super(GeoTest, self).__init__()

  @classmethod
  def setUpClass(cls):
    util.install_with_permission("ConsoleTest.apk")

  @classmethod
  def tearDownClass(cls):
    util.unstall_apps(CONSOLE_TEST_PACKAGE_NAME)

  def test_geo(self):
    """Test command for: geo fix xxx

    TT ID: caad94f5-1714-470c-829c-6df616dfa358
    Test steps:
      1. Launch an emulator avd
      2. From command prompt, run: telnet localhost <port>
      3. Copy the auth_token value from ~/.emulator_console_auth_token
      4. Run: auth auth_token
      5. Open Google Maps app and accept the terms and conditions
      6. Enable location service in Google Maps
      7. Tap on My Location
      8. Run: geo fix -122 37 0
    Verify:
      Check Maps location centers on San Francisco.
    """
    this_function_name = sys._getframe().f_code.co_name
    print(('Running test: %s' %(this_function_name)))
    self._execute_command_and_verify(CMD_GEO_FIX.format(SF_LONGITUDE, SF_LATITUDE, SF_ALTITUDE), util.OK,
                                     ASSERT_MSG)
    self._poll_and_verify_coordinates(COORDINATES_MATCHING_STRING.format(SF_LONGITUDE, SF_LATITUDE, SF_ALTITUDE))

  def test_geo_stress(self):
    """Stress geo location by attempting to send invalid coordinates."""
    this_function_name = sys._getframe().f_code.co_name
    print(('Running test: %s' % (this_function_name)))
    self._execute_command_and_verify(CMD_GEO_FIX.format(SF_LONGITUDE, SF_LATITUDE, SF_ALTITUDE), util.OK,
                                     ASSERT_MSG)
    self._execute_command_and_verify(CMD_GEO_FIX.format(SF_INVALID_LONGITUDE, SF_INVALID_LATITUDE, SF_INVALID_ALTITUDE), RESPONSE_FOR_INVALID_CMD,
                                     ASSERT_MSG)
    self._poll_and_verify_coordinates(COORDINATES_MATCHING_STRING.format(SF_LONGITUDE, SF_LATITUDE, SF_ALTITUDE))

  def _poll_and_verify_coordinates(self, coordinates_string):
   adb_binary = os.path.join(os.environ['ANDROID_SDK_ROOT'], 'platform-tools', 'adb')
   subprocess.Popen(['adb', 'logcat', '-c'], stderr=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
   util.launch_application(CONSOLE_TEST_PACKAGE_NAME + '/com.example.ConsoleTest.MainActivity')
   time.sleep(1)
   test_process = subprocess.check_output([adb_binary, 'logcat', '-d'])
   is_match_successful = coordinates_string in str(test_process)
   self.assertTrue(is_match_successful, ASSERT_MSG_MATCH_FAILURE)

  def _execute_command_and_verify(self, command, expected_output, assert_msg):
    """Executes console command and verify output.
    Args:
      command: Console command to be executed.
      expected_output: Expected console output.
      assert_msg: Assertion message.
    """
    is_command_successful, output = util.execute_console_command(
    self.telnet, command, expected_output)
    self.assert_cmd_successful(is_command_successful, assert_msg, False, '',
                               'Pattern: \n%s' % expected_output, output)

if __name__ == '__main__':
  print('======= geo Test =======')
  unittest.main()
