"""
Tests for port-related commands
"""

import unittest
import console_utils.console_utils as console_utils
import time
import inspect
from testcase_base import BaseConsoleTest

NUM_MAX_TRIALS = 3
TRIAL_WAIT_TIMEOUT = 0.5
CMD_WAIT_TIMEOUT = 0.5

EMULATOR_PORT = "5554"
HOST_PORT = "5556"

CMD_REDIR_LIST = "redir list\n"
CMD_REDIR_ADD = "redir add tcp:%s:%s\n" % (HOST_PORT, EMULATOR_PORT)
CMD_REDIR_DEL = "redir del tcp:%s\n" % (HOST_PORT)


class PortTest(BaseConsoleTest):

    def _list_redir_cmd(self):
        is_cmd_succ = False

        for i in range(NUM_MAX_TRIALS):
            print("Running %s,  trial #%s" %
                  (inspect.stack()[0][3], str(i + 1)))
            self.telnet.write(CMD_REDIR_LIST)
            time.sleep(CMD_WAIT_TIMEOUT)
            output_redir_list = console_utils.parseOutput(self.telnet)
            is_cmd_succ = (output_redir_list == console_utils.PORT_NO_REDIR)

            if is_cmd_succ:
                break

            time.sleep(TRIAL_WAIT_TIMEOUT)

        self.assertCmdSuccessful(
            is_cmd_succ,
            "Failed to properly list port redirection.",
            False,
            "",
            console_utils.PORT_NO_REDIR, output_redir_list)

        return output_redir_list

    def _add_port_redir_cmd(self):
        is_cmd_succ = False

        for i in range(NUM_MAX_TRIALS):
            print("Running %s, trial #%s" %
                  (inspect.stack()[0][3], str(i + 1)))

            self.telnet.write(CMD_REDIR_ADD)
            time.sleep(CMD_WAIT_TIMEOUT)
            output_redir_add = console_utils.parseOutput(self.telnet)
            assert output_redir_add == console_utils.OK

            self.telnet.write(CMD_REDIR_LIST)
            time.sleep(CMD_WAIT_TIMEOUT)
            output_redir_list = console_utils.parseOutput(self.telnet)

            is_cmd_succ = (output_redir_list == console_utils.PORT_REDIR_ADD)

            if is_cmd_succ:
                break

            time.sleep(TRIAL_WAIT_TIMEOUT)

        self.assertCmdSuccessful(
            is_cmd_succ,
            "Failed to properly add a new port redirection",
            False,
            "",
            console_utils.PORT_REDIR_ADD,
            output_redir_add)

    def _del_port_redir_cmd(self):
        is_cmd_succ = False

        for i in range(NUM_MAX_TRIALS):
            print("Running : %s, trial #%s" %
                  (inspect.stack()[0][3], str(i+1)))

            self.telnet.write(CMD_REDIR_DEL)
            time.sleep(CMD_WAIT_TIMEOUT)
            output_redir_del = console_utils.parseOutput(self.telnet)
            assert output_redir_del == console_utils.OK

            is_cmd_succ = (self._list_redir_cmd() == console_utils.PORT_NO_REDIR)

            if is_cmd_succ:
                break

            time.sleep(TRIAL_WAIT_TIMEOUT)

        self.assertCmdSuccessful(
            is_cmd_succ,
            "Failed to properly delete a port redirection",
            False,
            "",
            console_utils.OK,
            output_redir_del)

    def test_list_port_redir(self):
        """
        Test for command: redir list
        TR ID: C14594979
        """
        print("Running test: %s" % (inspect.stack()[0][3]))
        self._list_redir_cmd()

    def test_add_new_port_and_delete_port_redir(self):
        """
        Test for commands: redir add <tcp_or_udp>:<5556>:<port_of_emulator>
                           redir def <tcp_or_udp>:<5556>
        TR ID: C14594979
        b/210442:
            command "redir del" doesn't work on API 23/24 on Windows; but Linux.
        """

        print("Running test: %s" % (inspect.stack()[0][3]))
        self._add_port_redir_cmd()
        self._del_port_redir_cmd()


if __name__ == '__main__':
    print "======= Port Test ======="
    unittest.main()
