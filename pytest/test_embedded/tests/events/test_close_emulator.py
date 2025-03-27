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
import platform
import signal
import pytest

from emu.timing import eventually
from tests.test_utils import click_button


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
async def open_power_menu(avd, ad_ui):
    """Open the power menu in the emulator.

    Launches the power menu from the Quick Settings panel.
    """
    await avd.adb.shell("cmd statusbar expand-notifications")
    assert ad_ui(res="com.android.systemui:id/notification_panel").wait.exists()

    await avd.adb.shell("cmd statusbar expand-settings")
    pm_button = ad_ui(res="com.android.systemui:id/pm_lite")

    assert pm_button.wait.exists()
    assert pm_button.click.wait()

@pytest.fixture
async def is_power_menu_open(ad_ui):
    """Provides a coroutine to check if the power menu is open.

    Args:
        avd: The emulator instance.

    Returns:
        A coroutine that returns True if the power menu is open, False otherwise.
    """

    async def _is_power_menu_open():
        return ad_ui(text="Power off").exists

    return _is_power_menu_open


@pytest.mark.sanity
@pytest.mark.async_timeout(30)
@pytest.mark.dependency()
async def test_can_open_power_menu(open_power_menu, is_power_menu_open):
    """Verifies that the power menu can be opened.

    Note: Bringing up the power menu is a bit flaky.
    """
    assert await eventually(is_power_menu_open), "Couldn't open the Power options menu."


@pytest.mark.sanity
@pytest.mark.async_timeout(60)
async def test_close_emulator_with_power_menu(avd, emulator_is_off, ad_ui):
    """Verifies closing the emulator via the power menu."""
    assert ad_ui(text="Power off").click.wait()
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
