# Copyright 2021 The Android Open Source Project
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

from io import BytesIO
import time

import re
import pytest
from aemu.proto.emulator_controller_pb2 import (
    ImageFormat,
    ParameterValue,
    PhysicalModelValue,
    KeyboardEvent,
)
from PIL import Image
from tests.test_utils import wait_for_regex


def pause_animation_app(emu):
    """Pauses the animation app."""

    def _wait_for_pause(stream, max_wait):
        """Waits until the timing entry has been written by our app."""
        PAUSE_RE = re.compile(r".*Pausing animation.")
        timeout = time.time() + max_wait
        for line in iter(stream.get, None):
            m = PAUSE_RE.match(line)
            if timeout < time.time():
                return False

            if m:
                return True

    with emu.adb_stream(["logcat", "-s", "aemu"]) as stream:
        emu.get_emulator_controller().sendKey(
            KeyboardEvent(key="P", eventType=KeyboardEvent.keypress)
        )
        return wait_for_regex(stream, r".*Pausing animation.", 5)


def rotate_device(emu, angle):
    """Rotate the device to the given angle."""
    emu.setPhysicalModel(
        PhysicalModelValue(
            target=PhysicalModelValue.ROTATION,
            value=ParameterValue(data=[0, 0, angle]),
        )
    )
    time.sleep(0.2)


EMU_TO_PIL_IMAGE_FORMATS = {
    ImageFormat.RGB888: "RGB",
    ImageFormat.RGBA8888: "RGBA",
    ImageFormat.PNG: "PNG",
}


@pytest.mark.parametrize("w,h", [(0, 0), (320, 200), (1920, 1080)])
def test_screenshot_all_formats_are_equal(animation_app, w, h):
    """Make sure that all the screenshots are exactly the same, regardless of format.

    This is done by launching the animation app, and pausing it. This should make sure
    we always have the same frame displayed on the device.
    """
    assert pause_animation_app(pytest.emulator)
    emu = pytest.emulator.get_emulator_controller()
    last_pixels = None
    for fmt in [ImageFormat.RGBA8888, ImageFormat.RGB888, ImageFormat.PNG]:
        image = emu.getScreenshot(ImageFormat(format=fmt, width=w, height=h))

        # Load and convert the image using pillow
        if image.format.format == ImageFormat.PNG:
            pillow_image = Image.open(BytesIO(image.image))
        else:
            pillow_image = Image.frombytes(
                EMU_TO_PIL_IMAGE_FORMATS[fmt],
                (image.format.width, image.format.height),
                image.image,
            )

        # a == b, b == c --> a == c, so we can just compare the last known image
        # to the current one.
        pixels = list(pillow_image.convert("RGB").getdata())
        assert last_pixels == None or last_pixels == pixels
        last_pixels == pixels


@pytest.mark.parametrize(
    "fmt,bpp",
    [(ImageFormat.RGB888, 3), (ImageFormat.RGBA8888, 4)],
)
@pytest.mark.parametrize("degrees", [0, 90])
def test_screenshot_exact_amount_of_pixels(at_home, fmt, bpp, degrees):
    """Tests that the screenshot API delivers exactly the right amount of pixels.

    The number of pixels is determined by the bytes per pixel * w * h, irrespective of rotation.
    """
    emu = pytest.emulator.get_emulator_controller()
    rotate_device(emu, degrees)

    image = emu.getScreenshot(
        ImageFormat(
            format=fmt,
        )
    )
    assert len(image.image) == (bpp * image.format.width * image.format.height)
