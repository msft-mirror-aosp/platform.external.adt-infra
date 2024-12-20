# Copyright 2024 The Android Open Source Project
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
from functools import partial

import pytest
from aemu.proto.emulator_controller_pb2 import KeyboardEvent
from emu.emulator import Emulator
from emu.timing import eventually


@pytest.fixture
async def keypress(emulator_controller):
    """Sends a keypress event to the emulator.

    Args:
        emulator_controller: The EmulatorControllerStub instance.
        key: The key to press.
        n_times: The number of times to press the key.
    """

    async def _keypress(key, n_times=1):
        for _ in range(n_times):
            logging.info("Sending %s key", key)
            await emulator_controller.sendKey(
                KeyboardEvent(key=key, eventType=KeyboardEvent.keypress)
            )
            await asyncio.sleep(0.5)  # Delay between key presses

    return _keypress


@pytest.fixture
async def awake(is_asleep, keypress):
    """Ensures the emulator is awake.

    If the emulator is currently asleep, sends a "Power" keypress to wake it up.

    Args:
        is_asleep: Fixture providing a coroutine to check if the emulator is asleep.
        keypress: Fixture providing a coroutine to send keypress events.
    """
    if await is_asleep():
        await keypress("Power")


@pytest.fixture
async def set_music_volume_to_one(avd):
    """Sets the music stream volume to 1.

    Args:
        avd: The emulator instance.
    """
    await avd.adb.shell("media volume --stream STREAM_MUSIC --set 1")


@pytest.fixture
async def is_asleep(avd):
    """Fixture to check if the emulator is asleep.

    Args:
        avd: The emulator instance.

    Returns:
        An awaitable coroutine that resolves to True if the emulator
        is asleep, False otherwise.
    """

    async def _is_asleep():  # Inner coroutine
        state = await avd.adb.shell("dumpsys power | grep mWakefulness=")
        return "Asleep" in state or "Dozing" in state

    return _is_asleep


@pytest.fixture
async def is_awake(avd):
    """Fixture to check if the emulator is awake.

    Args:
        avd: The emulator instance.

    Returns:
        An awaitable coroutine that resolves to True if the emulator
        is awake, False otherwise.
    """

    async def _is_awake():
        return "Awake" in await avd.adb.shell("dumpsys power | grep mWakefulness=")

    return _is_awake


async def get_volume(avd, stream_type="STREAM_MUSIC"):
    """Gets the current volume level for a given stream type.

    Args:
        avd: The emulator instance.
        stream_type: The type of audio stream. Defaults to "STREAM_MUSIC".

    Returns:
        The current volume level as an integer.

    Raises:
        AssertionError: If the specified stream type is not found in the dumpsys output.
    """

    async def audio_dump():
        return await avd.adb.shell("dumpsys audio")

    async def get_stream_volume_dump(output: list):
        dumpsys = await audio_dump()
        match = re.search(f"{stream_type}.*streamVolume:(\\d+)", dumpsys)
        if match is None:
            return False
        output.append(int(match.groups()[0]))
        return True

    volume = []
    assert await eventually(partial(get_stream_volume_dump, volume)), f(
        f"Couldn't detect the stream '{stream_type}' in the system dump after several attempts.\n"
        "Dump output (may be incomplete):\n"
        f"{await audio_dump()}"
    )
    return volume[0]


async def check_volume_changed(avd, initial_volume, increase=True):
    async def check_volume():
        current_volume = await get_volume(avd)
        if increase:
            return current_volume > initial_volume
        else:
            return current_volume < initial_volume

    return await eventually(check_volume)


async def check_screenshot_created(avd):
    return "Screenshot_" in await avd.adb.exec_out(
        "ls /storage/emulated/0/Pictures/Screenshots/"
    )


async def get_top_focused_root_task(avd):
    activities = await avd.adb.shell("dumpsys activity activities")
    match = re.search("topDisplayFocusedRootTask=(Task{[^}]*})", activities)
    return match.groups()[0] if match else None


async def check_root_task_contains_name(avd, name):
    focused_task = await get_top_focused_root_task(avd)
    return name in focused_task if focused_task else False


async def check_root_task_has_type(avd, expected_type):
    focused_task = await get_top_focused_root_task(avd)
    if not focused_task:
        return False
    task_type = re.search("type=([^ }]*)", focused_task).group(1)
    return task_type == expected_type if task_type else False


@pytest.mark.embedded
@pytest.mark.async_timeout(30)
async def test_emulator_controls_key_power(awake, keypress, is_asleep):
    await keypress("Power")
    assert await eventually(is_asleep)


@pytest.mark.embedded
@pytest.mark.async_timeout(30)
async def test_emulator_controls_key_power_2x(awake, keypress, is_asleep, is_awake):
    await keypress("Power")
    await keypress("Power")
    assert await eventually(is_awake)


@pytest.mark.embedded
@pytest.mark.async_timeout(30)
async def test_emulator_controls_key_volumeup(avd, set_music_volume_to_one, keypress):
    volume = await get_volume(avd)
    await keypress("AudioVolumeUp", 2)
    assert await check_volume_changed(
        avd, volume, increase=True
    ), f"Volume was not raised from {volume} (current: {await get_volume(avd)})"


@pytest.mark.embedded
@pytest.mark.async_timeout(30)
async def test_emulator_controls_key_volumedown(avd, set_music_volume_to_one, keypress):
    volume = await get_volume(avd)
    await keypress("AudioVolumeDown", 2)
    assert await check_volume_changed(
        avd, volume, increase=False
    ), f"Volume was not lowered from {volume} (current: {await get_volume(avd)})"


@pytest.mark.embedded
@pytest.mark.async_timeout(30)
async def test_emulator_controls_key_screenshot(avd):
    await avd.adb.shell("rm -rf /storage/emulated/0/Pictures/Screenshots/*")
    await avd.adb.shell("input keyevent 120")  # Screenshot key event
    assert await eventually(
        partial(check_screenshot_created, avd)
    ), "Screenshot not created"


@pytest.mark.embedded
@pytest.mark.async_timeout(30)
async def test_emulator_controls_key_back(avd, keypress, animation_app):
    await avd.start_activity(
        "com.google.android.apps.messaging/.ui.ConversationListActivity", params="-W"
    )
    assert await eventually(
        partial(check_root_task_contains_name, avd, "com.google.android.apps.messaging")
    ), "Could not find the messaging application on the foreground"

    await keypress("GoBack")
    assert await eventually(
        partial(check_root_task_contains_name, avd, "com.google.AnimateBox")
    )


@pytest.mark.embedded
@pytest.mark.async_timeout(30)
async def test_emulator_controls_key_home(avd, keypress, animation_app):
    await keypress("GoHome")
    assert await eventually(partial(check_root_task_has_type, avd, "home"))
