#!/usr/bin/env python

"""
Test for help-related commands.
"""

import os
import sys
import time
import inspect
import unittest
import telnetlib

from os.path import expanduser
from testcase_base import BaseConsoleTest

import console_utils.console_utils as console_utils

CMD_HELP = 'help\n'
REGEX_HELP_DISPLAY_NO_AUTH = \
    '.*\n.*\n.*help.*\n.*avd.*\n.*auth.*\n.*quit\|exit.*\n.*\n.*\nOK'
REGEX_HELP_DISPLAY_AUTH = \
    '.*\n.*\n.*help.*\n.*event.*\n.*geo.*\n.*gsm.*\n.*cdma.*\n.*crash.*\n' \
    '.*kill.*\n.*network.*\n.*power.*\n.*quit\|exit.*\n.*redir.*\n' \
    '.*sms.*\n.*avd.*\n.*qemu.*\n.*sensor.*\n.*finger.*\n.*debug.*\n.*\n.*\nOK'


class HelpTest(BaseConsoleTest):
    """
    This class aims to test help-related emulator console commands.
    """

    def setUp(self):
        """
        Only telnet to emulator, initially not need to run auth command.
        """
        self.telnet = telnetlib.Telnet(console_utils.SERVER_NAME,
                                       console_utils.CONSOLE_PORT)
        if not console_utils.checkReadUntil(
                self.telnet.read_until(console_utils.OK, console_utils.TIMEOUT_S)):
            sys.exit(-1)

    def _help_command(self, user_auth):
        is_command_successful = False
        expected_regex_pattern = None

        for i in range(console_utils.NUM_MAX_TRIALS):
            print('Running %s, user authorized: %s, trial #%d' %
                  (inspect.stack()[0][3], user_auth, i))

            self.telnet.write(CMD_HELP)
            time.sleep(console_utils.CMD_WAIT_TIMEOUT_S)

            output_help = console_utils.parseOutput(self.telnet)

            if user_auth:
                expected_regex_pattern = REGEX_HELP_DISPLAY_AUTH
            else:
                expected_regex_pattern = REGEX_HELP_DISPLAY_NO_AUTH

            is_command_successful = console_utils.patternMatchOutput(
                output_help,
                expected_regex_pattern)

            if is_command_successful:
                break

            time.sleep(console_utils.TRIAL_WAIT_TIMEOUT_S)

        self.assertCmdSuccessful(
            is_command_successful,
            'Failed to properly list all command options.',
            False,
            '',
            'Pattern: \n%s' % expected_regex_pattern,
            output_help)

    def _auth_user_for_emulator_console(self):
        home = expanduser('~')
        token_path = os.path.join(home,
                                  console_utils.CONSOLE_AUTH_TOKEN_FILE_NAME)
        with open(token_path) as f:
            content = f.readlines()
        auth_token = content[0]
        cmd_auth = 'auth %s\n' % (auth_token)
        self.telnet.write(cmd_auth)
        self.wait_on_windows()
        if not console_utils.checkReadUntil(
                self.telnet.read_until(console_utils.OK,
                                       console_utils.TIMEOUT_S)):
            sys.exit(-1)

    def test_help_command(self):
        """
        Test command for: help
        Test Rail ID: C14578962
        """
        self._help_command(user_auth=False)
        self._auth_user_for_emulator_console()
        self._help_command(user_auth=True)

if __name__ == '__main__':
    print('======= Port Test =======')
    unittest.main()
