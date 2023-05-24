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
import time
from aemu.proto.emulator_controller_pb2 import ImageFormat

from PIL import Image
from tests.test_utils import proto_to_pillow


def adb_test_sleep_awake(avd):
    """Verify that the device can be put to sleep and waked up successfully.

    Args:
      avd: The emulator

    Returns:
      True if the device was successfully put to sleep and waked up, else False.
    """

    return not "adb: error" in avd.adb.run(["shell", "input", "keyevent", "POWER"])


def adb_verify_sleep_awake_state(img: Image):
    """Verify the black screen on  the emulator.

    Args:
        img (Image): A PIL image we are inspecting
    """
    for x in range(img.width):
        for y in range(img.height):
            co = (x, y)
            pixel = img.getpixel(co)
            if pixel != (0, 0, 0, 255):
                # The screen is not black.
                pytest.fail("Screen is not black.")


@pytest.mark.adb
@pytest.mark.flaky(reruns=3, reruns_delay=5)
def test_adb_sleep_awake(emulator_controller, avd):
    """Test ADB sleep/wake commands"""

    success = adb_test_sleep_awake(avd)
    time.sleep(2)
    assert success, "ADB Sleep failed"

    image = emulator_controller.getScreenshot(ImageFormat())
    pillow_img = proto_to_pillow(image)
    adb_verify_sleep_awake_state(pillow_img)

    success = adb_test_sleep_awake(avd)
    time.sleep(1)
    assert success, "ADB Wake up failed"
