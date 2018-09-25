"""Test for restart-related commands."""

import inspect
import sys
import time
import unittest

import testcase_base
from utils import util

RESTART_CMD = 'restart\n'
RESTART_RESPONSE = 'OK: restarting emulator, bye bye.*\n.*OK'
RESTART_WAIT_TIMEOUT_S = 30 # This timeout needs to calibrate on buildbot.


class RestartTest(testcase_base.BaseConsoleTest):
  """This class aims to test restart-related emulator console commands."""

  def __init__(self, method_name=None, avd=None, builder_name=None):
    if method_name:
      super(RestartTest, self).__init__(method_name)
    else:
      super(RestartTest, self).__init__()
    self.avd = avd
    self.builder_name = builder_name

  def _telnet_to_emulator_and_auth(self):
    """Telnet to emulator and auth token"""
    auth_token = util.get_auth_token()
    self.telnet = util.telnet_emulator()
    self.telnet.write('%s %s\n' % (util.AUTH, auth_token))
    util.wait_on_windows()
    if (not util.check_read_until(
            self.telnet.read_until(util.OK, util.TIMEOUT_S))):
      sys.exit(-1)

  def _execute_command_and_verify(self, command, expected_output, assert_msg):
    """Executes console command and verify output.

    Args:
        command: Console command to be executed.
        expected_output: Expected console output.
        assert_msg: Assertion message.
    """
    is_command_successful, output = util.execute_console_command(
        self.telnet, command, expected_output)

    print output

    self.assert_cmd_successful(is_command_successful, assert_msg, False, '',
                               'Pattern:\n%s' % expected_output, output)

  def test_restart_command(self):
    """Test command for: restart.

    TODO: TT ID:
    Test steps:
      1. Launch an emulator avd
      2. From command prompt, run: telnet localhost <port>
      3. Run: auth <token>
      4. Run: restart, and verify output
      5. Repeat step 2-3, and verify it works, which means emulator restarted
    """
    print 'Running test: %s' % (inspect.stack()[0][3])

    self.telnet.write(RESTART_CMD)
    self.assertTrue(RESTART_RESPONSE, self.telnet.read_all())

    time.sleep(RESTART_WAIT_TIMEOUT_S)
    self._telnet_to_emulator_and_auth()


if __name__ == '__main__':
  print '======= restart Test ======='
  unittest.main()
