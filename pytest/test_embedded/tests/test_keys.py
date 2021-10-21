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

# Parse emulator log.
EMU_MANY_KEY_EVENT = re.compile(r".* (\d+): sendKeyCodes: \[([0-9a-fA-F ,]+)\]")
EMU_SINGLE_KEY_EVENT = re.compile(r".* (\d+): sendKeyCode: (\d+)")


def wait_for_keyboard(event_stream, ev_code, timeout=10):
    """Wait for the evdev value to occur in the given event stream

    Args:
        event_stream: A queue that produces log lines which contain
          ev dev values.
        ev_code: The evdev code we are looking for.
        timeout: Maximum time in seconds we are willing to wait.

    Returns:
         the time in epoch seconds when this event occurred, or 0
         if the event did not arrive before the timeout was reached.
    """
    until = time.time() + timeout
    while time.time() < until:
        while not event_stream.empty():
            line = event_stream.get(False)
            entry = EMU_MANY_KEY_EVENT.match(line)
            if entry:
                codes = [int(x, 16) for x in entry.group(2).split(",")]
                if ev_code in codes:
                    return int(entry.group(1)) / 1000000
            entry = EMU_SINGLE_KEY_EVENT.match(line)
            if entry and ev_code == int(entry.group(2)):
                return int(entry.group(1)) / 1000000

    return 0


def keypress_expects(emulator, log, jskey, expected_code):
    """Sends a key press through grpc, and expecting the event on the emulator log."""
    stub = emulator.get_emulator_controller()

    logging.info("Sending %s, expecting %d", jskey, expected_code)
    stub.sendKey(KeyboardEvent(key=jskey, eventType=KeyboardEvent.keypress))

    # There is some concurrency weirdness, so we are willing to wait a few sec
    # to see if all the events arrived.
    timeout = time.time() + 2
    wait_for_keyboard(log, expected_code, timeout)


@pytest.mark.e2e
@pytest.mark.timeout(timeout=5, func_only=True)
def test_hardware_keys(at_home, emulator_log):
    """Checks that the hardware key events that studio sends are working."""
    if not emulator_log:
        pytest.skip("Likely running under debugger without logger")

    expected = [
        # see https://developer.android.com/reference/android/view/KeyEvent# for event values
        ("Power", 116),
        ("AppSwitch", 580),
        ("GoBack", 158),
        ("GoHome", 102),
        ("AudioVolumeUp", 115),
        ("AudioVolumeDown", 114),
    ]

    for key, expect in expected:
        keypress_expects(pytest.emulator, emulator_log, key, expect)


@pytest.mark.e2e
@pytest.mark.timeout(timeout=5, func_only=True)
def test_whitespace_chrs(at_home, emulator_log):
    """Checks that the whitespace characters that studio sends are working."""
    if not emulator_log:
        pytest.skip("Likely running under debugger without logger")

    expected = [
        ("\x08", 14),
        ("\n", 28),
        # "\x18", "KEYCODE_ESCAPE", You will need to send Javascript code.
        (" ", 57),
        # "\x7f", "KEYCODE_DEL",  You will need to send Javascript code.
    ]

    for key, expect in expected:
        keypress_expects(pytest.emulator, emulator_log, key, expect)


@pytest.mark.e2e
@pytest.mark.timeout(timeout=10, func_only=True)
def test_unicode_no_deadlock(at_home):
    """Tests that we properly handle unicode characters."""
    pytest.emulator.get_emulator_controller().sendKey(
        KeyboardEvent(text="\xc6\x80 <-- Used to deadlock")
    )
