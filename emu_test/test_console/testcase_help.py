"""Test for help-related commands."""

import inspect
import sys
import telnetlib
import unittest

from . import testcase_base
from .utils import util


class HelpTest(testcase_base.BaseConsoleTest):
  """This class aims to test help-related emulator console commands."""

  def __init__(self, method_name=None):
    if method_name:
      super(HelpTest, self).__init__(method_name)
    else:
      super(HelpTest, self).__init__()

  def setUp(self):
    """Only telnet to emulator, initially not need to run auth command."""
    self.telnet = telnetlib.Telnet(util.SERVER_NAME, util.CONSOLE_PORT)
    if not util.check_read_until(
        self.telnet.read_until(bytes(util.OK, 'utf-8'), util.TIMEOUT_S)):
      sys.exit(-1)

  def _help_command(self, expected_output):
    """Executes help command and verifies output.

    Args:
        expected_output: Expected console output for help commands.
    """
    output = util.execute_help_command(self.telnet, util.CMD_HELP)
    is_command_successful = True
    for cmd in expected_output:
      if cmd not in output:
        is_command_successful = False

    self.assert_cmd_successful(
        is_command_successful,
        'Failed to properly list all command options.',
        False, '', 'Pattern: \n%s' % expected_output, output)

  def _help_verbose_command(self, expected_output):
    """Executes help-verbose command and verifies output.

    Args:
        expected_output: Expected console output for help-vebose command.
    """
    output = util.execute_help_command(self.telnet, util.CMD_HELP_VERBOSE)
    is_command_successful = True
    for cmd in expected_output:
      if cmd not in output:
        is_command_successful = False

    self.assert_cmd_successful(
        is_command_successful,
        'Failed to properly list all command options.',
        False, '', 'Pattern: \n%s' % expected_output, output)

  def _auth_user_for_emulator_console(self):
    """Authorization user."""
    auth_token = util.get_auth_token()
    self.telnet = util.telnet_emulator()
    self.telnet.write(bytes('%s %s\n' % (util.AUTH, auth_token), 'utf-8'))
    util.wait_on_windows()
    if (not util.check_read_until(
        self.telnet.read_until(bytes(util.OK, 'utf-8'), util.TIMEOUT_S))):
      sys.exit(-1)

  def test_help_command(self):
    """Test command for: help.

    TT ID: b4bed6f1-062d-4a52-b8c2-b9eb0c445ab0
    Test steps:
      1. Launch an emulator avd
      2. From command prompt, run: telnet localhost <port>
      3. Run: help, and verify 1
      4. Copy the auth_token value from ~/.emulator_console_auth_token
      5. Run: auth auth_token
      6. Run: help, and verify 2
    Verify:
      1. help, auth, avd and quit/exit commands are available
      2. crash, kill, redir, power, event, avd ,finger, geo, sms, cdma,
         gsm and rotate commands are available
    """
    print(('Running test: %s' % (inspect.stack()[0][3])))
    self._help_command(util.CMDS_FOR_HELP_NO_AUTH)
    self._help_verbose_command(util.CMDS_FOR_HELP_VERBOSE_NO_AUTH)

    self._auth_user_for_emulator_console()

    self._help_command(util.CMDS_FOR_HELP_AUTH)
    self._help_verbose_command(util.CMDS_FOR_HELP_VERBOSE_DISPLAY_AUTH)


if __name__ == '__main__':
  print('======= help Test =======')
  unittest.main()
