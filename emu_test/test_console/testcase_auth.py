#!/usr/bin/env python

"""Test for auth-related commands."""

import os
import sys
import telnetlib
import unittest

from utils import util
from os.path import expanduser
from testcase_base import BaseConsoleTest

AUTH_OUTPUT = 'Android Console: type \\\'help\\\' for a list of commands\r\nOK'


class AuthTest(BaseConsoleTest):
    """This class aims to test auth-related emulator console commands."""

    def setUp(self):
        """Only telnet to emulator, initially not need to run auth command."""
        self.telnet = telnetlib.Telnet(util.SERVER_NAME,
                                       util.CONSOLE_PORT)
        if not util.checkReadUntil(
              self.telnet.read_until(util.OK,
                                     util.TIMEOUT_S)):
            sys.exit(-1)

    def _auth_user_for_emulator_console(self):
        home = expanduser('~')
        token_path = os.path.join(home,
                                  util.CONSOLE_AUTH_TOKEN_FILE_NAME)
        with open(token_path) as f:
            content = f.readlines()
        auth_token = content[0]
        cmd_auth = 'auth %s\n' % auth_token

        is_command_successful, output = util.execute_console_command(
            self.telnet,
            cmd_auth,
            AUTH_OUTPUT)
        self.assertCmdSuccessful(is_command_successful,
                                 'Failed to properly authentication.',
                                 False,
                                 '',
                                 AUTH_OUTPUT,
                                 output)

    def _verify_auth_command_by_enter_help_command(self):
        is_command_successful, output = \
            util.execute_console_command(
                self.telnet,
                util.CMD_HELP,
                util.REGEX_HELP_DISPLAY_AUTH)

        self.assertCmdSuccessful(
            is_command_successful,
            'Failed to properly list all command options.',
            False,
            '',
            'Pattern: \n%s' % util.REGEX_HELP_DISPLAY_AUTH,
            output)

    def test_auth_command(self):
        """
        Test command for: auth <auth_token>
        Test Rail ID: C14595293
        Test steps:
            1. Launch an emulator avd
            2. From command prompt, run: telnet localhost <port>
            3. Copy the auth_token value from ~/.emulator_console_auth_token
            4. Run: auth auth_token, verify 1
            5. Run: help, verify 2
        Verify:
            1. Check the console output is as expected
            2. 'help' command can be entered and executed
        """
        self._auth_user_for_emulator_console()
        self._verify_auth_command_by_enter_help_command()

if __name__ == '__main__':
    print('======= auth Test =======')
    unittest.main()
