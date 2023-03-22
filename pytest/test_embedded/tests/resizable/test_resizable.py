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
from emu.timing import wait_until

_EMPTY_ = empty_pb2.Empty()

avd_config = {
    "api": "33",
    "tag.id": "google_apis",
    "hw.device.name": "resizable",
    "hw.resizable.configs": "phone-0-1080-2340-420, foldable-1-1768-2208-420, tablet-2-1920-1200-240, desktop-3-1920-1080-160",
    "skin.name": "1080x2340",
    "skin.path": "no_skin",
}


@pytest.mark.parametrize(
    "width, height, mode",
    [
        (1080, 2340, DisplayModeValue.PHONE),
        (1768, 2208, DisplayModeValue.FOLDABLE),
        (1920, 1200, DisplayModeValue.TABLET),
        (1920, 1080, DisplayModeValue.DESKTOP),
    ],
)
@pytest.mark.timeout(timeout=10, func_only=True)
@pytest.mark.flaky(reruns=2, reruns_delay=2)
@pytest.mark.skip(reason="Width doesn't match for display mode desktop on screenshot b/274493769")
def test_resizable_changes_resolution(emulator_controller, width, height, mode):

    emulator_controller.setDisplayMode(
        DisplayMode(
            value=mode,
        )
    )

    # Eventually the currentMode is equal to the one we have set.
    # If this is broken the test will timeout
    assert wait_until(lambda: emulator_controller.getDisplayMode(_EMPTY_).value == mode)

    image = emulator_controller.getScreenshot(
        ImageFormat(
            format=ImageFormat.RGB888,
        )
    )

    # prevent crazy logging in case of assert failures
    format = image.format
    byte_count = len(image.image)

    assert format.width == width
    assert format.height == height
    assert byte_count == width * height * 3
