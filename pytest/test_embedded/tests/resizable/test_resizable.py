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
from aemu.proto.emulator_controller_pb2 import (
    DisplayMode,
    DisplayModeValue,
    ImageFormat,
)
from google.protobuf import empty_pb2

from emu.timing import wait_until
from tests.test_utils import StreamingCall

_EMPTY_ = empty_pb2.Empty()

avd_config = {
    "api": "33",
    "tag.id": "google_apis",
    "hw.device.name": "resizable",
    "hw.resizable.configs": "phone-0-1080-2340-420, foldable-1-1768-2208-420, tablet-2-1920-1200-240, desktop-3-1920-1080-160",
    "skin.name": "1080x2340",
    "skin.path": "no_skin",
}


def set_display_mode(emulator_controller, mode, timeout=5):
    emulator_controller.setDisplayMode(
        DisplayMode(
            value=mode,
        )
    )

    # Eventually the currentMode is equal to the one we have set.
    currentMode = emulator_controller.getDisplayMode(_EMPTY_).value
    timeout = time.time() + timeout
    while currentMode != mode and time.time() < timeout:
        time.sleep(0.1)
        currentMode = emulator_controller.getDisplayMode(_EMPTY_).value

    return emulator_controller.getDisplayMode(_EMPTY_).value


@pytest.mark.resizable
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
@pytest.mark.timeout_win(timeout=60)
@pytest.mark.flaky(reruns=2, reruns_delay=2)
@pytest.mark.sanity
@pytest.mark.skipos("all", "reason: b/309463427")
def test_resizable_changes_resolution(
    animation_app, emulator_controller, width, height, mode, get_screenshot
):
    emulator_controller.setDisplayMode(DisplayMode(value=mode))
    # Eventually the currentMode is equal to the one we have set.
    # If this is broken the test will timeout
    assert wait_until(lambda: emulator_controller.getDisplayMode(_EMPTY_).value == mode)

    def screenshot_is_sized_properly():
        image, _ = get_screenshot(
            ImageFormat(
                format=ImageFormat.RGB888,
            )
        )

        format = image.format
        byte_count = len(image.image)

        return (
            format.width == width
            and format.height == height
            and byte_count == width * height * 3
        )

    # Eventually we should receive a screenshot that has the expected size.
    assert wait_until(screenshot_is_sized_properly)


@pytest.mark.timeout(timeout=60, func_only=True)
@pytest.mark.parametrize(
    "fmt, bpp",
    [
        (ImageFormat.RGBA8888, 4),
        (ImageFormat.RGB888, 3),
    ],
)
def test_resizable_observable_from_streaming(
    emulator_controller, stream_screenshot, fmt, bpp
):
    available_dimensions = iter(
        [
            (1080, 2340, DisplayModeValue.PHONE),
            (1768, 2208, DisplayModeValue.FOLDABLE),
            (1920, 1200, DisplayModeValue.TABLET),
            (1920, 1080, DisplayModeValue.DESKTOP),
        ]
    )

    # Start with moving to the intial dimension
    w, h, mode = next(available_dimensions)
    assert set_display_mode(emulator_controller, mode) == mode

    # Wait until we observe the expected dimension in the stream of screenshots
    # If we see it we move to the next dimension we are going to check
    # Eventually we run out dimensions, resulting in a StopIteration
    # If things are broken we will timeout.
    with pytest.raises(StopIteration):
        with stream_screenshot(ImageFormat(format=fmt)) as stream:
            for image in stream:
                if image.format.width == w and image.format.height == h:
                    pixel_count = len(image.image)
                    assert pixel_count == w * h * bpp

                    # Transition to the next.
                    w, h, mode = next(available_dimensions)
                    assert set_display_mode(emulator_controller, mode) == mode


@pytest.mark.timeout(timeout=60, func_only=True)
@pytest.mark.parametrize(
    "fmt, bpp",
    [
        (ImageFormat.RGBA8888, 4),
        (ImageFormat.RGB888, 3),
    ],
)
def test_resizable_observable_from_streaming(
    emulator_controller, stream_screenshot, fmt, bpp
):
    available_dimensions = iter(
        [
            (1080, 2340, DisplayModeValue.PHONE),
            (1768, 2208, DisplayModeValue.FOLDABLE),
            (1920, 1200, DisplayModeValue.TABLET),
            (1920, 1080, DisplayModeValue.DESKTOP),
        ]
    )

    # Start with moving to the intial dimension
    w, h, mode = next(available_dimensions)
    emulator_controller.setDisplayMode(DisplayMode(value=mode))
    # Eventually the currentMode is equal to the one we have set.
    # If this is broken the test will timeout
    assert wait_until(lambda: emulator_controller.getDisplayMode(_EMPTY_).value == mode)

    # Wait until we observe the expected dimension in the stream of screenshots
    # If we see it we move to the next dimension we are going to check
    # Eventually we run out dimensions, resulting in a StopIteration
    # If things are broken we will timeout.
    with pytest.raises(StopIteration):
        with stream_screenshot(ImageFormat(format=fmt)) as stream:
            for image in stream:
                if image.format.width == w and image.format.height == h:
                    pixel_count = len(image.image)
                    assert pixel_count == w * h * bpp

                    # Transition to the next.
                    w, h, mode = next(available_dimensions)

                    emulator_controller.setDisplayMode(DisplayMode(value=mode))
                    # Eventually the currentMode is equal to the one we have set.
                    # If this is broken the test will timeout
                    assert wait_until(
                        lambda: emulator_controller.getDisplayMode(_EMPTY_).value
                        == mode
                    )
