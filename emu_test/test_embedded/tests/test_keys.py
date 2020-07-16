# Copyright 2020 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import logging
import re
import time

import pytest
from aemu.proto.emulator_controller_pb2 import KeyboardEvent

# The android keymap to codes
# https://developer.android.com/reference/android/view/KeyEvent
ANDROID_KEY_CODE_MAP = {
    "KEYCODE_UNKNOWN": 0,
    "KEYCODE_SOFT_LEFT": 1,
    "KEYCODE_SOFT_RIGHT": 2,
    "KEYCODE_HOME": 3,
    "KEYCODE_BACK": 4,
    "KEYCODE_ENDCALL": 6,
    "KEYCODE_VOLUME_UP": 24,
    "KEYCODE_VOLUME_DOWN": 25,
    "KEYCODE_POWER": 26,
    "KEYCODE_CAMERA": 27,
    "KEYCODE_ENTER": 66,
    "KEYCODE_DEL": 67,
    "KEYCODE_SPACE": 62,
    "KEYCODE_APP_SWITCH": 187,
}


def get_latest_keyevents(emulator):
    """This gets a list of the latest #nr keyevents by calling dumpsys, note you can see old events!"""
    KEVENT_LINE = re.compile(r"\s*KeyEvent\(.*action=(UP|DOWN),.*keyCode=(\d+).*")
    sout = emulator.adb(["shell", "dumpsys", "input"])
    # Parse this:
    #   KeyEvent(deviceId=0, source=0x00000101, displayId=-1, action=DOWN, flags=0x00000008, keyCode=187, scanCode=580, metaState=0x00000000, repeatCount=0), policyFlags=0x62000000, age=1964.6

    events = []
    for line in sout.splitlines():
        # logging.info("Line: %s", line)
        m = KEVENT_LINE.match(line)
        if m:
            events.append((m.group(1), int(m.group(2))))  # Action, keyCode

    return events


def keypress_expects(emulator, jskey, expected_code):
    """Sends a key press through grpc, and expecting the event on adb."""
    stub = emulator.get_emulator_controller()

    logging.info(
        "Sending %s, expecting %s = %d",
        jskey,
        expected_code,
        ANDROID_KEY_CODE_MAP[expected_code],
    )
    stub.sendKey(KeyboardEvent(key=jskey, eventType=KeyboardEvent.keypress))

    # There is some concurrency weirdness, so we are willing to wait a few sec
    # to see if all the events arrived.
    timeout = time.time() + 2
    expected_codes = [
        ("DOWN", ANDROID_KEY_CODE_MAP[expected_code]),
        ("UP", ANDROID_KEY_CODE_MAP[expected_code]),
    ]
    codes = []
    while expected_codes and time.time() < timeout:
        # Retrieve the latest received codes and validate that they are as expected.
        codes = get_latest_keyevents(emulator)
        expected_codes = [x for x in expected_codes if x not in codes]

    assert not expected_codes, "{} not in {}".format(expected_codes, codes)


@pytest.mark.e2e
def test_hardware_keys(at_home):
    """Checks that the hardware key events that studio sends are working."""
    expected = [
        # see https://developer.android.com/reference/android/view/KeyEvent# for event values
        ("Power", "KEYCODE_POWER"),
        ("AppSwitch", "KEYCODE_APP_SWITCH"),
        ("GoBack", "KEYCODE_BACK"),
        ("GoHome", "KEYCODE_HOME"),
        ("AudioVolumeUp", "KEYCODE_VOLUME_UP"),
        ("AudioVolumeDown", "KEYCODE_VOLUME_DOWN"),
    ]

    for key, expect in expected:
        keypress_expects(pytest.emulator, key, expect)


@pytest.mark.e2e
def test_whitespace_chrs(at_home):
    """Checks that the whitespace characters that studio sends are working."""
    expected = [
        ("\x08", "KEYCODE_DEL"),
        ("\n", "KEYCODE_ENTER"),
        # "\x18", "KEYCODE_ESCAPE", You will need to send Javascript code.
        (" ", "KEYCODE_SPACE"),
        # "\x7f", "KEYCODE_DEL",  You will need to send Javascript code.
    ]

    for key, expect in expected:
        keypress_expects(pytest.emulator, key, expect)


@pytest.mark.e2e
@pytest.mark.timeout(10)
def test_unicode_no_deadlock(at_home):
    """Tests that we properly handle unicode characters."""
    pytest.emulator.get_emulator_controller().sendKey(
        KeyboardEvent(text="\xc6\x80 <-- Used to deadlock")
    )
