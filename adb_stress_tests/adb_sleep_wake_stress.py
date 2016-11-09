"""ADB stress test for sleep/wake.

usage: adb_sleep_wake_stress.py [-h] [-d float] [-c int]

optional arguments:
  -h, --help                     Show this help message and exit.
  -d float, --duration float     Duration of time to run stress test (in hrs).
  -c int, --count int            Number of devices/emulators connected.
"""

import subprocess

import util

_ITERATIONS = 30*60


def test_sleep(dut):
    """Verify that putting the device to sleep is successful.

    Args:
      dut: Serial number of device to connect to.

    Returns:
      True if the device was successfully put to sleep, else False
    """
    # Simulate power button press.
    # It would be good if we verified the device was currently awake.
    # Otherwise, this will actually wake up the device.
    arg = 'adb -s ' + str(dut) + ' shell input keyevent POWER'
    process = subprocess.Popen(arg.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    success = True
    for line in output.split('\n'):
        if line.startswith('adb: error'):
            success = False
            print('\nERROR:\nFAILED to put device to sleep: ' + str(dut))
            print(output)

    return success


def test_wake(dut):
    """Verify that the device can be woken up.

    Args:
      dut: Serial number of device under test.

    Returns:
      True if the device was successfully woken up, else False.
    """
    arg = 'adb -s ' + str(dut) + ' shell input keyevent POWER'
    process = subprocess.Popen(arg.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    success = True
    for line in output.split('\n'):
        if line.startswith('adb: error'):
            print('\nERROR:\nFAILED to wake device: ' + str(dut))
            print(output)
            success = False

    return success


def launcher(duration, devices):
    """Launches the test.

    Args:
        duration: Number of iterations to execute.
        devices: Number of expected devices.
    """
    connection_error = False
    iterations = int(duration * _ITERATIONS)
    for i in range(iterations):
        util.print_progress(i, iterations, prefix='Progress:', suffix='Complete', bar_len=50)
        success, connected = util.test_connected(devices)
        if not success:
            break

        # Verify successful sleep and wake from each connected device/emulator.
        for dut in connected:
            success_sleep = test_sleep(dut)
            success_wake  = test_wake(dut)
            if not success_sleep or not success_wake:
                connection_error = True

        if connection_error:
            break

    if i == iterations - 1 and success and not connection_error:
        util.print_progress(i + 1, iterations, prefix='Progress:', suffix='Complete', bar_len=50)
        print('\nSUCCESS\n')


if __name__ == '__main__':
    args = util.parse_args()
    launcher(args.duration, args.count)