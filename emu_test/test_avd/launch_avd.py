"""AVD Launch test.

Verify the emulator launched in AVD can be detected.

usage: launch_avd.py [-h] [-t TIMEOUT_IN_SECONDS] --avd AVD
                     [--exec EMULATOR_EXEC]
"""

import argparse
import logging
import multiprocessing.pool
import subprocess
from subprocess import PIPE, STDOUT
import sys
import time
import threading
import unittest

import util

log = logging.getLogger('launch_avd')

def arg_parser():
    """Return argument parser for launch_avd test"""
    parser = argparse.ArgumentParser(description='Argument parser for emu test')

    parser.add_argument('-t', '--timeout', type=int, dest='timeout_in_seconds', action='store',
                        default=600,
                        help='an integer for timeout in seconds, default is 600')
    parser.add_argument('--avd', type=str, dest='avd', action='store',
                        required=True,
                        help='run test for given AVD')
    parser.add_argument('--exec', type=str, dest='emulator_exec', action='store',
                        default='emulator',
                        help='path of emulator executable, default is system emulator')
    parser.add_argument('unittest_args', nargs='*')
    return parser

class TimeoutError(Exception):
    """Exception raised for timeout

    Attributes:
        cmd -- cmd which timed out
        timeout  -- value of timeout
    """

    def __init__(self, cmd, timeout):
        self.cmd = cmd
        self.timeout = timeout

def run_with_timeout(cmd, timeout):
    """Run command with specified timeout.

    Args:
      cmd     - Required  : command to run
      timeout - Required  : timeout (in seconds)

    Returns:
      Tuple of form (returncode, output, err), where:
      * returncode is the exit code of the command
      * output is the stdout output of the command, collected into a string
      * err is the stderr output of the command, collected into a string
    """
    vars = {'output': "",
            'err': "",
            'process': None}

    def run_cmd():
        vars['process'] = subprocess.Popen(cmd, stdout=PIPE, stderr=PIPE)
        (vars['output'], vars['err']) = vars['process'].communicate()

    thread = threading.Thread(target=run_cmd)
    thread.start()

    thread.join(timeout)
    if thread.is_alive():
        log.debug('cmd %s timeout, force terminate' % ' '.join(cmd))
        try:
            vars['process'].terminate()
        except Exception as e:
            log.error('exception terminating adb getprop process: %r' % e)
    thread.join(timeout)
    return vars['process'].returncode, vars['output'], vars['err']


def launch_emu(avd, emu_args):
    """Launch given avd and return immediately"""
    log.debug('call Launching AVD, ...: %s' % str(avd))
    exec_path = emu_args.emulator_exec
    launch_cmd = [exec_path, "-avd", str(avd), "-verbose", "-show-kernel"]

    if "emu-master-dev" in exec_path:
        launch_cmd += ["-skip-adb-auth"]

    log.info('Launching AVD, cmd: %s' % ' '.join(launch_cmd))
    start_proc = subprocess.Popen(launch_cmd, stdout=PIPE, stderr=STDOUT)
    log.info('done Launching AVD, cmd: %s' % ' '.join(launch_cmd))

    if start_proc.poll():
        raise LaunchError(str(avd))
    log.debug('return Launching AVD, ...: %s' % str(avd))
    return start_proc


def launch_emu_and_wait(avd, emu_args):
    """Launch given avd and wait for boot completion, return boot time"""
    run_with_timeout(["adb", "kill-server"], 20)
    run_with_timeout(["adb", "start-server"], 20)
    pool = multiprocessing.pool.ThreadPool(processes = 1)
    launcher_emu = pool.apply_async(launch_emu, [avd, emu_args])
    start_time = time.time()
    completed = "0"
    real_time_out = emu_args.timeout_in_seconds;
    if 'swiftshader' in str(avd):
        real_time_out = real_time_out + emu_args.timeout_in_seconds
    if 'arm' in str(avd):
        real_time_out = real_time_out + emu_args.timeout_in_seconds;
    if 'mips' in str(avd):
        real_time_out = real_time_out + emu_args.timeout_in_seconds;
    while time.time()-start_time < real_time_out:
        cmd = ["adb", "shell", "getprop", "sys.boot_completed"]
        try:
            (exit_code, output, err) = run_with_timeout(cmd, 10)
        except Exception as e:
            log.error('exception run_with_timeout adb getprop: %r' % e)
            continue
        if exit_code is 0:
            completed = output.strip()
        if completed is "1":
            log.info('AVD %s is fully booted' % avd)
            break
        time.sleep(1)
    if completed is not "1":
        log.debug('command output - %s %s' % (output,err))
        log.error('AVD %s didn\'t boot up within %s seconds' % (avd,real_time_out))
        raise TimeoutError(avd, real_time_out)
    boot_time = time.time() - start_time
    log.debug('AVD %s, boot time is %s' % (avd, boot_time))
    emu_proc = launcher_emu.get(10)
    if util.get_connected_devices():
        success = True
    else:
        success = False
    emu_proc.terminate()
    return success


class LaunchAVDTest(unittest.TestCase):
    def test_launch_avd(self):
        args = arg_parser().parse_args()
        avd = args.avd
        return launch_emu_and_wait(avd, args)

if __name__ == '__main__':
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    log.addHandler(console_handler)
    log.setLevel(logging.DEBUG)
    suite = unittest.TestLoader().loadTestsFromTestCase(LaunchAVDTest)
    unittest.TextTestRunner(verbosity=2).run(suite)
