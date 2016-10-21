"""ADB device reboot stress test.

usage: adb_reboot_stress.py [-h] [-d float] [-c int]

optional arguments:
  -h, --help                     Show this help message and exit.
  -d float, --duration float     Duration of time to run stress test (in hrs).
  -c int, --count int            Number of devices/emulators connected.
"""

import subprocess
import time

import util

_ITERATIONS = 30


def test_reboot(dut):
    """Verify that rebooting the device is successful.

    Args:
      dut: Device under test.

    Returns:
      True if successful, else False.
    """
    arg = 'adb -s ' + str(dut) + ' reboot'
    process = subprocess.Popen(arg.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    success = True
    for line in output.split('\n'):
        if line.startswith('adb: error'):
            success = False
            print('\nERROR:\nFAILED to reboot device: ' + str(dut))
            print(output)

    return success


def wait_for_reboot(devices):
    """Wait for devices to become available again after reboot.

    Args:
      devices: List of devices to wait for.

    Returns:
      True if successful, else False.
    """
    # We currently just sleep for 2 minutes.
    # It would be better to check (perhaps via `adb shell`)
    # whether the devices are available again, with an appropriate timeout.
    time.sleep(2*60)


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

        # Verify successful reboot of each connected device.
        for dut in connected:
            success_reboot = test_reboot(dut)
            if not success_reboot:
                connection_error = True

        # Wait for devices to reboot.
        wait_for_reboot(devices)

        if connection_error:
            break

    if i == iterations - 1 and success and not connection_error:
        util.print_progress(i + 1, iterations, prefix='Progress:', suffix='Complete', bar_len=50)
        print('\nSUCCESS\n')


if __name__ == '__main__':
    args = util.parse_args()
    launcher(args.duration, args.count)