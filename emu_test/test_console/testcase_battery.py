"""
Tests for battery-related commands
"""

import unittest
import telnetlib
from subprocess import check_output
import console_utils.console_utils as console_utils
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
        self.assertCmdSuccessful(isCmdSuccessful, "Failed to properly display current power info", False, "")

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
            isCmdSuccessful = (console_utils.parseOutput(self.telnet) == console_utils.OK)
            if isCmdSuccessful:
                break
            time.sleep(TRIAL_WAIT_TIMEOUT)
        self.assertCmdSuccessful(isCmdSuccessful, "Failed to set power ac to " + status, True, status)

        isCmdSuccessful = True
        for i in range(0, NUM_MAX_TRIALS):
            print "Running test: " + inspect.stack()[0][3] + " retrieve status " + status + ", trial #" + str(i+1)
            output_pwr_display = self.getPowerDisplay()
            isCmdSuccessful = (console_utils.extractFieldFromOutput(output_pwr_display, console_utils.AC) == status + "line")
            if isCmdSuccessful:
                break
            time.sleep(TRIAL_WAIT_TIMEOUT)
        print "Test result: " + inspect.stack()[0][3] + " " + status + " => " + str(isCmdSuccessful)
        self.assertCmdSuccessful(isCmdSuccessful, "Failed to retrieve power status as " + status + "line", True, status)

    def test_setACChargeState(self):
        """
        Test for command: power ac <on_or_off>
        """
        self.setACChargeTest("on")
        self.setACChargeTest("off")

    def setBatteryStatusTest(self, status):
        isCmdSuccessful = True
        for i in range(0, NUM_MAX_TRIALS):
            print "Running test: " + inspect.stack()[0][3] + " set as " + status + ", trial #" + str(i+1)
            self.telnet.write("power status " + status + "\n")
            time.sleep(CMD_WAIT_TIMEOUT)
            isCmdSuccessful = (console_utils.parseOutput(self.telnet) == console_utils.OK)
            if isCmdSuccessful:
                break
            time.sleep(TRIAL_WAIT_TIMEOUT)
        self.assertCmdSuccessful(isCmdSuccessful, "Failed to set power status to " + status, True, status)

        isCmdSuccessful = True
        for i in range(0, NUM_MAX_TRIALS):
            print "Running test: " + inspect.stack()[0][3] + " check whether status matches " + status + ", trial #" + str(i+1)
            output_pwr_display = self.getPowerDisplay()
            isCmdSuccessful = ((console_utils.extractFieldFromOutput(output_pwr_display, console_utils.STATUS) == console_utils.checkBatteryStatus(status)))
            if isCmdSuccessful:
                break
            time.sleep(TRIAL_WAIT_TIMEOUT)
        self.assertCmdSuccessful(isCmdSuccessful, "Failed to retrieve power status as " + console_utils.checkBatteryStatus(status), True, status)

    def test_setBatteryStatusToUnknown(self):
        """
        Test for command: power status unknown
        """
        self.setBatteryStatusTest("unknown")

    def test_setBatteryStatusToCharging(self):
        """
        Test for command: power status charging
        """
        self.setBatteryStatusTest("charging")

    def test_setBatteryStatusToDischarging(self):
        """
        Test for command: power status discharging
        """
        self.setBatteryStatusTest("discharging")

    def test_setBatteryStatusToNotCharging(self):
        """
        Test for command: power status not-charging
        """
        self.setBatteryStatusTest("not-charging")

    def test_setBatteryStatusToFull(self):
        """
        Test for command: power status full
        """
        self.setBatteryStatusTest("full")

    def setPresenceStateTest(self, state):
        isCmdSuccessful = True
        for i in range(0, NUM_MAX_TRIALS):
            print "Running test: " + inspect.stack()[0][3] + " set as " + state + ", trial #" + str(i+1)
            self.telnet.write("power present " + state + "\n")
            time.sleep(CMD_WAIT_TIMEOUT)
            isCmdSuccessful = (console_utils.parseOutput(self.telnet) == console_utils.OK)
            if isCmdSuccessful:
                break
            time.sleep(TRIAL_WAIT_TIMEOUT)
        self.assertCmdSuccessful(isCmdSuccessful, "Failed to set power presence to " + state, True, state)

        isCmdSuccessful = True
        for i in range(0, NUM_MAX_TRIALS):
            print "Running test: " + inspect.stack()[0][3] + " check whether presence matches " + state + ", trial #" + str(i+1)
            output_pwr_display = self.getPowerDisplay()
            isCmdSuccessful = (console_utils.extractFieldFromOutput(output_pwr_display, console_utils.PRESENT))
            if isCmdSuccessful:
                break
            time.sleep(TRIAL_WAIT_TIMEOUT)
        self.assertCmdSuccessful(isCmdSuccessful, "Failed to retrieve power status as " + state, True, state)

    def test_setPresenceState(self):
        """
        Test for command: power present <true_or_false>
        """
        self.setPresenceStateTest("true")
        self.setPresenceStateTest("false")

    def setBatteryHealthTest(self, status):
        isCmdSuccessful = True
        for i in range(0, NUM_MAX_TRIALS):
            print "Running test: " + inspect.stack()[0][3] + " set as " + status + ", trial #" + str(i+1)
            self.telnet.write("power health " + status + "\n")
            time.sleep(CMD_WAIT_TIMEOUT)
            isCmdSuccessful = (console_utils.parseOutput(self.telnet) == console_utils.OK)
            if isCmdSuccessful:
                break
            time.sleep(TRIAL_WAIT_TIMEOUT)
        self.assertCmdSuccessful(isCmdSuccessful, "Failed to set power health to " + status, True, status)

        isCmdSuccessful = True
        for i in range(0, NUM_MAX_TRIALS):
            print "Running test: " + inspect.stack()[0][3] + " check whether health matches " + status + ", trial #" + str(i+1)
            output_pwr_display = self.getPowerDisplay()
            isCmdSuccessful = (console_utils.extractFieldFromOutput(output_pwr_display, console_utils.HEALTH) == console_utils.checkBatteryStatus(status))
            if isCmdSuccessful:
                break
            time.sleep(TRIAL_WAIT_TIMEOUT)
        c_status = console_utils.checkBatteryStatus(status)
        self.assertCmdSuccessful(isCmdSuccessful, "Failed to retrieve power health as " + c_status, True, c_status)

    def test_setBatteryHealthToUnknown(self):
        """
        Test for command: power health unknown
        """
        self.setBatteryHealthTest("unknown")

    def test_setBatteryHealthToGood(self):
        """
        Test for command: power health good
        """
        self.setBatteryHealthTest("good")

    def test_setBatteryHealthToOverheat(self):
        """
        Test for command: power health overheat
        """
        self.setBatteryHealthTest("overheat")

    def test_setBatteryHealthToDead(self):
        """
        Test for command: power health dead
        """
        self.setBatteryHealthTest("dead")

    def test_setBatteryHealthToOvervoltage(self):
        """
        Test for command: power health overvoltage
        """
        self.setBatteryHealthTest("overvoltage")

    def test_setBatteryHealthToFailure(self):
        """
        Test for command: power health failure
        """
        self.setBatteryHealthTest("failure")

    def test_setRemainingBatteryCapacity(self):
        """
        Test for command: power capacity 75
        """
        isCmdSuccessful = True
        for i in range(0, NUM_MAX_TRIALS):
            print "Running test: " + inspect.stack()[0][3] + ", set battery capacity: trial #" + str(i+1)
            self.telnet.write("power capacity 75\n")
            time.sleep(CMD_WAIT_TIMEOUT)
            isCmdSuccessful = (console_utils.parseOutput(self.telnet) == console_utils.OK)
            if isCmdSuccessful:
                break
            time.sleep(TRIAL_WAIT_TIMEOUT)
        self.assertCmdSuccessful(isCmdSuccessful, "Failed to set remaining battery to 75", False, "")

        isCmdSuccessful = True
        for i in range(0, NUM_MAX_TRIALS):
            print "Running test: " + inspect.stack()[0][3] + "check whether batterty capacity set properly , trial #" + str(i+1)
            output_pwr_display = self.getPowerDisplay()
            isCmdSuccessful = (console_utils.extractFieldFromOutput(output_pwr_display, console_utils.CAPACITY) == "75")
            if isCmdSuccessful:
                break
            time.sleep(TRIAL_WAIT_TIMEOUT)
        self.assertCmdSuccessful(isCmdSuccessful, "Failed to retrieve battery capacity as 75", False, "")


if __name__ == '__main__':
    print "======= Battery Test ======="
    unittest.main()
