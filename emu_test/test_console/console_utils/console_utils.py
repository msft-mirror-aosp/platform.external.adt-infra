"""
This module contains utility helper functions and constants for running each console test.
Particularly, parseOutput(telnet) function is extensively used throughout
the entire console test in order to parse the console output until "OK" message.
"""

#TODO: refactor this file name to util.py, the parent dir name to utils

import re
import os

NEWLINE = "\n"
OK = "OK"
STATUS = "status: "
AC = "AC: "
PRESENT = "present: "
HEALTH = "health: "
CAPACITY = "capacity: "
REGEX_PWR_DISPLAY = "AC:.*\nstatus:.*\nhealth:.*\npresent:.*\ncapacity:.*\nOK"
COMPARE_CMD = ""
if os.name == "nt":
    COMPARE_CMD = "FC"
else:
    COMPARE_CMD = "diff"

SERVER_NAME = 'localhost'
CONSOLE_PORT = 5554

NUM_MAX_TRIALS = 3
TRIAL_WAIT_TIMEOUT = 0.5
CMD_WAIT_TIMEOUT = 0.5

TIMEOUT = 1 # in second

CONSOLE_AUTH_TOKEN_FILE_NAME = '.emulator_console_auth_token'

UTILS_DIR = os.path.dirname(os.path.realpath(__file__))
EVENT_DIR = os.path.join(UTILS_DIR, "..", "EVENT_TEST_DATA")
EVENTS_CODE_NO_ALIAS = "no code aliases defined for this type\r\nOK"
EVENTS_CODE_EV_KEY_FILENAME = os.path.join(EVENT_DIR, "EVENTS_CODE_EV_KEY")
EVENTS_CODE_EV_REL_FILENAME = os.path.join(EVENT_DIR, "EVENTS_CODE_EV_REL")
EVENTS_CODE_EV_ABS_FILENAME = os.path.join(EVENT_DIR, "EVENTS_CODE_EV_ABS")
EVENTS_EV_TYPES_FILENAME = os.path.join(EVENT_DIR, "EVENTS_EV_TYPES")
PORT_NO_REDIR = "no active redirections\r\nOK"
PORT_REDIR_ADD = "tcp:5556  => 5554 \r\nOK"

def checkReadUntil(consoleOutput):
    """
    Helper function for checking whether the console output ends with "OK" message
    """
    consoleOutput = consoleOutput.strip()
    index_OK = consoleOutput.rfind(OK)
    return index_OK == len(consoleOutput) - len(OK)

def parseOutput(telnet):
    """
    Helper function for parsing console output until 'OK' appears
    """
    parsed_output = telnet.read_until(OK).strip()
    return parsed_output

def extractFieldFromOutput(output, keyword):
    """
    Helper function for extracting value of specific field from battery command
    """
    keyword_idx = output.find(keyword)
    return output[keyword_idx + len(keyword):output.find(NEWLINE, keyword_idx)].strip()

def patternMatchOutput(output, regex):
    """
    Helper function for checking whether console output matches with a given regex
    """
    if re.match(regex, output):
        return True
    else:
        return False

def checkBatteryStatus(status):
    """
    Helper function for checking each battery status, used in testcase_battery.py
    """
    if status == "not-charging":
        return "Not charging"
    if status == "failure":
        return "Unspecified failure"
    if status == "overheat":
        return "Overheat"
    return status.capitalize()

def parseOutputForEV(telnet):
    """
    Helper function for parsing console output until 'OK' appears for 'event' command
    """
    parsed_output = telnet.read_until("\n"+OK).strip()
    return parsed_output

def getEventsCodeEvKey():
    """
    Helper function for getting event codes from a static file
    """
    with open(EVENTS_CODE_EV_KEY_FILENAME) as f:
        lines = f.readlines()
    EVENTS_CODE_EV_KEY = ""
    for line in lines:
        EVENTS_CODE_EV_KEY += ("\r\n    " + line.strip())
    return EVENTS_CODE_EV_KEY.strip() + "\r\nOK"

def readStringFromFile(filename):
    """
    Helper function for reading strings written in the file by appending each line
    """
    with open(filename) as f:
        lines = f.readlines()
    stringRead = ""
    for line in lines:
        stringRead += line
    return stringRead

def removeAllSpaces(string):
    """
    Helper function for removing all the trailing spaces and spaces within the string
    """
    return re.sub('[\s+]', '', string.strip(' \t\n\r'))
