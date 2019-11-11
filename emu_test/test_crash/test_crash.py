"""Test the emulator crash grpc endpoints."""

import glob
import os
import platform
import shutil
import socket
import tempfile
import time
import traceback
import unittest
from contextlib import closing

import psutil

import emu_test.utils.emu_testcase
import emu_test.utils.path_utils as path_utils
from emu_test.test_crash.symbol_processor import SymbolProcessor
from emu_test.utils.emu_argparser import emu_args
from emu_test.utils.emu_error import *
from emu_test.utils.emu_testcase import AVDConfig, EmuBaseTestCase
from emu_test.utils.emulator_connection import EmulatorConnection


class TemporaryDirectory(object):
    """Self deleting temp dir."""

    def __enter__(self):
        self.location = tempfile.mkdtemp()
        return self.location

    def __exit__(self, exc_type, exc_value, traceback):
        shutil.rmtree(self.location)


class crashTestCase(EmuBaseTestCase):
    def __init__(self, *args, **kwargs):
        super(crashTestCase, self).__init__(*args, **kwargs)
        self.avd_config = None
        self.android_home = os.path.join(os.path.expanduser("~"), ".android")
        self.fhandle = None

    def __del__(self):
        if self.fhandle:
            close(self.fhandle)

    @classmethod
    def setUpClass(cls):
        super(crashTestCase, cls).setUpClass()

    def breakpad_files(self):
        breakpad_dmps = os.path.join(self.android_home, "breakpad", "*.dmp")
        return glob.glob(breakpad_dmps)

    def grab_minidump(self, minidump_dest):
        """Tries to grab a minidump and copies it to the given destination."""

        # Okay, this is a bit of a hack.
        # We have a separate process that captures the .dmp file. This process takes
        # some time to complete, once that process completes the .dmp file will be deleted.
        # we have to grab it before it disappears.
        list_of_files = self.breakpad_files()
        # Let's try for at most 10 seconds..
        timeout = time.time() + 10
        while not list_of_files and time.time() < timeout:
            self.m_logger.info(
                "Waiting for mini dump in %s/breakpad", self.android_home
            )
            list_of_files = self.breakpad_files()
            time.sleep(0.1)

        if not list_of_files:
            self.m_logger.info(
                "Did not find a minidump file in %s/breakpad", self.android_home
            )
            self.fail("No minidump was found.")

        latest_file = max(list_of_files, key=os.path.getctime)

        # Okay, we need to wait until the dumpfile is really completed, so just open an fd
        # so deletion will not happen until we are finished..
        self.fhandle = open(latest_file, "r")

        # And now we just check until the file size has not changed.
        size = -1
        while size != os.stat(latest_file).st_size:
            size = os.stat(latest_file).st_size
            time.sleep(0.2)

        shutil.copy2(latest_file, minidump_dest)
        self.m_logger.info("Copied %s -> %s", latest_file, minidump_dest)

    def crash(self, connection):
        """Send the crash command to the emulator.

        This should cause an immediate crash, which will cause
        a disconnect.

        Note: This will NOT WORK with emulators that are not build
        with crash support!!
        """
        timeout = time.time() + 5
        while not connection.is_connected() and time.time() < timeout:
            self.m_logger.info("Waiting for connection...")
            time.sleep(0.2)

        self.m_logger.info("Sending crash signal!")
        connection.send("crash")

    def check_trace(self, syms, regex):
        trace = syms.trace_has(regex)
        self.m_logger.info("%s -> %s", regex, trace)
        return trace

    def check_minidump(self, symbols, stackwalker, minidump):
        # Translate the dump into something human readable.
        syms = SymbolProcessor(symbols, stackwalker)
        syms.decode_stack_trace(minidump)

        # There are 2 ways in which we can detect a crash.

        # 1. Immediate. Note that our symbols might have mangled C++
        # functions, which can be mangled differently from compiler
        # to compiler, so we just look for some readable names.
        IMMEDIATE_CRASH = [
            r".*0.*!.*GenerateDumpAndDie.*",
            r".*1.*!.*crashhandler_die.*",
            r".*2.*!.*crash.*",
            r".*3.*!.*do_crash.*",
            r".*4.*!.*control_client_do_command.*",
            r".*5.*!.*control_client_read.*",
        ]

        # 2. Through our hang detector (happens regularly on windows).
        HANG_DETECTED = [
            r".*3.*!.*workerThread.*",
            r".*4.*!.*HangDetector.*",
            r".*5.*!.*Thread.*",
        ]

        # We need to have a matching call stack.
        if not (
            all([self.check_trace(syms, sym) for sym in IMMEDIATE_CRASH])
            or all([self.check_trace(syms, sym) for sym in HANG_DETECTED])
        ):
            self.m_logger.error("No match found in %s", syms.decoded)
            self.fail("Symbols not found")

    def kill_emulator(self):
        self.m_logger.debug("First try - quit emulator by adb emu kill")
        adb_binary = path_utils.get_adb_binary()
        _ = psutil.Popen([adb_binary, "emu", "kill"]).communicate()
        # check emulator process is terminated
        result = self.term_check(timeout=5)
        if not result:
            self.m_logger.info("Second try - quit emulator by psutil")
            self.kill_proc_by_name(["emulator", "qemu-system"])
            result = self.term_check(timeout=10)
            self.m_logger.info("term_check after psutil.kill - %s" % result)
        try:
            self.m_logger.debug("kill adb and crash-service")
            if result and self.start_proc:
                self.start_proc.wait()
            time.sleep(1)
            self.kill_proc_by_name(["crash-service", "adb"])
        except Exception, e:
            self.m_logger.error("Error in cleanup - %r" % e)
            pass
        self.m_logger.debug("Killed emulator done")

    def tearDown(self):
        self.kill_emulator()
        self.m_logger.info("Remove AVD inside of tear down")
        # avd should be found $HOME/.android/avd/
        avd_dir = os.path.join(os.path.expanduser("~"), ".android", "avd")
        try:
            os.remove(os.path.join(avd_dir, "%s.ini" % self.avd_config.name()))
            shutil.rmtree(
                os.path.join(avd_dir, "%s.avd" % self.avd_config.name()),
                ignore_errors=True,
            )
        except Exception, e:
            self.m_logger.error("Error in cleanup - %r" % e)
            pass

    def do_crash_check(self, port):
        symbols = os.path.join(emu_args.session_dir, "emu-master-dev-dbg")
        stack_walker = os.path.join(
            emu_args.session_dir, "emu-master-dev-dbg", "tests", "minidump_stackwalk"
        )
        if platform.system() == "Windows":
            stack_walker += ".exe"

        self.m_logger.info("Checking port %s with %s", port, stack_walker)
        connection = EmulatorConnection.connect(port, self.m_logger)
        self.crash(connection)
        with TemporaryDirectory() as t:
            dmp = os.path.join(t, "minidump")
            self.grab_minidump(dmp)
            self.check_minidump(symbols, stack_walker, dmp)

    def crash_check(self, avd):
        for dmp_file in self.breakpad_files():
            self.m_logger.info("Removing lingering minidump: %s.", dmp_file)
            os.remove(dmp_file)

        try:
            self.launch_emu_and_wait(avd)
            self.m_logger.debug("Emulator is up and ready")
        except TimeoutError:
            self.m_logger.error("AVD %s, time out..", avd)
            self.fail("Timeout while launching the emulator")
            return

        try:
            # We should get the proper port from the emulator itself
            self.do_crash_check(5554)
        except:
            self.m_logger.error("Fatal error in main test", exc_info=True)
            self.fail("Fatal exception in test, check the logs.")
            return False

    def run_crash_test(self, avd_config):
        self.m_logger.info("Running run_crash_test")
        self.avd_config = avd_config
        if self.create_avd(avd_config) == 0:
            self.crash_check(avd_config)


def create_test_case_for_avds():
    avd_list = emu_args.avd_list
    for avd in avd_list:

        def fn(i):
            return lambda self: self.crash_check(i)

        setattr(crashTestCase, "test_crash_%s" % avd, fn(avd))


if emu_args.config_file is None:
    create_test_case_for_avds()
else:
    emu_test.utils.emu_testcase.create_test_case_from_file(
        "crash", crashTestCase, crashTestCase.run_crash_test
    )

if __name__ == "__main__":
    os.environ["SHELL"] = "/bin/bash"
    emu_argparser.emu_args = emu_argparser.get_parser().parse_args()
    print emu_argparser.emu_args
    sys.argv[1:] = emu_args.unittest_args
    unittest.main()
