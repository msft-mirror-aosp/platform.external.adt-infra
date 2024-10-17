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
    asyncio.wait_for(wait_for_keyboard(log, expected_code), 2)


@pytest.mark.hardware
async def test_hardware_keys(avd, at_home, emulator_log):
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
        await keypress_expects(avd, emulator_log, key, expect)


@pytest.mark.hardware
async def test_whitespace_chrs(avd, at_home, emulator_log):
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
        await keypress_expects(avd, emulator_log, key, expect)


@pytest.mark.hardware
async def test_unicode_no_deadlock(at_home, emulator_controller):
    """Tests that we properly handle unicode characters."""
    await emulator_controller.sendKey(
        KeyboardEvent(text="\xc6\x80 <-- Used to deadlock")
    )


@pytest.mark.sanity
@pytest.mark.embedded
@pytest.mark.async_timeout(50000)
async def test_emulator_controls_keys(avd, emulator_controller):
    """Ensure the emulator controls keys and events work.

    Args:
        avd (BaseEmulator): Fixture that gives access to the running emulator.
        emulator_controller (EmulatorControllerStub): Emulator controller fixture.

    Test Steps:
        1. Click on Power button (Verify 1).
        2. Click on Power button once again (Verify 2).
        3. Click on Volume Up and Down buttons (Verify 3).
        4. Click on Rotate Left and then Rotate Right (Verify 4).
        5. Click on Screenshot (Verify 5).
        6. Click on Back and Home (Verify 6).
        7. Click on the Extended Controls button (the three dots) (Verify 7).

    Verify:
        1. Emulator goes into sleep mode.
        2. Emulator wakes up and the lock screen is displayed.
        3. Emulator volume increases and decreases as the respective buttons are pressed.
        4. Emulator window switches between portrait and landscape mode.
        5. Screenshot of the emulator window is captured.
        6. Back button, home and recents work as expected.
        7. Extended Controls window is displayed.
    """

    async def keypress(key, n_times=1):
        # Send the keypress 'key' event 'n_time' times.
        for i in range(n_times):
            logging.info("Sending %s key", key)
            await emulator_controller.sendKey(
                KeyboardEvent(key=key, eventType=KeyboardEvent.keypress)
            )
            if n_times > 1:
                # Delay between successive key events.
                await asyncio.sleep(1)

        await asyncio.sleep(1)

    async def is_asleep():
        state = await avd.adb.shell("dumpsys power | grep mWakefulness=")
        return "Asleep" in state or "Dozing" in state

    async def is_awake():
        return "Awake" in await avd.adb.shell("dumpsys power | grep mWakefulness=")

    async def get_volume(stream_type="STREAM_MUSIC"):
        # Wait until 'stream_type' appears in dumpsys and return the current volume level.
        async def get_stream_volume_dump(output: list):
            # Return 'True' if the stream is observed in the system dump.
            # Store the volume level in the 'output' list.
            dumpsys = await avd.adb.shell("dumpsys audio")
            match = re.search(f"{stream_type}.*streamVolume:(\d+)", dumpsys)
            if match is None:
                return False
            output.append(int(match.groups()[0]))
            return True

        volume = []
        assert await eventually(
            partial(get_stream_volume_dump, volume)
        ), f"Coudn't detect the stream {stream_type} in the system dump"
        return volume[0]

    async def check_volume_raises(volume):
        current_volume = await get_volume()
        return current_volume > volume

    async def check_volume_lowers(volume):
        current_volume = await get_volume()
        return current_volume < volume

    async def apply_user_rotation(rotation):
        # Apply user rotation (0: Portrait, 1: Landscape, 2: Portrait Reversed, 3: Landscape Rev).
        await avd.adb.shell(
            f"content insert --uri content://settings/system \
                             --bind name:s:user_rotation --bind value:i:{rotation}"
        )

    async def check_display_rotation(expected_rotation):
        # Check if the current display rotation matches the expected rotation.
        displays_lines = await avd.adb.shell("dumpsys window displays")
        match = re.search("DisplayRotation.*mRotation=([0-9])\s", displays_lines)
        if match is None:
            return False
        current_rotation = int(match.groups()[0])
        return current_rotation == expected_rotation

    async def check_screenshot_created():
        # Return 'True' if a screenshot is present in the folder Screenshots/
        return (
            await avd.adb.shell(
                "ls /storage/emulated/0/Pictures/Screenshots/Screenshot_* > /dev/null 2>&1; echo $?"
            )
            == "0"
        )

    async def get_top_focused_root_task():
        # Return the name of the top focused root task
        activities = await avd.adb.shell("dumpsys activity activities")
        match = re.search("topDisplayFocusedRootTask=(Task{[^}]*})", activities)
        if match is None:
            return None
        return match.groups()[0]

    async def check_root_task_contains_name(name):
        # Return 'True' if the top focused root task contains 'name'.
        focused_task = await get_top_focused_root_task()
        if focused_task is None:
            return False
        return name in focused_task

    async def check_root_task_has_type(expected_type):
        # Return 'True' if the focused tasks has type equal to 'expected_type'.
        focused_task = await get_top_focused_root_task()
        if focused_task is None:
            return False
        type = re.search("type=(.*)}", focused_task).groups()[0]
        if type is None or type != expected_type:
            return False
        return True

    ############ Steps 1 and 2 - Power key ##

    # Click on Power button.
    await keypress("Power")
    assert await eventually(is_asleep)

    # Click on Power button again.
    await keypress("Power")
    assert await eventually(is_awake)

    ############ Step 3 - Volume keys ##

    # Click on Volume Up.
    volume = await get_volume()
    await keypress("AudioVolumeUp", 2)
    assert await eventually(
        partial(check_volume_raises, volume)
    ), "Volume was not raised"

    # Click on Volume Down.
    volume = await get_volume()
    await keypress("AudioVolumeDown", 2)
    assert await eventually(
        partial(check_volume_lowers, volume)
    ), "Volume was not lowered"

    ############ Step 4 - Rotation keys ##

    # Disable auto-rotation.
    await avd.adb.shell(
        "content insert --uri content://settings/system \
                        --bind name:s:accelerometer_rotation --bind value:i:0"
    )
    # Launch the Animation APK.
    assert await avd.start_activity(
        "com.google.AnimateBox/com.google.emu.MainActivity", params=None
    )
    # Rotate left (Landscape).
    await apply_user_rotation(1)
    assert await eventually(partial(check_display_rotation, 1))

    # Rotate right (Portrait).
    await apply_user_rotation(0)
    assert await eventually(partial(check_display_rotation, 0))
    await avd.stop_activity("com.google.AnimateBox")

    ########### Step 5 - Screenshot event ##

    # Empty the Screenshots folder.
    await avd.adb.shell("rm -rf /storage/emulated/0/Pictures/Screenshots/*")

    # Send a screenshot key event.
    await avd.adb.shell("input keyevent 120")

    # Verify a new screenshot is created.
    assert await eventually(check_screenshot_created), "A screenshot was not created"

    ########## Step 6 - Back and Home button ##

    # Launch the dialer app.
    await avd.start_activity(
        "com.google.android.dialer/.extensions.GoogleDialtactsActivity", params="-W"
    )
    # Launch the messaging app.
    await avd.start_activity(
        "com.google.android.apps.messaging/.ui.ConversationListActivity", params="-W"
    )
    # Check if the messaging app has the focus.
    assert await eventually(
        partial(check_root_task_contains_name, "com.google.android.apps.messaging")
    ), "Couldn't launch the messaging app"

    # Click on the Back button.
    await keypress("GoBack")
    # Check if the focus went back to the dialler app.
    assert await eventually(
        partial(check_root_task_contains_name, "com.google.android.dialer")
    ), "Couldn't go Back"

    # Click on Home button.
    await keypress("GoHome")

    # Check if the Home screen appears.
    assert await eventually(
        partial(check_root_task_has_type, "home")
    ), "Couldn't go Home"

    ##########  Step 7 - Extended Controls grpc event ##

    ui_controller = UiControllerStub(avd.channel)

    # Simulate a click on the extended controls button.
    controlStatus = await ui_controller.showExtendedControls(empty_pb2.Empty())
    # Verify the extended controls window appeared.
    assert controlStatus.visibilityChanged


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
