"""Tests for sms-related commands."""

import os
import unittest
import sys
import subprocess
import time
from test_console.utils.util import WINDOWS_OS_NAME
from . import testcase_base
from .utils import util

SENDER_PHONE_NUMBER = '987654321'
TEXT_MESSAGE = 'Hello There'
MSG_MATCHING_STRING = 'Sender:{} || Message:{}'
CMD_SMS_SEND = 'sms send {} {}\n'
CMD_SMS_PDU = 'sms pdu {}\n'
PDU_FORMAT_MESSAGE = '07911326040000F0040B911346610089F60000208062917314080CC8F71D14969741F977FD07'
PDU_MESSAGE = 'How are you?'
PDU_PHONE_NUMBER = '+31641600986'
CONSOLE_TEST_PACKAGE_NAME = 'com.example.smstesthelper'
ASSERT_MSG_MATCH_FAILURE = 'Message/ Sender do not match'
ASSERT_MSG = 'Message sending failed'



class SmsTest(testcase_base.BaseConsoleTest):
  """This class aims to test sms-related emulator console commands."""

  def __init__(self, method_name=None):
    if method_name:
      super(SmsTest, self).__init__(method_name)
    else:
      super(SmsTest, self).__init__()

  @classmethod
  def setUpClass(cls):
    util.install_with_permission("SmsTestHelper.apk");

  @classmethod
  def tearDownClass(cls):
    util.unstall_apps(CONSOLE_TEST_PACKAGE_NAME)

  @unittest.skip("b/244168150")
  def test_send_inbound_sms_text_message(self):
    """Test command for: sms send <phone number> <text message>.

    TT ID: f2c2aa1a-b793-4939-b156-0e7d82c85502
    Test steps:
      1. Launch an emulator avd
      2. From command prompt, run: telnet localhost <port>
      3. Copy the auth_token value from ~/.emulator_console_auth_token
      4. Run: auth auth_token
      5. Run: sms send <phone number> <text message>, and verify
    Verify:
      An sms is received from <phone number> with the text <text message>.
    """
    this_function_name = sys._getframe().f_code.co_name
    print(('Running test: %s' % (this_function_name)))
    self._execute_command_and_verify(CMD_SMS_SEND.format(SENDER_PHONE_NUMBER, TEXT_MESSAGE), util.OK, ASSERT_MSG)
    self._poll_and_verify_sms(MSG_MATCHING_STRING.format(SENDER_PHONE_NUMBER, TEXT_MESSAGE))

  @unittest.skip("b/244168150")
  def test_send_inbound_sms_pdu(self):
    """Test command for: sms send <phone number> <text message>.

    TT ID: f2c2aa1a-b793-4939-b156-0e7d82c85502
    Test steps:
        1. Launch an emulator avd
        2. From command prompt, run: telnet localhost <port>
        3. Copy the auth_token value from ~/.emulator_console_auth_token
        4. Run: auth auth_token
        5. Run: sms pdu <pdu message>
           and verify
    Verify:
        An sms is received from <expected phone number> with
        <expected text> ('How are you?').
    """
    this_function_name = sys._getframe().f_code.co_name
    print(('Running test: %s' % (this_function_name)))
    self._execute_command_and_verify(CMD_SMS_PDU.format(PDU_FORMAT_MESSAGE), util.OK, ASSERT_MSG)
    self._poll_and_verify_sms(MSG_MATCHING_STRING.format(PDU_PHONE_NUMBER, PDU_MESSAGE))

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

  def _poll_and_verify_sms(self, msg_string):
    time.sleep(5)
    adb_binary = os.path.join(os.environ['ANDROID_SDK_ROOT'], 'platform-tools', 'adb')
    print('Clear logcat')
    subprocess.Popen(['adb', 'logcat', '-c'], stderr=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
    print('Launch activity')
    util.launch_application(CONSOLE_TEST_PACKAGE_NAME + '/com.example.smstesthelper.MainActivity')
    time.sleep(1)
    print('Get logcat')
    test_process = subprocess.check_output([adb_binary, 'logcat', '-d'])
    print('Stop activity')
    util.stop_application(CONSOLE_TEST_PACKAGE_NAME)
    is_match_successful = msg_string in str(test_process)
    print('Logcat checked')
    self.assertTrue(is_match_successful, ASSERT_MSG_MATCH_FAILURE)

if __name__ == '__main__':
  print('======= sms Test =======')
  unittest.main()
