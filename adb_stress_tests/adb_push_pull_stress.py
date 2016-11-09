"""ADB stress test for device push/pull commands.

usage: adb_push_pull_stress.py [-h] [-d float] [-c int]

optional arguments:
  -h, --help                     Show this help message and exit.
  -d float, --duration float     Duration of time to run stress test (in hrs).
  -c int, --count int            Number of devices/emulators connected.
"""

from __future__ import print_function
import os
import subprocess

import util

_ITERATIONS = 500000
TEMP_FILE = '__push_file.txt'

# Number of lines in push/pull'd file.
FILE_SIZE = 100


def create_temp_files():
    """Setup for push test.

    Creates all temporary files created used in push test."""
    file = open(TEMP_FILE, 'w')
    for i in range(FILE_SIZE):
        file.write('lorem ipsum\n')
    file.close()


def delete_temp_files():
    """Teardown for push test.

    Deletes all temporary files created for push test.
    """
    try:
        os.remove(TEMP_FILE)
    except OSError:
        pass


def test_push(dut):
    """Verify that pushing a file is successful.

    File size is determined by FILE_SIZE constant.

    Args:
      dut: Device to test against.

    Returns:
      True if successful, else False.
    """
    arg = 'adb -s ' + str(dut) + ' push ' + TEMP_FILE + ' /sdcard/'
    process = subprocess.Popen(arg.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    success = True
    for line in output.split('\n'):
        if line.startswith('adb: error'):
            success = False
            print('\nERROR:\nEPush FAILED for: ' + str(dut))
            print(output)

    return success


def test_pull(connec):
    """Verify that pulling a file is successful.

    File size is determined by FILE_SIZE constant.

    Returns:
      True if successful, else False.
    """
    arg = 'adb -s ' + str(connec) + ' push ' + TEMP_FILE + ' /sdcard/'
    process = subprocess.Popen(arg.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    success = True
    for line in output.split('\n'):
        if line.startswith('adb: error'):
            print('\nERROR:\nEPush FAILED for: ' + str(connec))
            print(output)
            success = False

    return success


def launcher(duration, devices):
    """Launches the test.

    Args:
        duration: Number of iterations to execute.
        devices: Number of expected devices.
    """
    try:
        create_temp_files()
        connection_error = False
        iterations = int(duration * _ITERATIONS)
        for i in range(iterations):
            util.print_progress(i, iterations, prefix='Progress:', suffix='Complete', bar_len=50)
            success, connected = util.test_connected(devices)
            if not success:
                break

            # Verify successful push and pull from each connected device/emulator.
            for dut in connected:
                success_push = test_push(dut)
                success_pull = test_pull(dut)
                if not success_push or not success_pull:
                    connection_error = True

            if connection_error:
                break

        if i == iterations - 1 and success and not connection_error:
            util.print_progress(i + 1, iterations, prefix='Progress:', suffix='Complete', bar_len=50)
            print('\nSUCCESS\n')
    finally:
        delete_temp_files()


if __name__ == '__main__':
    args = util.parse_args()
    launcher(args.duration, args.count)