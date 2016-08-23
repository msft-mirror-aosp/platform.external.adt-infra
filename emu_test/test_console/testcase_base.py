"""
This class is a parent class for all subordniate "testcase_" classes such as
testcase_battery.py, testcase_call.py, testcase_event.py, and testcaes_port.py.
It uses telnetlib to connect to telnet in order to communicate with emulator.
There is some sync problem or potential bug in emualtor, particularly observable when run on Windows machine:
(https://code.google.com/p/android/issues/detail?id=220171)
The issue was handled by giving timeout parameter to the read_until function of python telnetlib
and give wait time of 0.5 after each write onto the telnet stream.
"""

import unittest
import telnetlib
from subprocess import check_output
import subprocess
import os
from os.path import expanduser
import console_utils.console_utils as console_utils
import time
import inspect

TIMEOUT = 1

class BaseConsoleTest(unittest.TestCase):
    def wait_on_windows(self):
        if os.name == "nt":
            time.sleep(0.5)

    def setUp(self):
        home = expanduser("~")
        token_path = os.path.join(home, ".emulator_console_auth_token")
        with open(token_path) as f:
            content = f.readlines()
        auth_token = content[0]
        self.telnet = telnetlib.Telnet("localhost", 5554)
        if not console_utils.checkReadUntil(self.telnet.read_until("OK", TIMEOUT)):
            sys.exit(-1)
        self.telnet.write("auth " + auth_token + "\n")
        self.wait_on_windows()
        if not console_utils.checkReadUntil(self.telnet.read_until("OK", TIMEOUT)):
            sys.exit(-1)

    def tearDown(self):
        self.telnet.write("exit\n")
        self.wait_on_windows()
        self.telnet.close()

    def assertCmdSuccessful(self, isCmdSuccessful, assertionMsg, hasStatus, status):
        if hasStatus:
            print "Test result: " + inspect.stack()[0][3] + " status matches " + status + " => " + str(isCmdSuccessful)
        else:
            print "Test result: " + inspect.stack()[0][3] + " => " + str(isCmdSuccessful)
        self.assertTrue(isCmdSuccessful, assertionMsg)


if __name__ == '__main__':
    print "======= Base Console Test ======="
    unittest.main()
