"""ADB device reboot stress test.

usage: adb_reboot_stress.py [-h] [-d float] [-c int]

optional arguments:
  -h, --help                     Show this help message and exit.
  -d float, --duration float     Duration of time to run stress test (in hrs).
  -c int, --count int            Number of devices/emulators connected.
  -p, --progress                 Print progress
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
    return True


def test_device(dut):
    return test_reboot(dut) and wait_for_reboot(dut)


if __name__ == '__main__':
    args = util.parse_args()
    iterations = int(args.duration * _ITERATIONS)
    util.launcher(test_device, iterations, args.count, is_print_progress=args.progress)