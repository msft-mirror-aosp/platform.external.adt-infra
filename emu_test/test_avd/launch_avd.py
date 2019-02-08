"""AVD Launch test.

Verify the emulator launched in AVD can be detected.

usage: launch_avd.py [-h] [-t TIMEOUT_IN_SECONDS] --avd AVD
                     [--exec EMULATOR_EXEC]
"""

import argparse
import logging
import multiprocessing.pool
import os
import subprocess
from subprocess import PIPE
import sys
import time
import threading
import unittest

import util
from utils.emu_error import LaunchError

import emu_test
from emu_test.utils import emu_argparser
from emu_test.utils.emu_testcase import EmuBaseTestCase, AVDConfig
import emu_test.utils.path_utils as path_utils

log = logging.getLogger('launch_avd')

def arg_parser():
    """Return argument parser for launch_avd test"""
    parser = argparse.ArgumentParser(description='Argument parser for emu test')

    parser.add_argument('-t', '--timeout', type=int, dest='timeout_in_seconds', action='store',
                        default=600,
                        help='an integer for timeout in seconds, default is 600')
    parser.add_argument('--exec', type=str, dest='emulator_exec', action='store',
                        default='emulator',
                        help='path of emulator executable, default is system emulator')
    parser.add_argument('unittest_args', nargs='*')
    return parser

class TimeoutError(Exception):
    """Exception raised for timeout.
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


def launch_emu(avd, emu_args, emu_log_stream, additional_args=None):
    """Launch given avd and return immediately"""
    log.debug('call Launching AVD, ...: %s' % str(avd))
    exec_path = emu_args.emulator_exec
    launch_cmd = [exec_path, "-avd", str(avd), "-verbose", "-show-kernel"]
    if additional_args:
        launch_cmd.extend(additional_args)

    if "emu-master-dev" in exec_path:
        launch_cmd += ["-skip-adb-auth"]

    log.info('Launching AVD, cmd: %s' % ' '.join(launch_cmd))
    start_proc = subprocess.Popen(launch_cmd,
                                  stderr=subprocess.STDOUT,
                                  stdout=emu_log_stream)
    log.info('done Launching AVD, cmd: %s' % ' '.join(launch_cmd))

    if start_proc.poll():
        raise LaunchError(str(avd))
    log.debug('return Launching AVD, ...: %s' % str(avd))
    return start_proc


def launch_emu_and_wait(avd, emu_args, emu_log_stream, additional_args=None):
    """Launch given avd and wait for boot completion, return boot time"""
    adb_binary = path_utils.get_adb_binary()
    run_with_timeout([adb_binary, "kill-server"], 20)
    run_with_timeout([adb_binary, "start-server"], 20)
    pool = multiprocessing.pool.ThreadPool(processes = 1)
    launcher_emu = pool.apply_async(launch_emu, [avd, emu_args, emu_log_stream, additional_args])
    start_time = time.time()
    completed = "0"
    real_time_out = emu_args.timeout_in_seconds;
    if 'swiftshader' in str(avd):
        real_time_out = real_time_out + emu_args.timeout_in_seconds
    if 'arm' in str(avd):
        real_time_out = real_time_out + emu_args.timeout_in_seconds;
    if 'mips' in str(avd):
        real_time_out = real_time_out + emu_args.timeout_in_seconds;

    # Initialize these to None, in case try block fails.
    output = None
    err = None

    while time.time()-start_time < real_time_out:
        cmd = [adb_binary, "shell", "getprop", "sys.boot_completed"]
        if launcher_emu.ready():
            emu_proc = launcher_emu.get()
            if emu_proc.poll():
                msg = 'Emulator process terminated with exit code {} before boot completed.'
                raise LaunchError(msg.format(emu_proc.returncode))

        try:
            (exit_code, output, err) = run_with_timeout(cmd, 10)
        except Exception as e:
            log.error('exception run_with_timeout adb getprop: %r' % e)
            continue
        if exit_code is 0:
            completed = output.strip()
        if completed == "1":
            log.info('AVD %s is fully booted' % str(avd))
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
    run_with_timeout([adb_binary, "kill-server"], 20)
    return success


class LaunchAVDTest(EmuBaseTestCase):
    def launch_avd(self, avd_config):
        self.avd_config = avd_config
        self.assertEqual(self.create_avd(avd_config), 0)
        test_name = self.id().rsplit('.', 1)[-1]
        emu_log_path = os.path.join(emu_argparser.emu_args.session_dir,
                                    emu_argparser.emu_args.test_dir,
                                    "%s_verbose.txt" % test_name)

        with open(emu_log_path, 'wb') as emu_log:
            return launch_emu_and_wait(avd_config,
                                       emu_argparser.emu_args,
                                       emu_log)


if emu_argparser.emu_args.config_file is None:
    sys.exit(-1)
else:
    emu_test.utils.emu_testcase.create_test_case_from_file(
        'launch_avd', LaunchAVDTest, LaunchAVDTest.launch_avd)


if __name__ == '__main__':
    os.environ['SHELL'] = '/bin/bash'
    emu_argparser.emu_args = emu_argparser.get_parser().parse_args()
    log.info(emu_argparser.emu_args)
    sys.argv[1:] = emu_argparser.emu_args.unittest_args
    unittest.main()
