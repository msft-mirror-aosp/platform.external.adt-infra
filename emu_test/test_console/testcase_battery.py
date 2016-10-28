"""
Tests for battery-related commands
"""

import unittest
import telnetlib
from subprocess import check_output
import utils.util as console_utils
from os.path import expanduser
import os
import inspect
import time
from testcase_base import BaseConsoleTest

NUM_MAX_TRIALS = 3
TRIAL_WAIT_TIMEOUT = 0.5
CMD_WAIT_TIMEOUT = 0.5

class BatteryTest(BaseConsoleTest):

    def test_powerDisplay(self):
        """
        Test for command: power ac <on_or_off>
        Test Rail ID: C14595300
        Test steps:
            1. Launch an emulator avd
            2. From command prompt, run: telnet localhost <port>
            3. Copy the auth_token value from ~/.emulator_console_auth_token
            4. Run: auth auth_token
            5. Run: power display, and verify 1
        Verify:
            1. Power details are displayed
        """
        isCmdSuccessful = True
        for i in range(0, NUM_MAX_TRIALS):
            print "Running test: " + inspect.stack()[0][3] + ", trial #" + str(i+1)
            self.telnet.write("power display\n")
            time.sleep(CMD_WAIT_TIMEOUT)
            output_pwr_display = console_utils.parseOutput(self.telnet)
            isCmdSuccessful = console_utils.patternMatchOutput(output_pwr_display, console_utils.REGEX_PWR_DISPLAY)
            if isCmdSuccessful:
                break
            time.sleep(TRIAL_WAIT_TIMEOUT)
        self.assertCmdSuccessful(isCmdSuccessful, "Failed to properly display current power info", False, "", "Pattern: " + console_utils.REGEX_PWR_DISPLAY, output_pwr_display)

    def getPowerDisplay(self):
        self.telnet.write("power display\n")
        time.sleep(CMD_WAIT_TIMEOUT)
        output_pwr_display = console_utils.parseOutput(self.telnet)
        return output_pwr_display

    def setACChargeTest(self, status):
        isCmdSuccessful = True
        for i in range(0, NUM_MAX_TRIALS):
            print "Running test: " + inspect.stack()[0][3] + " set as " + status + ", trial #" + str(i+1)
            self.telnet.write("power ac " + status + "\n")
            time.sleep(CMD_WAIT_TIMEOUT)
            output = console_utils.parseOutput(self.telnet)
            isCmdSuccessful = (output == console_utils.OK)
            if isCmdSuccessful:
                break
            time.sleep(TRIAL_WAIT_TIMEOUT)
        self.assertCmdSuccessful(isCmdSuccessful, "Failed to set power ac to " + status, True, status, console_utils.OK, output)

        isCmdSuccessful = True
        for i in range(0, NUM_MAX_TRIALS):
            print "Running test: " + inspect.stack()[0][3] + " retrieve status " + status + ", trial #" + str(i+1)
            output_pwr_display = self.getPowerDisplay()
            output_extracted = console_utils.extractFieldFromOutput(output_pwr_display, console_utils.AC)
            isCmdSuccessful = (output_extracted == status + "line")
            if isCmdSuccessful:
                break
            time.sleep(TRIAL_WAIT_TIMEOUT)
        print "Test result: " + inspect.stack()[0][3] + " " + status + " => " + str(isCmdSuccessful)
        self.assertCmdSuccessful(isCmdSuccessful, "Failed to retrieve power status as " + status + "line", True, status, status + "line", output_extracted)

    def test_setACChargeState(self):
        """
        Test for command: power ac <on_or_off>
        Test Rail ID: C14595300
        Test steps:
            1. Launch an emulator avd
            2. From command prompt, run: telnet localhost <port>
            3. Copy the auth_token value from ~/.emulator_console_auth_token
            4. Run: auth auth_token
            5. Run: power ac on
            6. Run: power display, and verify 1
            7. Run: power ac off
            8. Run: power display, and verify 2
        Verify:
            1. Emulator displays AC as online
            2. Emulator displays AC as offline
        """
        self.setACChargeTest("on")
        self.setACChargeTest("off")

    def setBatteryStatusTest(self, status):
        isCmdSuccessful = True
        for i in range(0, NUM_MAX_TRIALS):
            print "Running test: " + inspect.stack()[0][3] + " set as " + status + ", trial #" + str(i+1)
            self.telnet.write("power status " + status + "\n")
            time.sleep(CMD_WAIT_TIMEOUT)
            output = console_utils.parseOutput(self.telnet)
            isCmdSuccessful = (output == console_utils.OK)
            if isCmdSuccessful:
                break
            time.sleep(TRIAL_WAIT_TIMEOUT)
        self.assertCmdSuccessful(isCmdSuccessful, "Failed to set power status to " + status, True, status, console_utils.OK, output)

        isCmdSuccessful = True
        for i in range(0, NUM_MAX_TRIALS):
            print "Running test: " + inspect.stack()[0][3] + " check whether status matches " + status + ", trial #" + str(i+1)
            output_pwr_display = self.getPowerDisplay()
            output_extracted = console_utils.extractFieldFromOutput(output_pwr_display, console_utils.STATUS)
            correct_output = console_utils.checkBatteryStatus(status)
            isCmdSuccessful = (output_extracted == correct_output)
            if isCmdSuccessful:
                break
            time.sleep(TRIAL_WAIT_TIMEOUT)
        self.assertCmdSuccessful(isCmdSuccessful, "Failed to retrieve power status as " + console_utils.checkBatteryStatus(status), True, status, correct_output, output_extracted)

    def test_setBatteryStatusToUnknown(self):
        """
        Test for command: power status unknown
        Test Rail ID: C14595300
        Test steps:
            1. Launch an emulator avd
            2. From command prompt, run: telnet localhost <port>
            3. Copy the auth_token value from ~/.emulator_console_auth_token
            4. Run: auth auth_token
            5. Run: power status unknown, and verify 1
        Verify:
            1. Success to set power status to unknown
        """
        self.setBatteryStatusTest("unknown")

    def test_setBatteryStatusToCharging(self):
        """
        Test for command: power status charging
        Test Rail ID: C14595300
        Test steps:
            1. Launch an emulator avd
            2. From command prompt, run: telnet localhost <port>
            3. Copy the auth_token value from ~/.emulator_console_auth_token
            4. Run: auth auth_token
            5. Run: power status charging, and verify 1
        Verify:
            1. Success to set power status to charging
        """
        self.setBatteryStatusTest("charging")

    def test_setBatteryStatusToDischarging(self):
        """
        Test for command: power status discharging
        Test Rail ID: C14595300
        Test steps:
            1. Launch an emulator avd
            2. From command prompt, run: telnet localhost <port>
            3. Copy the auth_token value from ~/.emulator_console_auth_token
            4. Run: auth auth_token
            5. Run: power status discharging, and verify 1
        Verify:
            1. Success to set power status to discharging
        """
        self.setBatteryStatusTest("discharging")

    def test_setBatteryStatusToNotCharging(self):
        """
        Test for command: power status not-charging
        Test Rail ID: C14595300
        Test steps:
            1. Launch an emulator avd
            2. From command prompt, run: telnet localhost <port>
            3. Copy the auth_token value from ~/.emulator_console_auth_token
            4. Run: auth auth_token
            5. Run: power status not-charging, and verify 1
        Verify:
            1. Success to set power status to not-charging
        """
        self.setBatteryStatusTest("not-charging")

    def test_setBatteryStatusToFull(self):
        """
        Test for command: power status full
        Test Rail ID: C14595300
        Test steps:
            1. Launch an emulator avd
            2. From command prompt, run: telnet localhost <port>
            3. Copy the auth_token value from ~/.emulator_console_auth_token
            4. Run: auth auth_token
            5. Run: power status full, and verify 1
        Verify:
            1. Success to set power status to full
        """
        self.setBatteryStatusTest("full")

    def setPresenceStateTest(self, state):
        isCmdSuccessful = True
        for i in range(0, NUM_MAX_TRIALS):
            print "Running test: " + inspect.stack()[0][3] + " set as " + state + ", trial #" + str(i+1)
            self.telnet.write("power present " + state + "\n")
            time.sleep(CMD_WAIT_TIMEOUT)
            output = console_utils.parseOutput(self.telnet)
            isCmdSuccessful = (output == console_utils.OK)
            if isCmdSuccessful:
                break
            time.sleep(TRIAL_WAIT_TIMEOUT)
        self.assertCmdSuccessful(isCmdSuccessful, "Failed to set power presence to " + state, True, state, console_utils.OK, output)

        isCmdSuccessful = True
        for i in range(0, NUM_MAX_TRIALS):
            print "Running test: " + inspect.stack()[0][3] + " check whether presence matches " + state + ", trial #" + str(i+1)
            output_pwr_display = self.getPowerDisplay()
            output_extracted = console_utils.extractFieldFromOutput(output_pwr_display, console_utils.PRESENT)
            isCmdSuccessful = output_extracted
            if isCmdSuccessful:
                break
            time.sleep(TRIAL_WAIT_TIMEOUT)
        self.assertCmdSuccessful(isCmdSuccessful, "Failed to retrieve power status as " + state, True, state, "<any value>", output_extracted)

    def test_setPresenceState(self):
        """
        Test for command: power present <true_or_false>
        Test Rail ID: C14595300
        Test steps:
            1. Launch an emulator avd
            2. From command prompt, run: telnet localhost <port>
            3. Copy the auth_token value from ~/.emulator_console_auth_token
            4. Run: auth auth_token
            5. Run: power present true, and verify 1
            6. Run: power present false, and verify 2
        Verify:
            1. Success to set power presence to True
            2. Success to set power presence to False
        """
        self.setPresenceStateTest("true")
        self.setPresenceStateTest("false")

    def setBatteryHealthTest(self, status):
        isCmdSuccessful = True
        for i in range(0, NUM_MAX_TRIALS):
            print "Running test: " + inspect.stack()[0][3] + " set as " + status + ", trial #" + str(i+1)
            self.telnet.write("power health " + status + "\n")
            time.sleep(CMD_WAIT_TIMEOUT)
            output = console_utils.parseOutput(self.telnet)
            isCmdSuccessful = (output == console_utils.OK)
            if isCmdSuccessful:
                break
            time.sleep(TRIAL_WAIT_TIMEOUT)
        self.assertCmdSuccessful(isCmdSuccessful, "Failed to set power health to " + status, True, status, console_utils.OK, output)

        isCmdSuccessful = True
        for i in range(0, NUM_MAX_TRIALS):
            print "Running test: " + inspect.stack()[0][3] + " check whether health matches " + status + ", trial #" + str(i+1)
            output_pwr_display = self.getPowerDisplay()
            output_extracted = console_utils.extractFieldFromOutput(output_pwr_display, console_utils.HEALTH)
            correct_output = console_utils.checkBatteryStatus(status)
            isCmdSuccessful = (output_extracted == correct_output)
            if isCmdSuccessful:
                break
            time.sleep(TRIAL_WAIT_TIMEOUT)
        c_status = console_utils.checkBatteryStatus(status)
        self.assertCmdSuccessful(isCmdSuccessful, "Failed to retrieve power health as " + c_status, True, c_status, correct_output, output_extracted)

    def test_setBatteryHealthToUnknown(self):
        """
        Test for command: power health unknown
        Test Rail ID: C14595300
        Test steps:
            1. Launch an emulator avd
            2. From command prompt, run: telnet localhost <port>
            3. Copy the auth_token value from ~/.emulator_console_auth_token
            4. Run: auth auth_token
            5. Run: power health unknown, and verify 1
        Verify:
            1. Success to set power health to unknown
        """
        self.setBatteryHealthTest("unknown")

    def test_setBatteryHealthToGood(self):
        """
        Test for command: power health good
        Test Rail ID: C14595300
        Test steps:
            1. Launch an emulator avd
            2. From command prompt, run: telnet localhost <port>
            3. Copy the auth_token value from ~/.emulator_console_auth_token
            4. Run: auth auth_token
            5. Run: power health good, and verify 1
        Verify:
            1. Success to set power health to good
        """
        self.setBatteryHealthTest("good")

    def test_setBatteryHealthToOverheat(self):
        """
        Test for command: power health overheat
        Test Rail ID: C14595300
        Test steps:
            1. Launch an emulator avd
            2. From command prompt, run: telnet localhost <port>
            3. Copy the auth_token value from ~/.emulator_console_auth_token
            4. Run: auth auth_token
            5. Run: power health overheat, and verify 1
        Verify:
            1. Success to set power health to overheat
        """
        self.setBatteryHealthTest("overheat")

    def test_setBatteryHealthToDead(self):
        """
        Test for command: power health dead
        Test Rail ID: C14595300
        Test steps:
            1. Launch an emulator avd
            2. From command prompt, run: telnet localhost <port>
            3. Copy the auth_token value from ~/.emulator_console_auth_token
            4. Run: auth auth_token
            5. Run: power health dead, and verify 1
        Verify:
            1. Success to set power health to dead
        """
        self.setBatteryHealthTest("dead")

    def test_setBatteryHealthToOvervoltage(self):
        """
        Test for command: power health overvoltage
        Test Rail ID: C14595300
        Test steps:
            1. Launch an emulator avd
            2. From command prompt, run: telnet localhost <port>
            3. Copy the auth_token value from ~/.emulator_console_auth_token
            4. Run: auth auth_token
            5. Run: power health overvoltage, and verify 1
        Verify:
            1. Success to set power health to overvoltage
        """
        self.setBatteryHealthTest("overvoltage")

    def test_setBatteryHealthToFailure(self):
        """
        Test for command: power health failure
        Test Rail ID: C14595300
        Test steps:
            1. Launch an emulator avd
            2. From command prompt, run: telnet localhost <port>
            3. Copy the auth_token value from ~/.emulator_console_auth_token
            4. Run: auth auth_token
            5. Run: power health failure, and verify 1
        Verify:
            1. Success to set power health to failure
        """
        self.setBatteryHealthTest("failure")

    def test_setRemainingBatteryCapacity(self):
        """
        Test for command: power capacity 75
        Test Rail ID: C14595300
        Test steps:
            1. Launch an emulator avd
            2. From command prompt, run: telnet localhost <port>
            3. Copy the auth_token value from ~/.emulator_console_auth_token
            4. Run: auth auth_token
            5. Run: power capacity 75, and verify 1
        Verify:
            1. Success to set power capacity to 75
        """
        isCmdSuccessful = True
        for i in range(0, NUM_MAX_TRIALS):
            print "Running test: " + inspect.stack()[0][3] + ", set battery capacity: trial #" + str(i+1)
            self.telnet.write("power capacity 75\n")
            time.sleep(CMD_WAIT_TIMEOUT)
            output = console_utils.parseOutput(self.telnet)
            isCmdSuccessful = (output == console_utils.OK)
            if isCmdSuccessful:
                break
            time.sleep(TRIAL_WAIT_TIMEOUT)
        self.assertCmdSuccessful(isCmdSuccessful, "Failed to set remaining battery to 75", False, "", console_utils.OK, output)

        isCmdSuccessful = True
        for i in range(0, NUM_MAX_TRIALS):
            print "Running test: " + inspect.stack()[0][3] + "check whether batterty capacity set properly , trial #" + str(i+1)
            output_pwr_display = self.getPowerDisplay()
            output_extracted = console_utils.extractFieldFromOutput(output_pwr_display, console_utils.CAPACITY)
            isCmdSuccessful = (output_extracted == "75")
            if isCmdSuccessful:
                break
            time.sleep(TRIAL_WAIT_TIMEOUT)
        self.assertCmdSuccessful(isCmdSuccessful, "Failed to retrieve battery capacity as 75", False, "", "75", output_extracted)


if __name__ == '__main__':
    print "======= Battery Test ======="
    unittest.main()
