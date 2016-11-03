"""Test for help-related commands."""

import inspect
import sys
import telnetlib
import unittest

import testcase_base
from utils import util


class HelpTest(testcase_base.BaseConsoleTest):
  """This class aims to test help-related emulator console commands."""

  def setUp(self):
    """Only telnet to emulator, initially not need to run auth command."""
    self.telnet = telnetlib.Telnet(util.SERVER_NAME, util.CONSOLE_PORT)
    if not util.check_read_until(
        self.telnet.read_until(util.OK, util.TIMEOUT_S)):
      sys.exit(-1)

  def _help_command(self, expected_output):
    """Executes help command and verifies output.

    Args:
        expected_output: Expected console output for help commands.
    """
    is_command_successful, output = util.execute_console_command(
        self.telnet, util.CMD_HELP, expected_output)

    self.assert_cmd_successful(
        is_command_successful,
        'Failed to properly list all command options.',
        False, '', 'Pattern: \n%s' % expected_output, output)

  def _auth_user_for_emulator_console(self):
    """Authorization user."""
    auth_token = util.get_auth_token()
    self.telnet = util.telnet_emulator()
    self.telnet.write('%s %s\n' % (util.AUTH, auth_token))
    util.wait_on_windows()
    if (not util.check_read_until(
        self.telnet.read_until(util.OK, util.TIMEOUT_S))):
      sys.exit(-1)

  def test_help_command(self):
    """Test command for: help.

    Test Rail ID: C14578962
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
    print 'Running test: %s' % (inspect.stack()[0][3])
    self._help_command(util.REGEX_HELP_DISPLAY_NO_AUTH)
    self._auth_user_for_emulator_console()
    self._help_command(util.REGEX_HELP_DISPLAY_AUTH)


if __name__ == '__main__':
  print '======= help Test ======='
  unittest.main()
