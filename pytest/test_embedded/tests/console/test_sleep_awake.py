# Copyright 2023 The Android Open Source Project
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
import sys

import pytest
from aemu.proto.emulator_controller_pb2 import ImageFormat

from emu.timing import eventually


def wake_up(adb_shell):
    """
    Sends a wake-up command to the connected Android device using ADB. The device is woken
    up by sending the KEYCODE_WAKEUP (https://developer.android.com/reference/android/view/KeyEvent#KEYCODE_WAKEUP)

    Args:
        adb (callable): A function or method that executes ADB commands.

    Raises:
        AssertionError: If the ADB command output contains the error message "adb: error".

    Returns:
        None
    """
    assert not "adb: error" in adb_shell("input keyevent KEYCODE_WAKEUP")


def power_down(adb_shell):
    """
    Sends a power-down command to the connected Android device using ADB. The device is powered
    down by sending the POWER key event (https://developer.android.com/reference/android/view/KeyEvent#KEYCODE_POWER).

    Args:
        adb (callable): A function or method that executes ADB commands.

    Raises:
        AssertionError: If the ADB command output contains the error message "adb: error".

    Returns:
        None
    """
    assert not "adb: error" in adb_shell("input keyevent POWER")


@pytest.fixture
def emulator_on(adb_shell):
    """
    Fixture that ensures the connected Android device is powered on before running tests.

    Args:
        adb (callable): The adb fixture that executes ADB commands.

    Returns:
        None
    """
    wake_up(adb_shell)


@pytest.fixture
def emulator_off(adb_shell):
    """
    Fixture that ensures the connected Android device is powered off before running tests.

    Args:
        adb (callable): The adb fixture that executes ADB commands.

    Returns:
        None
    """
    power_down(adb_shell)


@pytest.mark.adb
@pytest.mark.timeout(timeout=20, func_only=True)
@pytest.mark.flaky(reruns=3, reruns_delay=5)
@pytest.mark.skipif(sys.platform == "win32", reason="b/288441746")
def test_power_down_sleeps_the_device(adb_shell, emulator_on):
    """Test case to verify that sending the power-down command to an awake device will put the device to sleep."""

    def is_asleep():
        return "Asleep" in adb_shell("dumpsys power | grep mWakefulness")

    power_down(adb_shell)
    assert eventually(is_asleep)


@pytest.mark.adb
@pytest.mark.timeout(timeout=20, func_only=True)
@pytest.mark.flaky(reruns=3, reruns_delay=5)
def test_wake_up_wakes_the_device(adb_shell, emulator_off):
    """Test case to verify that sending the wake-up command to a sleeping device will wake the device."""

    def is_awake():
        return "Awake" in adb_shell("dumpsys power | grep mWakefulness")

    wake_up(adb_shell)
    assert eventually(is_awake)


@pytest.mark.e2e
@pytest.mark.adb
@pytest.mark.timeout(timeout=20, func_only=True)
@pytest.mark.flaky(reruns=3, reruns_delay=5)
def test_power_down_turns_off_the_screen(emulator_off, get_screenshot):
    """Test case to verify that a powered-down device has a black screen.

    An e2e adb test where emulator is turned off using adb command and then check is made to verify if there is a
    black screen on the emulator.
    """

    def emulator_screen_is_black():
        """Verify if the emulator screen is black.

        Returns:
            bool: True if the screen is black, False otherwise.
        """
        __doc__, img = get_screenshot(ImageFormat())
        for x in range(img.width):
            for y in range(img.height):
                co = (x, y)
                pixel = img.getpixel(co)
                if pixel != (0, 0, 0, 255):
                    # The screen is not black.
                    return False
        return True

    # We eventually should see a black screen..
    assert eventually(emulator_screen_is_black), "The screen did not become black!"
