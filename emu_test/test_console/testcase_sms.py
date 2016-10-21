#!/usr/bin/env python

"""Tests for sms-related commands."""

import json
import os
import requests
import subprocess
import time
import unittest
from testcase_base import BaseConsoleTest
from console_utils import console_utils

TESTCASE_CALL_DIR = os.path.dirname(os.path.realpath(__file__))
SERVLET_SMS = 'http://localhost:8080/SmsManagerService'

SENDER_PHONE_NUMBER = '2345678910'
TEXT_MESSAGE = 'Hello there'
CMD_SMS_SEND = 'sms send %s %s\n' % (SENDER_PHONE_NUMBER, TEXT_MESSAGE)
CMD_SMS_PDU = 'sms pdu 07911326040000F0040B911346610089F6000020806291'\
              '7314080CC8F71D14969741F977FD07\n'
PDU_MESSAGE = 'How are you?'
PDU_PHONE_NUMBER = '+31641600986'


class SmsTest(BaseConsoleTest):
    """This class aims to test sms-related emulator console commands."""

    @classmethod
    def run_script_run_adb_shell(cls):
        proc_install_apk = subprocess.Popen(
            ['python', TESTCASE_CALL_DIR + '/runADBShell.py'])
        return proc_install_apk

    @classmethod
    def setUpClass(cls):
        subprocess.call(
            ['adb', '-s', 'emulator-5554', '-e', 'forward', 'tcp:8080',
             'tcp:8081'])
        subprocess.call(['python', TESTCASE_CALL_DIR + '/installAPK.py'])
        cls.run_script_run_adb_shell()
        time.sleep(console_utils.SETUP_WAIT_TIMEOUT_S)

    def _process_request_sms_service(self, payload):
        """Processes post request to sms service.

        Sends post request to sms service, gets the newest sms message,
        then parses the result to get phone number and text message.

        Args:
            payload: The payload for sending POST request to sms server.

        Returns:
            phone_number: The sender's phone number in the sms message.
            text_message: The text message in the sms.
        """
        r = requests.post(SERVLET_SMS, data=json.dumps(payload))

        if r.raise_for_status():
            print('Servlet Error: Post request to %s failed' % SERVLET_SMS)
            return False

        r_json = r.json()

        if r_json['isFail']:
            print('Servlet Error: Failure occurred in servlet side => %s'
                  % SERVLET_SMS)
            return False

        return r_json['smsAddress'], r_json['smsTextMessage']

    def test_send_inbound_sms_text_message(self):
        """
        Test command for: sms send <phone number> <text message>
        Test Rail ID: C14595297
        Test steps:
            1. Launch an emulator avd
            2. From command prompt, run: telnet localhost <port>
            3. Copy the auth_token value from ~/.emulator_console_auth_token
            4. Run: auth auth_token
            5. Run: sms send <phone number> <text message>, and verify
        Verify:
            An sms is received from <phone number> with the text <text message>.
        """
        is_command_successful, output = \
            console_utils.execute_console_command(self.telnet,
                                                  CMD_SMS_SEND,
                                                  console_utils.OK)
        self.assertCmdSuccessful(is_command_successful,
                                 'Failed to properly send sms text message',
                                 False,
                                 '',
                                 console_utils.OK,
                                 output)

        got_phone_number, got_sms_message = self._process_request_sms_service({})
        print('got_phone_number = %s, got_sms_message=%s'
              % (got_phone_number, got_sms_message))
        self.assertTrue(
            got_phone_number == SENDER_PHONE_NUMBER,
            'Sender phone number is wrong.')
        self.assertTrue(
            got_sms_message == TEXT_MESSAGE,
            'The received text message is wrong.')

    def test_send_inbound_sms_pdu(self):
        """
        Test command for: sms send <phone number> <text message>
        Test Rail ID: C14595297
        Test steps:
            1. Launch an emulator avd
            2. From command prompt, run: telnet localhost <port>
            3. Copy the auth_token value from ~/.emulator_console_auth_token
            4. Run: auth auth_token
            5. Run: sms pdu <pdu message>
               and verify
        Verify:
            An sms is received from <expected phone number> with
            <expected text> ('How are you?').
        """
        is_command_successful, output = \
            console_utils.execute_console_command(self.telnet,
                                                  CMD_SMS_PDU,
                                                  console_utils.OK)
        self.assertCmdSuccessful(is_command_successful,
                                 'Failed to properly send sms pdu',
                                 False,
                                 '',
                                 console_utils.OK,
                                 output)

        got_phone_number, got_sms_message = self._process_request_sms_service({})
        print('got_phone_number = %s, got_sms_message=%s'
              % (got_phone_number, got_sms_message))
        self.assertTrue(
            got_phone_number == PDU_PHONE_NUMBER,
            'Sender phone number is wrong.')
        self.assertTrue(
            got_sms_message == PDU_MESSAGE,
            'The received text message is wrong.')

if __name__ == '__main__':
    print('======= sms Test =======')
    unittest.main()
