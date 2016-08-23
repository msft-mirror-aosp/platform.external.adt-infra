"""
Tests for port-related commands
"""

import unittest
import telnetlib
from subprocess import check_output
import console_utils.console_utils as console_utils
from os.path import expanduser
import time
import inspect
from testcase_base import BaseConsoleTest

NUM_MAX_TRIALS = 3
TRIAL_WAIT_TIMEOUT = 0.5
CMD_WAIT_TIMEOUT = 0.5

class PortTest(BaseConsoleTest):

    def test_listPortRedir(self):
        """
        Test for command: redir list
        """
        isCmdSuccessful = True
        for i in range(0, NUM_MAX_TRIALS):
            print "Running test: " + inspect.stack()[0][3] + ", trial #" + str(i+1)
            self.telnet.write("redir list\n")
            time.sleep(CMD_WAIT_TIMEOUT)
            output_redir_list = console_utils.parseOutput(self.telnet)
            isCmdSuccessful = (output_redir_list == "no active redirections\r\nOK")
            if isCmdSuccessful:
                break
            time.sleep(TRIAL_WAIT_TIMEOUT)
        self.assertCmdSuccessful(isCmdSuccessful, "Failed to properly list port redirections", False, "")

    def test_addNewPortRedir(self):
        """
        Test for command: redir add <tcp_or_udp>:<5556>:<port_of_emulator>
        """
        # b/204883
        pass

    def test_deletePortRedir(self):
        """
        Test for command: redir del <tcp_or_udp>:5556
        """
        # b/204883
        pass


if __name__ == '__main__':
    print "======= Port Test ======="
    unittest.main()
