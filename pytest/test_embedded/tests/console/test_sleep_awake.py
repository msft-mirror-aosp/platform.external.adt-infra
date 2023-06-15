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

import pytest
from aemu.proto.emulator_controller_pb2 import Image, ImageFormat

from emu.timing import eventually
from tests.test_utils import StreamingCall, proto_to_pillow


def wake_up(adb):
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
    assert not "adb: error" in adb(["shell", "input", "keyevent", "KEYCODE_WAKEUP"])


def power_down(adb):
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
    assert not "adb: error" in adb(["shell", "input", "keyevent", "POWER"])


import pytest


@pytest.fixture
def on(adb):
    """
    Fixture that ensures the connected Android device is powered on before running tests.

    Args:
        adb (callable): The adb fixture that executes ADB commands.

    Returns:
        None
    """
    wake_up(adb)


@pytest.fixture
def off(adb):
    """
    Fixture that ensures the connected Android device is powered off before running tests.

    Args:
        adb (callable): The adb fixture that executes ADB commands.

    Returns:
        None
    """
    power_down(adb)


@pytest.mark.adb
@pytest.mark.timeout(timeout=20, func_only=True)
@pytest.mark.flaky(reruns=3, reruns_delay=5)
def test_power_down_sleeps_the_device(adb, on):
    """Test case to verify that sending the power-down command to an awake device will put the device to sleep."""

    def is_asleep():
        return "Asleep" in adb(
            ["shell", "dumpsys power | grep mWakefulness"]
        )

    power_down(adb)
    assert eventually(is_asleep)


@pytest.mark.adb
@pytest.mark.timeout(timeout=20, func_only=True)
@pytest.mark.flaky(reruns=3, reruns_delay=5)
def test_wake_up_wakes_the_device(adb, off):
    """Test case to verify that sending the wake-up command to a sleeping device will wake the device."""

    def is_awake():
        return "Awake" in adb(
            ["shell", "dumpsys power | grep mWakefulness"]
        )

    wake_up(adb)
    assert eventually(is_awake)


@pytest.mark.e2e
@pytest.mark.adb
@pytest.mark.timeout(timeout=20, func_only=True)
@pytest.mark.flaky(reruns=3, reruns_delay=5)
def test_power_down_turns_off_the_screen(emulator_controller, off):
    """Test case to verify that a powered-down device has a black screen.

    An e2e adb test where emulator is turned off using adb command and then check is made to verify if there is a
    black screen on the emulator.
    """

    def is_a_black_image(image: Image):
        """Verify if the emulator screen is black.

        Args:
            img (Image): An image received from the emulator.

        Returns:
            bool: True if the screen is black, False otherwise.
        """
        img = proto_to_pillow(image)
        for x in range(img.width):
            for y in range(img.height):
                co = (x, y)
                pixel = img.getpixel(co)
                if pixel != (0, 0, 0, 255):
                    # The screen is not black.
                    return False
        return True

    # We eventually should see a black screen..
    images = emulator_controller.streamScreenshot(ImageFormat())
    with StreamingCall(images) as stream:
        assert eventually(is_a_black_image, stream), "The screen did not become black!"
