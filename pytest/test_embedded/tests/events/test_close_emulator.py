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
"""Contains a set of tests to turn off the emulator."""
import asyncio
import logging
import platform
import signal

import pytest
from aemu.proto.emulator_controller_pb2 import InputEvent, KeyboardEvent

from emu.timing import eventually
from tests.test_utils import click_button, get_window_dump


@pytest.fixture
async def emulator_is_off(avd):
    """Provides a function to check if the emulator is off.

    Args:
        avd: The emulator instance.

    Returns:
        A function that returns True if the emulator is off, False otherwise.
    """

    def _emulator_is_off():
        return not avd.is_alive()

    return _emulator_is_off


@pytest.fixture
async def open_power_menu(emulator_controller):
    """Provides a coroutine to open the power menu in the emulator.

    Sends a sequence of key events (Volume Up + Power) to trigger the power menu.

    Args:
        emulator_controller: Fixture to interact with the emulator.

    Returns:
        A coroutine that opens the power menu.
    """

    async def long_press_power_button_down():
        logging.info("Sending [Volume up] and [Power] keydown events")
        yield InputEvent(
            key_event=KeyboardEvent(
                key="AudioVolumeUp", eventType=KeyboardEvent.keydown
            )
        )
        yield InputEvent(
            key_event=KeyboardEvent(key="Power", eventType=KeyboardEvent.keydown)
        )

    async def long_press_power_button_up():
        logging.info("Sending [Volume up] and [Power] keydown events")
        yield InputEvent(
            key_event=KeyboardEvent(key="AudioVolumeUp", eventType=KeyboardEvent.keyup)
        )
        yield InputEvent(
            key_event=KeyboardEvent(key="Power", eventType=KeyboardEvent.keyup)
        )

    await emulator_controller.streamInputEvent(long_press_power_button_down())
    yield
    await emulator_controller.streamInputEvent(long_press_power_button_up())


@pytest.fixture
async def is_power_menu_open(avd):
    """Provides a coroutine to check if the power menu is open.

    Args:
        avd: The emulator instance.

    Returns:
        A coroutine that returns True if the power menu is open, False otherwise.
    """

    async def _is_power_menu_open():
        window_dump = await get_window_dump(avd)
        return 'text="Power off"' in window_dump

    return _is_power_menu_open


@pytest.mark.sanity
@pytest.mark.async_timeout(20)
@pytest.mark.flaky(reruns=2)
@pytest.mark.dependency()
async def test_can_open_power_menu(open_power_menu, is_power_menu_open):
    """Verifies that the power menu can be opened.

    Note: Bringing up the power menu is a bit flaky.
    """
    assert await eventually(is_power_menu_open), "Couldn't open the Power options menu."


@pytest.mark.sanity
@pytest.mark.async_timeout(60)
async def test_close_emulator_with_power_menu(avd, emulator_is_off):
    """Verifies closing the emulator via the power menu."""
    assert await click_button(
        avd, text="Power off"
    ), "Couldn't click the Power off button."

    assert await eventually(
        emulator_is_off, timeout=20
    ), "The emulator was not shut down after selecting power off from the menu."


@pytest.mark.sanity
@pytest.mark.async_timeout(60)
async def test_close_emulator_with_console_kill(telnet, emulator_is_off):
    """Verifies closing the emulator via the 'kill' command in the console."""
    await telnet.send("kill")
    assert await eventually(
        emulator_is_off, timeout=20
    ), "The emulator was not shut down after the kill command was send over the telnet console"


@pytest.mark.skipos("win", "reason: b/392949854 killing pytest")
@pytest.mark.sanity
@pytest.mark.async_timeout(60)
async def test_close_emulator_with_ctrl_c(avd, emulator_is_off):
    """Verifies that sending Ctrl+C shuts down the emulator."""
    CTRL_C = signal.SIGINT if platform.system() != "Windows" else signal.CTRL_C_EVENT
    avd.cmd.process.send_signal(CTRL_C)
    assert await eventually(
        emulator_is_off, timeout=20
    ), "The emulator was not shut down after the CTRL-C event was sent."
