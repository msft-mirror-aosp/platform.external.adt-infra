"""ADB stress test utilities."""

import argparse
import subprocess
import sys


def print_progress(iteration, total, prefix='',
                   suffix='', decimals=1, bar_len=100):
    """Call in a loop to create terminal progress bar.

    Args:
      iteration   - Required  : current iteration (Int)
      total       - Required  : total iterations (Int)
      prefix      - Optional  : prefix string (Str)
      suffix      - Optional  : suffix string (Str)
      decimals    - Optional  : pos number of decimals in % complete (Int)
      barLength   - Optional  : character length of bar (Int)
    """
    format_str = '{0:.' + str(decimals) + 'f}'
    perc = format_str.format(100 * (iteration / float(total)))
    filled_len = int(round(bar_len * iteration / float(total)))
    bar = '*' * filled_len + '-' * (bar_len - filled_len)
    sys.stdout.write('\r%s |%s| %s%s %s' % (prefix, bar, perc, '%', suffix)),
    if iteration == total:
        sys.stdout.write('\n')
    sys.stdout.flush()


def test_connected(devices):
    """Verify that the expected number of devices/emulators are still connected.

    Args:
      devices: Number of expected devices.

    Returns:
      A tuple of form (success, connected).
      The success member indicates whether the expected number
      of devices were found.
      The connected member contains a list of device serial numbers
      identifying the connected devices.
    """
    proc = subprocess.Popen('adb devices'.split(), stdout=subprocess.PIPE)
    output, error = proc.communicate()
    connected = []
    # verify expected emulators/devices are present
    for emulator_entry in output.split('\n')[1:]:
        if emulator_entry != '':
            connected.append(emulator_entry.split('\t')[0])

    success = True
    if len(connected) != devices:
        print('\n\nERROR:\nExpected number of connections: ' +
              str(devices))
        print('Found: ' + str(len(connected)))
        success = False

    return success, connected

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-d', '--duration', metavar='float', type=float, default=1,
        help='Duration of time to run stress test (in hrs)')
    parser.add_argument(
        '-c', '--count', metavar='int', type=int, default=1,
        help='Number of devices/emulators connected')
    return parser.parse_args()
