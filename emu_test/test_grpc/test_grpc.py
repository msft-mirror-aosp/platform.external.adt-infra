"""Test the emulator Grpc grpc endpoints."""

import datetime
import os
import shutil
import socket
import sys
import string
import time
import unittest
from contextlib import closing

import psutil

import emu_test.utils.emu_testcase
import emu_test.utils.path_utils as path_utils
from emu_test.test_grpc.keymap import ANDROID_KEY_CODE_MAP
from emu_test.test_grpc.emulator_service import EmulatorService
from emu_test.test_grpc.waterfall_adb import WaterfallService
from emu_test.utils.emu_argparser import emu_args, get_parser
from emu_test.utils.emu_error import TimeoutError
from emu_test.utils.emu_testcase import AVDConfig, EmuBaseTestCase


class GrpcTestCase(EmuBaseTestCase):
    def __init__(self, *args, **kwargs):
        super(GrpcTestCase, self).__init__(*args, **kwargs)
        self.avd_config = None

    @classmethod
    def setUpClass(cls):
        super(GrpcTestCase, cls).setUpClass()

    def kill_emulator(self):
        self.m_logger.debug("First try - quit emulator by adb emu kill")
        adb_binary = path_utils.get_adb_binary()
        psutil.Popen([adb_binary, "emu", "kill"]).communicate()
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
        avd_dir = os.environ["ANDROID_AVD_HOME"]
        try:
            os.remove(os.path.join(avd_dir, "%s.ini" % self.avd_config.name()))
            shutil.rmtree(
                os.path.join(avd_dir, "%s.avd" % self.avd_config.name()),
                ignore_errors=True,
            )
        except Exception, e:
            self.m_logger.error("Error in cleanup - %r" % e)
            pass

    def keypress_expects(self, jskey, expected_code, events_per_key=1):
        """Sends a key press through grpc, and expecting the event on adb."""
        self.m_logger.info(
            "Sending %s, expecting %s = %d",
            jskey,
            expected_code,
            ANDROID_KEY_CODE_MAP[expected_code],
        )
        self.emu.sendKeyPress(jskey)

        # There is some concurrency weirdness, so we are willing to wait a few sec
        # to see if all the events arrived.
        timeout = time.time() + 2
        expected_codes = [
            (ANDROID_KEY_CODE_MAP[expected_code], "DOWN"),
            (ANDROID_KEY_CODE_MAP[expected_code], "UP"),
        ]
        evts = []
        good = False
        while not good and time.time() < timeout:
            good = True
            # Retrieve the latest received codes and validate that they are as expected.
            evts = self.wfall.get_latest_keyevents()
            codes = [(int(x.keyCode), x.action) for x in evts]
            for expect in expected_codes:
                if expect in codes:
                    good = expect and good

        self.assertTrue(
            good,
            msg="Send [{}], expecting to read code: {} down got: {}".format(
                jskey, expected_code, " ".join([str(e) for e in evts])
            ),
        )

    def check_keyevents(self):
        """Checks that the set of key events are processed as expected."""
        self.keypress_expects(
            "AppSwitch", "KEYCODE_APP_SWITCH"
        )  # https://developer.android.com/reference/android/view/KeyEvent#KEYCODE_APP_SWITCH
        self.keypress_expects(
            "GoBack", "KEYCODE_BACK"
        )  # https://developer.android.com/reference/android/view/KeyEvent#KEYCODE_BACK
        self.keypress_expects(
            "GoHome", "KEYCODE_HOME"
        )  # https://developer.android.com/reference/android/view/KeyEvent#KEYCODE_HOME

        self.keypress_expects(
            "Power", "KEYCODE_POWER"
        )  # https://developer.android.com/reference/android/view/KeyEvent#KEYCODE_HOME

    def check_ascii_keys(self):
        """Checks that we send and receive letters."""
        # We can send some special ascii codes.
        expected_map = {
            "\x08": "KEYCODE_DEL",
            "\n": "KEYCODE_ENTER",
            # "\x18": "KEYCODE_ESCAPE", You will need to send Javascript code.
            " ": "KEYCODE_SPACE",
            # "\x7f": "KEYCODE_DEL",  You will need to send Javascript code.
        }

        for key in expected_map:
            self.keypress_expects(key, expected_map[key])

        for letter in string.ascii_lowercase + "1234567890":
            code = "KEYCODE_{}".format(letter).upper()
            self.keypress_expects(letter, code)

    def do_not_lock(self):
        self.emu.sendText("\xc6\x80 <-- Used to deadlock")
        self.keypress_expects("x", "KEYCODE_X")

    def check_all(self, avd):
        try:
            self.launch_emu_and_wait(
                avd, ["-waterfall", "adb"]
            )
            self.m_logger.debug("Emulator is up and ready")
        except TimeoutError:
            self.m_logger.error("AVD %s, time out.." % str(avd))
            return

        try:
            self.m_logger.debug("Init things")
            self.wfall = WaterfallService(self.m_logger)
            self.emu = EmulatorService(self.m_logger)
        except:
            self.m_logger.error("Fatal error in main test", exc_info=True)
            self.fail()

        # Add your test below here.
        self.do_not_lock()
        self.check_keyevents()
        self.check_ascii_keys()

    def run_grpc_tests(self, avd_config):
        self.avd_config = avd_config
        if self.create_avd(avd_config) == 0:
            self.check_all(avd_config)


def create_test_case_for_avds():
    avd_list = emu_args.avd_list
    for avd in avd_list:

        def fn(i):
            return lambda self: self.all_tests(i)

        setattr(GrpcTestCase, "test_Grpc_%s" % avd, fn(avd))


if emu_args is None or emu_args.config_file is None:
    emu_args = get_parser().parse_args()
    create_test_case_for_avds()
else:
    emu_test.utils.emu_testcase.create_test_case_from_file(
        "Grpc", GrpcTestCase, GrpcTestCase.run_grpc_tests
    )

if __name__ == "__main__":
    os.environ["SHELL"] = "/bin/bash"
    emu_args = get_parser().parse_args()
    sys.argv[1:] = emu_args.unittest_args
    unittest.main()
