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
import time
import pytest
from google.protobuf import empty_pb2
from aemu.proto.emulator_controller_pb2 import (
    ImageFormat,
    DisplayMode,
    DisplayModeValue,
)
from PIL import Image

_EMPTY_ = empty_pb2.Empty()

avd_config = {
    "api": "33",
    "tag.id": "google_apis",
    "hw.device.name": "resizable",
    "hw.resizable.configs": "phone-0-1080-2340-420, foldable-1-1768-2208-420, tablet-2-1920-1200-24 0",
    "skin.name": "1080x2340",
    "skin.path": "no_skin",
}


def verify_that_images_are_equal(width, height, img, left, right, top, bottom):
    actual_img = Image.frombytes("RGB", (width, height), img.image)
    found_first = False
    expected_left = 0
    expected_right = 0
    expected_top = 0
    expected_bottom = 0
    for h in range(height):
        for w in range(width):
            if actual_img.getpixel((w, h)) == (255, 0, 0):
                if not found_first:
                    found_first = True
                    expected_left = w
                    expected_top = h
                else:
                    expected_right = w
                    expected_bottom = h
    assert left == expected_left
    assert right == expected_right
    assert top == expected_top
    assert bottom == expected_bottom


@pytest.mark.skip(reason="b/254131882, we need to really figure out why this fails.")
@pytest.mark.parametrize(
    "width, height, mode, left, right, top, bottom",
    [
        (1080, 2340, DisplayModeValue.PHONE, 882, 1079, 0, 227),
        (1768, 2208, DisplayModeValue.FOLDABLE, 1191, 1767, 0, 204),
        (1920, 1200, DisplayModeValue.TABLET, 1127, 1514, 0, 110),
    ],
)
def test_resizable(
    animation_app, emulator_controller, width, height, mode, left, right, top, bottom
):

    """Run Animation app. Take a screenshot. Locate the four edges of the red square,
    and make sure they are at the proper position of the display"""
    emulator_controller.setDisplayMode(
        DisplayMode(
            value=mode,
        )
    )
    image = emulator_controller.getScreenshot(
        ImageFormat(
            format=ImageFormat.RGB888,
        )
    )
    assert emulator_controller.getDisplayMode(_EMPTY_).value == mode
    assert image.format.width == width
    assert image.format.height == height
    verify_that_images_are_equal(
        image.format.width, image.format.height, image, left, right, top, bottom
    )
