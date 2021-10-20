"""Tests for call-related commands."""

import unittest
import sys

from . import testcase_base
from .utils import util

CALL_NUMBER = '1234567890'
CMD_GSM = 'gsm {} {}\n'
CMD_CALL = 'call'
CMD_LIST = 'list'
CMD_CANCEL = 'cancel'
CMD_HOLD = 'hold'
CMD_BUSY = 'busy'
CMD_ACCEPT = 'accept'
STATUS_INCOMING = 'incoming'
STATUS_HOLD = 'held'
STATUS_ACTIVE = 'active'
CMD_GSM_LIST = 'gsm list\n'

STATUS_TEMPLATE = 'inbound from {} : {}'
ASSERT_MSG = 'Failed to execute {} command'


class PhoneCallTest(testcase_base.BaseConsoleTest):
  """This class aims to test call-related emulator console commands."""

  def __init__(self, method_name=None):
    if method_name:
      super(PhoneCallTest, self).__init__(method_name)
    else:
      super(PhoneCallTest, self).__init__()

  def tearDown(self):
    if (self._execute_command_and_verify(CMD_GSM_LIST, util.OK, ASSERT_MSG.format(CMD_LIST)) is True):
      self._execute_command_and_verify(CMD_GSM.format(CMD_CANCEL, CALL_NUMBER), util.OK, ASSERT_MSG.format(CMD_CANCEL))

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

  def test_inbound_call(self):
    """Test for command: gsm call <phonenumber>.
    TT ID: 5c8892ba-e458-427c-a21d-19758e376749
    Test steps:
       1. Run: gsm call <phonenumber>
       2. Run: gsm list to verify that call is received and is from same number.
       3. Run: gms cancel <phoneNumber> to cancel the call
    Verify:
       1. Emulator displays an incoming call from the <phoneNumber>
       2. Phone call is terminated.
    """
    this_function_name = sys._getframe().f_code.co_name
    print(('Running test: %s' % (this_function_name)))
    self._execute_command_and_verify(CMD_GSM.format(CMD_CALL, CALL_NUMBER), util.OK, ASSERT_MSG.format(CMD_CALL))
    self._execute_command_and_verify(CMD_GSM_LIST, STATUS_TEMPLATE.format(CALL_NUMBER, STATUS_INCOMING), ASSERT_MSG.format(CMD_LIST))
    self._execute_command_and_verify(CMD_GSM.format(CMD_CANCEL, CALL_NUMBER), util.OK, ASSERT_MSG.format(CMD_CANCEL))

  @unittest.skip("b/203462196")
  def test_inbound_call_hold(self):
    """Test for command: gsm hold <phonenumber>.
    Test steps:
      1. Run: gsm call <phonenumber>
      2. Run: gsm hold <phoneNumber>
      3. Run: gsm list to verify that call is held and is from same number.
    Verify:
      1. Emulator displays an incoming call from the <phoneNumber>
      2. Phone call is terminated.
    """
    this_function_name = sys._getframe().f_code.co_name
    print(('Running test: %s' % (this_function_name)))
    self._execute_command_and_verify(CMD_GSM.format(CMD_CALL, CALL_NUMBER), util.OK, ASSERT_MSG.format(CMD_CALL))
    self._execute_command_and_verify(CMD_GSM.format(CMD_HOLD, CALL_NUMBER), util.OK, ASSERT_MSG.format(CMD_HOLD))
    self._execute_command_and_verify(CMD_GSM_LIST, STATUS_TEMPLATE.format(CALL_NUMBER, STATUS_HOLD),
                                   ASSERT_MSG.format(CMD_LIST))
    self._execute_command_and_verify(CMD_GSM.format(CMD_CANCEL, CALL_NUMBER), util.OK, ASSERT_MSG.format(CMD_CANCEL))

  def test_inbound_call_accept(self):
    """Test for command: gsm accept <phonenumber>.
    Test steps:
        1. Run: gsm call <phonenumber>
        2. Run: gsm accept <phoneNumber>
        3. Run: gsm list to verify that call is active and is from same number.
    Verify:
        1. Emulator displays an incoming call from the <phoneNumber>
        2. Phone call is terminated.
    """
    this_function_name = sys._getframe().f_code.co_name
    print(('Running test: %s' % (this_function_name)))
    self._execute_command_and_verify(CMD_GSM.format(CMD_CALL, CALL_NUMBER), util.OK, ASSERT_MSG.format(CMD_CALL))
    self._execute_command_and_verify(CMD_GSM.format(CMD_ACCEPT, CALL_NUMBER), util.OK, ASSERT_MSG.format(CMD_ACCEPT))
    self._execute_command_and_verify(CMD_GSM_LIST, STATUS_TEMPLATE.format(CALL_NUMBER, STATUS_ACTIVE),
                                       ASSERT_MSG.format(CMD_LIST))
    self._execute_command_and_verify(CMD_GSM.format(CMD_CANCEL, CALL_NUMBER), util.OK, ASSERT_MSG.format(CMD_CANCEL))

  @unittest.skip("b/203463348")
  def test_inbound_call_busy(self):
    """Test for command: gsm busy <phonenumber>.
    Test steps:
      1. Run: gsm call <phonenumber>
      2. Run: gsm busy <phoneNumber>
      3. Run: gsm list to verify that call is terminated .
    Verify:
      1. Emulator displays an incoming call from the <phoneNumber>
      2. Phone call is terminated.
    """
    this_function_name = sys._getframe().f_code.co_name
    print(('Running test: %s' % (this_function_name)))
    util.make_inbound_call(CALL_NUMBER)
    self._execute_command_and_verify(CMD_GSM.format(CMD_BUSY, CALL_NUMBER), util.OK, ASSERT_MSG.format(CMD_BUSY))
    self._execute_command_and_verify(CMD_GSM_LIST, util.OK,
                                     ASSERT_MSG.format(CMD_LIST))

if __name__ == '__main__':
  print('======= Call Test =======')
  unittest.main()