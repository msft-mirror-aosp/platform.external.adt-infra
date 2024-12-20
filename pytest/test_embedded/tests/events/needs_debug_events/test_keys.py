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
import asyncio
import logging
import re
import signal

import pytest
from aemu.proto.emulator_controller_pb2 import KeyboardEvent, InputEvent
from aemu.proto.emulator_controller_pb2_grpc import EmulatorControllerStub
from aemu.proto.ui_controller_service_pb2_grpc import UiControllerStub

from emu.logging.log_handler import AsyncLogHandler
from emu.timing import eventually
from functools import partial
from google.protobuf import empty_pb2
from tests.test_utils import get_window_dump, click_button
import platform


# Parse emulator log.
EMU_MANY_KEY_EVENT = re.compile(r".* (\d+): sendKeyCodes: \[([0-9a-fA-F ,]+)\]")
EMU_SINGLE_KEY_EVENT = re.compile(r".* (\d+): sendKeyCode: (\d+)")


async def wait_for_keyboard(event_stream: AsyncLogHandler, ev_code):
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
    async for line in event_stream:
        entry = EMU_MANY_KEY_EVENT.match(line)
        if entry:
            codes = [int(x, 16) for x in entry.group(2).split(",")]
            if ev_code in codes:
                return int(entry.group(1)) / 1000000
        entry = EMU_SINGLE_KEY_EVENT.match(line)
        if entry and ev_code == int(entry.group(2)):
            return int(entry.group(1)) / 1000000

    return 0


async def keypress_expects(avd, log, jskey, expected_code):
    """Sends a key press through grpc, and expecting the event on the emulator log."""
    stub = EmulatorControllerStub(avd.channel)

    logging.info("Sending %s, expecting %d", jskey, expected_code)
    await stub.sendKey(KeyboardEvent(key=jskey, eventType=KeyboardEvent.keypress))

    # There is some concurrency weirdness, so we are willing to wait a few sec
    # to see if all the events arrived.
    await asyncio.wait_for(wait_for_keyboard(log, expected_code), 2)


@pytest.mark.parametrize(
    "key, expected_code",
    [
        ("Power", 116),
        ("AppSwitch", 580),
        ("GoBack", 158),
        ("GoHome", 102),
        ("AudioVolumeUp", 115),
        ("AudioVolumeDown", 114),
    ],
)
async def test_hardware_keys(avd, emulator_log, key, expected_code):
    """Checks that the hardware key events that studio sends are working."""
    if not emulator_log:
        pytest.skip("Likely running under debugger without logger")

    await keypress_expects(avd, emulator_log, key, expected_code)


@pytest.mark.hardware
@pytest.mark.parametrize(
    "key, expected_code",
    [
        ("\x08", 14),  # Backspace
        ("\n", 28),  # Enter
        # "\x18", "KEYCODE_ESCAPE", You will need to send Javascript code.
        # "\x7f", "KEYCODE_DEL",  You will need to send Javascript code.
        (" ", 57),  # Space
    ],
)
async def test_whitespace_chrs(avd, emulator_log, key, expected_code):
    """Checks that the whitespace characters that studio sends are working."""
    if not emulator_log:
        pytest.skip("Likely running under debugger without logger")

    await keypress_expects(avd, emulator_log, key, expected_code)


@pytest.mark.hardware
async def test_unicode_no_deadlock(emulator_controller):
    """Tests that we properly handle unicode characters."""
    await emulator_controller.sendKey(
        KeyboardEvent(text="\xc6\x80 <-- Used to deadlock")
    )


@pytest.mark.sanity
@pytest.mark.async_timeout(2080)
@pytest.mark.flaky(reruns=0)
@pytest.mark.skipos("linux", "This is very flaky on linux b/365169284")
async def test_close_emulator(avd, logcat, screen_recorder):
    """Ensure the emulator windows closes cleanly.

    Args:
        avd (BaseEmulator): Fixture that gives access to the running emulator.

    Test Steps:
        1. Launch an emulator AVD.
        2. Send the kill command from the emulator console (Verify 1).
        3. Repeat step 1.
        4. Click and hold Power plus Volume Up buttons for a couple of seconds.
        5. Tap on "Power off" on the emulator (Verify 2).
        6. Restart the emulator.
        7. Send the Control + C (SIGINT) event to the emulator process (Verify 3).

    Verification:
        1. Emulator window closes.
        2. Emulator shuts down and window closes.
        3. Emulator window closes.
    """

    def emulator_is_off():
        return not avd.is_alive()

    async def open_power_menu():
        # Triger the Power Options menu and return 'True' when it is opened.
        # Send Volume Up and Power keystrokes.
        # await avd.adb.shell(
        #     "input keyevent KEYCODE_VOLUME_UP & \
        #                      input keyevent KEYCODE_POWER"
        # )
        stub = EmulatorControllerStub(avd.channel)
        events = [
            InputEvent(key_event=x)
            for x in [
                KeyboardEvent(key="AudioVolumeUp", eventType=KeyboardEvent.keydown),
                KeyboardEvent(key="Power", eventType=KeyboardEvent.keydown),
                KeyboardEvent(key="AudioVolumeUp", eventType=KeyboardEvent.keyup),
                KeyboardEvent(key="Power", eventType=KeyboardEvent.keyup),
            ]
        ]
        stub.streamInputEvent(events)
        window_dump = await get_window_dump(avd)
        if 'text="Power off"' not in window_dump:
            await asyncio.sleep(5)
            return False
        return True

    # Ensure the emulator goes off following a 'kill' event (emulator window closed)
    console = await avd.console()
    await console.send("kill")
    assert await eventually(
        emulator_is_off
    ), "The emulator was not shut down after the window was closed."

    await avd.restart(avd.launch_flags)
    await avd.wait_for_boot()

    # Ensure the emulator shuts down after the Power off button is tapped.
    assert await eventually(open_power_menu), "Couldn't open the Power options menu."

    assert await click_button(
        avd, text="Power off"
    ), "Couldn't click the Power off button."

    assert await eventually(
        emulator_is_off
    ), "The emulator was not shut down after the Power off button was clicked."

    await avd.restart(avd.launch_flags)
    await avd.wait_for_boot()

    # Ensure the emulator shuts down after the CTRL-C event is sent
    CTRL_C = signal.SIGINT if platform.system() != "Windows" else signal.CTRL_C_EVENT
    avd.cmd.process.send_signal(CTRL_C)
    assert await eventually(
        emulator_is_off
    ), "The emulator was not shut down after the CTRL-C event was sent."
