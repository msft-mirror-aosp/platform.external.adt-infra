"""
Tests for call-related commands
"""

import unittest
import telnetlib
from subprocess import check_output
import console_utils.console_utils as console_utils
import subprocess
import os
import time
import requests
import json
from os.path import expanduser
import inspect
from testcase_base import BaseConsoleTest

TESTCASE_CALL_DIR = os.path.dirname(os.path.realpath(__file__))
SERVLET_TELEPHONY = "http://localhost:8080/TelephonyManagerService"

SCRIPT_INSTALL_APK = TESTCASE_CALL_DIR + "/installAPK.sh"
SCRIPT_RUN_ADB_SHELL = TESTCASE_CALL_DIR + "/runADBShell.sh"

NUM_MAX_TRIALS = 3
SETUP_WAIT_TIMEOUT = 5
TRIAL_WAIT_TIMEOUT = 0.5
CMD_WAIT_TIMEOUT = 3

CALL_STATE_IDLE = 0
CALL_STATE_RINGING = 1
CALL_STATE_OFFHOOK = 2

CALL_NUMBER = "1234567890"

class PhoneCallTest(BaseConsoleTest):

    @classmethod
    def runScriptRunADBShell(cls):
        proc_installAPK = subprocess.Popen(["python", TESTCASE_CALL_DIR + "/runADBShell.py"])
        return proc_installAPK

    @classmethod
    def setUpClass(cls):
        res_portRedirect = subprocess.call(["adb", "-s", "emulator-5554", "-e", "forward", "tcp:8080", "tcp:8081"])
        res_runInstallAPKScript = subprocess.call(["python", TESTCASE_CALL_DIR + "/installAPK.py"])
        cls.runScriptRunADBShell()
        time.sleep(SETUP_WAIT_TIMEOUT)

    def processRequestTelephonyService(self, payload):
        r = requests.post(SERVLET_TELEPHONY, data=json.dumps(payload))
        if r.raise_for_status():
            print "Servlet Error: Post request to " + SERVLET_TELEPHONY + " failed"
            return False
        r_json = r.json()
        if r_json["isFail"]:
            print "Servlet Error: Failure occurred in servlet side => " + SERVLET_TELEPHONY
            return False
        return int(r_json["description"])

    def cancel_inbound_call(self):
        self.telnet.write("gsm cancel " + CALL_NUMBER + "\n")
        time.sleep(CMD_WAIT_TIMEOUT)

    def cancel_inbound_call_verification(self):
        isCmdSuccessful = True
        for i in range(0, NUM_MAX_TRIALS):
            print "Running test: " + inspect.stack()[0][3] + ", trial #" + str(i+1)
            self.telnet.write("gsm cancel " + CALL_NUMBER + "\n")
            time.sleep(CMD_WAIT_TIMEOUT)
            output_cancel_inbound = console_utils.parseOutput(self.telnet)
            isCmdSuccessful = (output_cancel_inbound == console_utils.OK)
            if isCmdSuccessful:
                break
            time.sleep(TRIAL_WAIT_TIMEOUT)
        self.assertCmdSuccessful(isCmdSuccessful, "Failed to properly cancel an inbound call", False, "")
        self.assertTrue(self.processRequestTelephonyService({}) == CALL_STATE_IDLE, "Call state idle not matched")
        time.sleep(CMD_WAIT_TIMEOUT)

    def make_inbound_call(self):
        self.assertTrue(self.processRequestTelephonyService({}) == CALL_STATE_IDLE, "Call state idle not matched")
        isCmdSuccessful = True
        for i in range(0, NUM_MAX_TRIALS):
            print "Running test: " + inspect.stack()[0][3] + ", trial #" + str(i+1)
            self.telnet.write("gsm call " + CALL_NUMBER +"\n")
            time.sleep(CMD_WAIT_TIMEOUT)
            output_inbound_call = console_utils.parseOutput(self.telnet)
            isCmdSuccessful = (output_inbound_call == console_utils.OK)
            if isCmdSuccessful:
                break
            time.sleep(TRIAL_WAIT_TIMEOUT)
        self.assertCmdSuccessful(isCmdSuccessful, "Failed to properly set up an inbound call", False, "")
        self.assertTrue(self.processRequestTelephonyService({}) == CALL_STATE_RINGING, "Call state ringing not matched")
        time.sleep(CMD_WAIT_TIMEOUT)

    def accept_inbound_call(self):
        isCmdSuccessful = True
        for i in range(0, NUM_MAX_TRIALS):
            print "Running test: " + inspect.stack()[0][3] + ", trial #" + str(i+1)
            self.telnet.write("gsm accept " + CALL_NUMBER + "\n")
            time.sleep(CMD_WAIT_TIMEOUT)
            output_accept_inbound = console_utils.parseOutput(self.telnet)
            isCmdSuccessful = (output_accept_inbound == console_utils.OK)
            if isCmdSuccessful:
                break
            time.sleep(TRIAL_WAIT_TIMEOUT)
        self.assertCmdSuccessful(isCmdSuccessful, "Failed to properly accept an inbound call", False, "")
        self.assertTrue(self.processRequestTelephonyService({}) == CALL_STATE_OFFHOOK, "Call state offhook not matched")
        time.sleep(CMD_WAIT_TIMEOUT)

    def test_inboundCall(self):
        """
        Test for command: gsm call <phonenumber>
        """
        self.make_inbound_call()
        self.cancel_inbound_call()

    def test_acceptCall(self):
        """
        Test for command: gsm accept <phonenumber>
        """
        self.make_inbound_call()
        self.accept_inbound_call()
        self.cancel_inbound_call()

    def test_terminateCall(self):
        """
        Test for command: gsm cancel <phonenumber>
        """
        self.make_inbound_call()
        self.accept_inbound_call()
        self.cancel_inbound_call_verification()


if __name__ == '__main__':
    print "======= Call Test ======="
    unittest.main()
