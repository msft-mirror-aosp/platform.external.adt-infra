"""Tests for rotate-related commands."""

import unittest
import sys
import time
from . import testcase_base
from .utils import util


CMD_ROTATE = 'rotate\n'
CMD_GET_ORIENTATION = 'sensor get orientation\n'
ROTATE_90_ORIENTATION = '0:0:-1.5708'
ROTATE_180_ORIENTATION = '-0:0:-3.14159'
ROTATE_270_ORIENTATION = '0:0:1.5708'
ROTATE_360_ORIENTATION = '0:0:0'
ROTATE_CMD_OUTPUT = ''
ASSERT_MSG_ROTATE = 'Failed to execute rotate command'
ASSERT_MSG_ORIENTATION = 'Failed to fetch orientation values'


class OrientationTest(testcase_base.BaseConsoleTest):
  """This class aims to test rotate-related emulator console commands."""

  def __init__(self, method_name=None):
    if method_name:
      super(OrientationTest, self).__init__(method_name)
    else:
      super(OrientationTest, self).__init__()

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

  def test_orientation(self):
    """Test command for: rotate

    TT ID: a802e7d8-75e6-44fd-ac9c-5af3f8d5d3a2
    Test steps:
      1. Run: rotate
      2. Run: sensor get orientation , to verify rotate is 90 degree.
      3. Run: rotate
      4. Run: sensor get orientation , to verify rotate is 180 degree.
      5. Run: rotate
      6. Run: sensor get orientation , to verify rotate is 270 degree.
      7. Run: rotate
      8. Run: sensor get orientation , to verify rotate is 360 degree.
    Verify:
      Check to orientation and rotation of the launched app.
    """
    this_function_name = sys._getframe().f_code.co_name
    print(('Running test: %s' % (this_function_name)))
    # Rotate 90 degree and check orientation values.
    self._execute_command_and_verify(CMD_ROTATE, ROTATE_CMD_OUTPUT, ASSERT_MSG_ROTATE)
    time.sleep(util.CMD_WAIT_TIMEOUT_S)
    self._execute_command_and_verify(CMD_GET_ORIENTATION, ROTATE_90_ORIENTATION, ASSERT_MSG_ORIENTATION)
    # Rotate 180 degree and check orientation values.
    self._execute_command_and_verify(CMD_ROTATE, ROTATE_CMD_OUTPUT, ASSERT_MSG_ROTATE)
    time.sleep(util.CMD_WAIT_TIMEOUT_S)
    self._execute_command_and_verify(CMD_GET_ORIENTATION, ROTATE_180_ORIENTATION, ASSERT_MSG_ORIENTATION)
    # Rotate 270 degree and check orientation values.
    self._execute_command_and_verify(CMD_ROTATE, ROTATE_CMD_OUTPUT, ASSERT_MSG_ROTATE)
    time.sleep(util.CMD_WAIT_TIMEOUT_S)
    self._execute_command_and_verify(CMD_GET_ORIENTATION, ROTATE_270_ORIENTATION, ASSERT_MSG_ORIENTATION)
    # Rotate 360 degree and check orientation values.
    self._execute_command_and_verify(CMD_ROTATE, ROTATE_CMD_OUTPUT, ASSERT_MSG_ROTATE)
    time.sleep(util.CMD_WAIT_TIMEOUT_S)
    self._execute_command_and_verify(CMD_GET_ORIENTATION, ROTATE_360_ORIENTATION, ASSERT_MSG_ORIENTATION)


if __name__ == '__main__':
  print('======= rotate Test =======')
  unittest.main()
