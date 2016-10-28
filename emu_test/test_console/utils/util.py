"""
This module contains utility helper functions and constants for running each console test.
Particularly, parseOutput(telnet) function is extensively used throughout
the entire console test in order to parse the console output until "OK" message.
"""
import inspect
import os
import re
import time

NEWLINE = '\n'
OK = 'OK'
STATUS = 'status: '
AC = 'AC: '
PRESENT = 'present: '
HEALTH = 'health: '
CAPACITY = 'capacity: '
REGEX_PWR_DISPLAY = 'AC:.*\nstatus:.*\nhealth:.*\npresent:.*\ncapacity:.*\nOK'
COMPARE_CMD = ''
if os.name == 'nt':
    COMPARE_CMD = 'FC'
else:
    COMPARE_CMD = 'diff'

SERVER_NAME = 'localhost'
CONSOLE_PORT = 5554

NUM_MAX_TRIALS = 3
TRIAL_WAIT_TIMEOUT_S = 0.5
CMD_WAIT_TIMEOUT_S = 0.5
SETUP_WAIT_TIMEOUT_S = 5

TIMEOUT_S = 1 # in second

CONSOLE_AUTH_TOKEN_FILE_NAME = '.emulator_console_auth_token'

UTILS_DIR = os.path.dirname(os.path.realpath(__file__))
EVENT_DIR = os.path.join(UTILS_DIR, '..', 'EVENT_TEST_DATA')
EVENTS_CODE_NO_ALIAS = 'no code aliases defined for this type\r\nOK'
EVENTS_CODE_EV_KEY_FILENAME = os.path.join(EVENT_DIR, 'EVENTS_CODE_EV_KEY')
EVENTS_CODE_EV_REL_FILENAME = os.path.join(EVENT_DIR, 'EVENTS_CODE_EV_REL')
EVENTS_CODE_EV_ABS_FILENAME = os.path.join(EVENT_DIR, 'EVENTS_CODE_EV_ABS')
EVENTS_EV_TYPES_FILENAME = os.path.join(EVENT_DIR, 'EVENTS_EV_TYPES')
PORT_NO_REDIR = 'no active redirections\r\nOK'
PORT_REDIR_ADD = 'tcp:5556  => 5554 \r\nOK'
CMD_HELP = 'help\n'
REGEX_HELP_DISPLAY_NO_AUTH = \
    '.*\n.*\n.*help.*\n.*avd.*\n.*auth.*\n.*quit\|exit.*\n.*\n.*\nOK'
REGEX_HELP_DISPLAY_AUTH = \
    '.*\n.*\n.*help.*\n.*event.*\n.*geo.*\n.*gsm.*\n.*cdma.*\n.*crash.*\n' \
    '.*kill.*\n.*network.*\n.*power.*\n.*quit\|exit.*\n.*redir.*\n' \
    '.*sms.*\n.*avd.*\n.*qemu.*\n.*sensor.*\n.*finger.*\n.*debug.*\n.*\n.*\nOK'

def checkReadUntil(consoleOutput):
    """Checks whether the console output ends with 'OK' message.

    Args:
        consoleOutput: The console output to be checked.

    Returns:
        A boolean value: It indicates the console output ends with 'OK' message
            or not.
    """
    consoleOutput = consoleOutput.strip()
    index_OK = consoleOutput.rfind(OK)
    return index_OK == len(consoleOutput) - len(OK)

def parseOutput(telnet):
    """Parses console output until 'OK' appears

    Args:
        telnet: The telnet connection to emulator.

    Returns:
        parsed_output: The parsed output until 'OK' message.
    """
    parsed_output = telnet.read_until(OK).strip()
    return parsed_output

def extractFieldFromOutput(output, keyword):
    """Extract value of specific field from battery command.

    Args:
        output: The output for extracting certain field.
        keyword: The keyword for searching.

    Returns:
        A string value: The field from output searching by given keyword.
    """
    keyword_idx = output.find(keyword)
    return output[keyword_idx + len(keyword):output.find(NEWLINE, keyword_idx)].strip()

def patternMatchOutput(output, regex):
    """Check whether console output matches with a given regex.

    Args:
        output: The console output of a command.
        regex: The regular pattern to use for searching.

    Returns:
        A boolean value: It indicates the pattern is found in the output or not.
    """
    if re.match(regex, output):
        return True
    else:
        return False

def checkBatteryStatus(status):
    """Checking each battery status, used in testcase_battery.py

    Args:
        status: A battery status to map.

    Returns:
        A string value: The capitalized/mapped battery status.
    """
    if status == 'not-charging':
        return 'Not charging'
    if status == 'failure':
        return 'Unspecified failure'
    if status == 'overheat':
        return 'Overheat'
    return status.capitalize()

def parseOutputForEV(telnet):
    """Parses console output until 'OK' appears for 'event' command.

    Args:
        telnet: The telnet connection to emulator.

    Returns:
        parsed_output: The parsed console output.
    """
    parsed_output = telnet.read_until("\n"+OK).strip()
    return parsed_output

def getEventsCodeEvKey():
    """Gets event codes from a static file.

    Returns:
        A string value: The event codes getting from a static file.
    """
    with open(EVENTS_CODE_EV_KEY_FILENAME) as f:
        lines = f.readlines()
    EVENTS_CODE_EV_KEY = ""
    for line in lines:
        EVENTS_CODE_EV_KEY += ('\r\n    ' + line.strip())
    return EVENTS_CODE_EV_KEY.strip() + '\r\nOK'

def readStringFromFile(filename):
    """Reads strings written in the file by appending each line.

    Args:
        filename: The file name to read strings from.

    Returns:
        stringRead: A single string value containing each line in the file.
    """
    with open(filename) as f:
        lines = f.readlines()
    stringRead = ""
    for line in lines:
        stringRead += line
    return stringRead

def removeAllSpaces(string):
    """Removes all the trailing spaces and spaces within the string.

    Args:
        string: A string to remove training spaces.

    Returns:
        A string value: A parsed string after removing all trailing spaces.
    """
    return re.sub('[\s+]', '', string.strip(' \t\n\r'))

def execute_console_command(telnet, command, expected_output):
    """Executes emulator console command.

    Executes emulator console command through telnet connection,
    compare command output and expected command output.

    Args:
        telnet: The telnet connection to emulator.
        command: The console command to execute.
        expected_output: The expected output for the executed command.

    Returns:
        is_command_successful: It indicates command executed successfully or not.
        output: The command output in the terminal.
    """
    is_command_successful = False

    for i in range(NUM_MAX_TRIALS):
        print('execute command: %s, trial #%d' % (inspect.stack()[0][3], i))

        telnet.write(command)
        time.sleep(CMD_WAIT_TIMEOUT_S)

        if command != 'crash\n':
            output = parseOutput(telnet)
        else:
            output = telnet.read_all()

        is_command_successful = patternMatchOutput(output, expected_output)

        if is_command_successful:
            break

        time.sleep(TRIAL_WAIT_TIMEOUT_S)

    return is_command_successful, output
