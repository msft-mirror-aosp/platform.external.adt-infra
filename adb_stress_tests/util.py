"""ADB stress test utilities."""

from multiprocessing import pool

import argparse
import os
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


def noop():
    """Function that does absolutely nothing.
    This is useful as a placeholder / default function
    for function arguments, such as the setup and teardown arguments
    of the launcher function.
    """
    pass


def launcher(test_fn, iterations, devices, setup=noop, cleanup=noop, is_print_progress=False, log_dir='logs'):
    """Higher-order function for launching tests

        Args:
            test_fn: Function that executes a single iteration of a test. This function must take a single argument,
                     which is the device under test, and must return a boolean value indicating the success (True)
                     or failure (False) of the test. Failure may also be indicated by raising an exception.
            iterations: Number of iterations to execute.
            devices: Number of expected devices.
            setup: Function that performs any necessary setup steps before the test is run
                   (optional — defaults to noop).
            cleanup: Function that performs any necessary cleanup steps after the test is run
                     (optional — defaults to noop).
            is_print_progress: If True, progress information is printed to stdout after each iteration of the test.
                               If False (the default), progress information is not printed.
                               If any other value (i.e., non-boolean) is provided for this argument,
                               the behaviour of this function is undefined.
            log_dir: base directory under which logs will be placed.

        Returns:
            True if the test ran successfully to completion, otherwise False.
        """

    # ThreadPool for running the tests in parallel.
    # We choose the size to match the number of devices, so that every device can execute in parallel.
    thread_pool = pool.ThreadPool(processes = devices)

    try:
        setup()
        for i in range(iterations):
            if is_print_progress:
                print_progress(i, iterations, prefix='Progress:', suffix='Complete', bar_len=50)
            connection_success, connected = test_connected(devices)
            if not connection_success:
                return False

            # Run one iteration of the test against every device in parallel
            results = thread_pool.map(test_fn, connected)

            # Verify the results
            for result in results:
                if not result:
                    return False

            # Capture logcat.
            logs = thread_pool.map(logcat, connected)
            for device,log in zip(connected, logs):
                filename = os.path.join(log_dir, device, str(i) + '.txt')
                spit(filename, log)

        # If we get here, the test completed successfully.
        if is_print_progress:
            # Print the progress bar one last time, to show 100%.
            print_progress(i + 1, iterations, prefix='Progress:', suffix='Complete', bar_len=50)
        print('\nSUCCESS\n')
        return True
    finally:
        cleanup()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-d', '--duration', metavar='float', type=float, default=1,
        help='Duration of time to run stress test (in hrs)')
    parser.add_argument(
        '-c', '--count', metavar='int', type=int, default=1,
        help='Number of devices/emulators connected')
    parser.add_argument(
        '-p', '--progress', default=False,
        action='store_const', const=True,
        help='Print progress')
    parser.add_argument(
        '--log-dir', type=str, default='logs',
        help='Directory under which log files will be placed (defaults to "logs")')
    return parser.parse_args()


def adb(dut):
    """Helper function for running adb commands.

    Args:
      dut: Device under tests.
      cmd: List containing adb command to run arguments.

    Returns:
      String containing the comand's output.
    """
    adb_cmd = ['adb', '-s', dut] + cmd
    return subprocess.check_output(adb_cmd)


def logcat(dut, cmd):
    """Get logcat of specified device.

    Args:
      dut: Device under test.
      cmd: List containing adb command to run arguments.

    Returns:
      String containing the command's output.
    """
    cmd = ['shell', 'logcat', '-d', '-v', 'threadtime']
    return adb(dut, cmd)


def spit(filename, text):
    """Writes given text to specified file.

    Args:
      filename: Name of file to write to.
      text: The text to write.
    """
    # Ensure the enclosing directory exists.
    directory = os.path.dirname(filename)
    if not os.path.exists(directory):
        os.makedirs(directory)

    # Write the file.
    out_file = open(filename, 'w+')
    out_file.write(text)
    out_file.close()
