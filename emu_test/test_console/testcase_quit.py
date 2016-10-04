#!/usr/bin/env python

"""
Test for quit/exit-related commands.
"""

import unittest
import console_utils.console_utils as console_utils
from testcase_base import BaseConsoleTest

CMD_QUIT = 'quit\n'
CMD_EXIT = 'exit\n'
EMPTY_OUTPUT = ''


class QuitTest(BaseConsoleTest):
    """
    This class aims to test quit/exit-related emulator console commands.
    """

    def tearDown(self):
        """
        Override superclass's method:
          In the end of each test case, it already exited from emulator.
        """

    def _execute_command_and_verify(self, command):
        is_command_successful = False

        self.telnet.write(command)
        self.wait_on_windows()

        output_exit = console_utils.parseOutput(self.telnet)
        is_command_successful = (output_exit == EMPTY_OUTPUT)

        self.telnet.close()

        self.assertCmdSuccessful(
            is_command_successful,
            'Failed to properly quit/exit emulator.',
            False,
            '',
            EMPTY_OUTPUT,
            output_exit)

    def test_quit_command(self):
        """
        Test command for: quit
        Test Rail ID: 14595303
        """
        self._execute_command_and_verify(CMD_QUIT)

    def test_exit_command(self):
        """
        Test command for: exit
        Test Rail ID: 14595303
        """
        self._execute_command_and_verify(CMD_EXIT)

if __name__ == '__main__':
    print('======= Quit/Exit Test =======')
    unittest.main()
