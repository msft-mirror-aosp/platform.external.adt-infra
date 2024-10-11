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
import pytest
from aemu.proto.emulator_controller_pb2 import (
    DisplayMode,
    DisplayModeValue,
    ImageFormat,
)
from google.protobuf import empty_pb2

from emu.timing import eventually

_EMPTY_ = empty_pb2.Empty()

avd_config = {
    "api": "33",
    "tag.id": "google_apis",
    "hw.device.name": "resizable",
    "hw.resizable.configs": "phone-0-1080-2340-420, foldable-1-1768-2208-420, tablet-2-1920-1200-240, desktop-3-1920-1080-160",
    "skin.name": "1080x2340",
    "skin.path": "no_skin",
}


async def set_display_mode(emulator_controller, mode, timeout=5):
    await emulator_controller.setDisplayMode(
        DisplayMode(
            value=mode,
        )
    )

    async def mode_is_set():
        currentMode = await emulator_controller.getDisplayMode(_EMPTY_)
        return currentMode.value == mode

    assert await eventually(mode_is_set, timeout=timeout)
    return mode


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
@pytest.mark.flaky(reruns=0)
@pytest.mark.sanity
@pytest.mark.skipos("all", "reason: b/309463427")
async def test_resizable_changes_resolution(
    animation_app, emulator_controller, width, height, mode, get_screenshot
):
    await set_display_mode(mode)

    async def screenshot_is_sized_properly():
        image, _ = await get_screenshot(
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
    assert eventually(screenshot_is_sized_properly)


@pytest.mark.resizable
@pytest.mark.parametrize(
    "fmt, bpp",
    [
        (ImageFormat.RGBA8888, 4),
        (ImageFormat.RGB888, 3),
    ],
)
async def test_resizable_observable_from_streaming(
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
    updated = await set_display_mode(emulator_controller, mode)
    assert updated == mode

    # Wait until we observe the expected dimension in the stream of screenshots
    # If we see it we move to the next dimension we are going to check
    # Eventually we run out dimensions, resulting in a StopIteration
    # If things are broken we will timeout.
    with pytest.raises(StopIteration):
        stream = stream_screenshot(ImageFormat(format=fmt))
        async for image in stream:
            if image.format.width == w and image.format.height == h:
                pixel_count = len(image.image)
                assert pixel_count == w * h * bpp

                # Transition to the next.
                w, h, mode = next(available_dimensions)
                updated = await set_display_mode(emulator_controller, mode)
                assert updated == mode


@pytest.mark.resizable
@pytest.mark.parametrize(
    "fmt, bpp",
    [
        (ImageFormat.RGBA8888, 4),
        (ImageFormat.RGB888, 3),
    ],
)
async def test_resizable_observable_from_streaming(
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
    updated = await set_display_mode(emulator_controller, mode)

    # Wait until we observe the expected dimension in the stream of screenshots
    # If we see it we move to the next dimension we are going to check
    # Eventually we run out dimensions, resulting in a StopIteration
    # If things are broken we will timeout.
    with pytest.raises(StopIteration):
        stream = stream_screenshot(ImageFormat(format=fmt))
        async for image in stream:
            if image.format.width == w and image.format.height == h:
                pixel_count = len(image.image)
                assert pixel_count == w * h * bpp

                # Transition to the next.
                w, h, mode = next(available_dimensions)

                # Eventually the currentMode is equal to the one we have set.
                # If this is broken the test will timeout
                updated = await set_display_mode(emulator_controller, mode)
                assert updated == mode
