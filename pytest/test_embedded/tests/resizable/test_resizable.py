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
import pkg_resources

import os
import pytest
from google.protobuf import empty_pb2
from aemu.proto.emulator_controller_pb2 import (
    ImageFormat,
    DisplayMode,
    DisplayModeValue,
)
from PIL import Image
_EMPTY_ = empty_pb2.Empty()
_DIFF_MAX_ = 0.01

avd_config = {
    "api": "33",
    "tag.id": "google_apis",
    "hw.device.name": "resizable",
    "hw.resizable.configs": "phone-0-1080-2340-420, foldable-1-1768-2208-420, tablet-2-1920-1200-240, desktop-3-1920-1080-160",
    "skin.name": "1080x2340",
    "skin.path": "no_skin",
}

def set_device_display_mode(emu, mode):
    """Change the device's display mode"""
    emu.setDisplayMode(
        DisplayMode(
            value=mode,
        )
    )
    time.sleep(5)

def img_compare(width, height, img, expected_img_file):
    current_path = os.path.dirname(os.path.realpath(__file__))
    filename = os.path.join(current_path, expected_img_file)
    expected_img = Image.open(filename).convert('RGB')
    actual_img = Image.frombytes(
        "RGB", (width, height), img.image
    )

    different_pixels = 0
    for w in range(width):
      for h in range(height):
        if actual_img.getpixel((w, h)) != expected_img.getpixel((w, h)):
          different_pixels+=1
    return different_pixels/(width*height)

@pytest.mark.parametrize("w,h,mode,expected_image",
                         [(1080, 2340, DisplayModeValue.PHONE, "phone.png"),
                          (1768, 2208, DisplayModeValue.FOLDABLE, "foldable.png"),
                          (1920, 1200, DisplayModeValue.TABLET, "tablet.png"),
                          (1920, 1080, DisplayModeValue.DESKTOP, "desktop.png")])
def test_resizable(emulator_controller, w, h, mode, expected_image):
    """test PHONE mode"""
    set_device_display_mode(emulator_controller, mode)
    image = emulator_controller.getScreenshot(
        ImageFormat(
            format=ImageFormat.RGB888,
        )
    )
    assert emulator_controller.getDisplayMode(_EMPTY_).value == mode
    assert image.format.width == w
    assert image.format.height == h
    diff = img_compare(image.format.width, image.format.height, image, expected_image)
    assert diff < _DIFF_MAX_
