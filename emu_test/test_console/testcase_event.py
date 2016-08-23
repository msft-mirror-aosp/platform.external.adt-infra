"""
Tests for event-related commands
"""

import unittest
import telnetlib
from subprocess import check_output
import subprocess
import console_utils.console_utils as console_utils
import time
import inspect
from testcase_base import BaseConsoleTest

NUM_MAX_TRIALS = 3
TRIAL_WAIT_TIMEOUT = 0.5
CMD_WAIT_TIMEOUT = 0.5

class EventTest(BaseConsoleTest):

    def test_listEventAliases(self):
        """
        Test for command: event types
        """
        isCmdSuccessful = True
        for i in range(0, NUM_MAX_TRIALS):
            print "Running test: " + inspect.stack()[0][3] + ", trial #" + str(i+1)
            self.telnet.write("event types\n")
            time.sleep(CMD_WAIT_TIMEOUT)
            output_event_aliases = console_utils.parseOutputForEV(self.telnet)
            correct_output = console_utils.readStringFromFile(console_utils.EVENTS_EV_TYPES_FILENAME)
            isCmdSuccessful = (console_utils.removeAllSpaces(output_event_aliases) == console_utils.removeAllSpaces(correct_output))
            if isCmdSuccessful:
                break
            time.sleep(TRIAL_WAIT_TIMEOUT)
        self.assertCmdSuccessful(isCmdSuccessful, "Listing all aliases of events failed", False, "")

    def verifyEventsNoAlias(self, command):
        isCmdSuccessful = True
        for i in range(0, NUM_MAX_TRIALS):
            print "Running test: " + inspect.stack()[0][3] + " " + command.strip() + ", trial #" + str(i+1)
            self.telnet.write(command)
            time.sleep(CMD_WAIT_TIMEOUT)
            output_event_listAll = console_utils.parseOutput(self.telnet)
            isCmdSuccessful = (output_event_listAll == console_utils.EVENTS_CODE_NO_ALIAS)
            if isCmdSuccessful:
                break
            time.sleep(TRIAL_WAIT_TIMEOUT)
        self.assertCmdSuccessful(isCmdSuccessful, "test_listAllCodeAliases failed, output mismatch: fail to run " + command + " properly", False, "")

    def verifyAllEventsNoAlias(self):
        self.verifyEventsNoAlias("event codes EV_SYN\n")
        self.verifyEventsNoAlias("event codes EV_MSC\n")
        self.verifyEventsNoAlias("event codes EV_SW\n")
        self.verifyEventsNoAlias("event codes EV_LED\n")
        self.verifyEventsNoAlias("event codes EV_SND\n")
        self.verifyEventsNoAlias("event codes EV_REP\n")
        self.verifyEventsNoAlias("event codes EV_FF\n")
        self.verifyEventsNoAlias("event codes EV_PWR\n")
        self.verifyEventsNoAlias("event codes EV_FF_STATUS\n")
        self.verifyEventsNoAlias("event codes EV_MAX\n")

    def verifyEventCodes(self, command, filename):
        isCmdSuccessful = True
        for i in range(0, NUM_MAX_TRIALS):
            print "Running test: " + inspect.stack()[0][3] + " " + command.strip() + " verified against " + filename.strip() + ", trial #" + str(i+1)
            self.telnet.write(command)
            time.sleep(CMD_WAIT_TIMEOUT)
            output_event_listAll = console_utils.parseOutputForEV(self.telnet)
            correct_output = console_utils.readStringFromFile(filename)
            isCmdSuccessful = (console_utils.removeAllSpaces(output_event_listAll) == console_utils.removeAllSpaces(correct_output))
            if isCmdSuccessful:
                break
            time.sleep(TRIAL_WAIT_TIMEOUT)
        self.assertCmdSuccessful(isCmdSuccessful, "test_listAllCodeAliases failed, output mismatch: fail to run " + command + " properly", False, "")

    def verifyAllEventCodes(self):
        self.verifyEventCodes("event codes EV_KEY\n", console_utils.EVENTS_CODE_EV_KEY_FILENAME)
        self.verifyEventCodes("event codes EV_REL\n", console_utils.EVENTS_CODE_EV_REL_FILENAME)
        self.verifyEventCodes("event codes EV_ABS\n", console_utils.EVENTS_CODE_EV_ABS_FILENAME)

    def test_listAllCodeAliases(self):
        """
        Test for command: event codes <type>" (for example: event codes EV_REL)
        """
        self.verifyAllEventCodes()
        self.verifyAllEventsNoAlias()

    def test_simulateKeyPresses(self):
        """
        Test for command: event text <message>
        """
        # b/204884
        pass


if __name__ == '__main__':
    print "======= Event Test ======="
    unittest.main()
