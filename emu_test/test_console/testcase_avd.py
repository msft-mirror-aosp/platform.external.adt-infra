"""Test for avd-related emulator console commands."""

import inspect
import unittest

from . import testcase_base
from .utils import util

CMD_HELP_AVD = 'help avd\n'
CMD_AVD_STOP = 'avd stop\n'
CMD_AVD_START = 'avd start\n'
CMD_AVD_STATUS = 'avd status\n'

AVD_STOPPED = 'virtual device is stopped.*\nOK'
AVD_RUNNING = 'virtual device is running.*\nOK'


class AvdTest(testcase_base.BaseConsoleTest):
  """This class aims to test avd-related emulator console commands."""

  def __init__(self, method_name=None):
    if method_name:
      super(AvdTest, self).__init__(method_name)
    else:
      super(AvdTest, self).__init__()

  @unittest.skip("Debugging for b/215910720")
  def test_avd_stop_and_start(self):
    """Test command for: avd stop, avd start, avd status.

    Test Rail ID: C14595362
    Test steps:
      1. Launch an emulator avd
      2. From command prompt, run: telnet localhost <port>
      3. Copy the auth_token value from ~/.emulator_console_auth_token
      4. Run: auth auth_token
      5. Run: avd stop
      6. Run: avd status and verify 1
      7. Run: avd start
      8. Run avd status and verify 2
    Verify:
      1. Check console output is 'virtual device is stopped'
      2. Check console output is 'virtual device is running'
    """
    print(('Running test: %s' % (inspect.stack()[0][3])))
    self._execute_console_command_and_verify(CMD_AVD_STOP, util.OK)
    self._execute_console_command_and_verify(CMD_AVD_STATUS, AVD_STOPPED)
    self._execute_console_command_and_verify(CMD_AVD_START, util.OK)
    self._execute_console_command_and_verify(CMD_AVD_STATUS, AVD_RUNNING)

  def _execute_console_command_and_verify(self, command, expected_output):
    """Executes emulator console command and verify the command output.

    Args:
        command: Console command to be executed.
        expected_output: The expected command output.
    """
    is_command_successful, output = util.execute_console_command(
        self.telnet, command, expected_output)

    self.assert_cmd_successful(
        is_command_successful, 'Failed to properly execute: %s' % command,
        False, '', expected_output, output)


if __name__ == '__main__':
  print('======= avd Test =======')
  unittest.main()
