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
import asyncio
import logging
import time

import pytest
from aemu.proto.emulator_controller_pb2 import (
    DisplayMode,
    DisplayModeValue,
    ImageFormat,
    ParameterValue,
    PhysicalModelValue,
)
from google.protobuf import empty_pb2

from emu.timing import eventually, wait_until

_EMPTY_ = empty_pb2.Empty()


async def set_device_hinge_angle(emu, angle):
    """Change the device's hinge angle"""
    await emu.setPhysicalModel(
        PhysicalModelValue(
            target=PhysicalModelValue.HINGE_ANGLE0,
            value=ParameterValue(data=[angle, 0.0, 0.0]),
        )
    )


async def set_display_mode(emulator_controller, mode, timeout=5):
    await emulator_controller.setDisplayMode(
        DisplayMode(
            value=mode,
        )
    )

    # Eventually the currentMode is equal to the one we have set.
    currentMode = await emulator_controller.getDisplayMode(_EMPTY_)
    logging.info("set_display_mode: currentMode:%s == %s", currentMode.value, mode)
    timeout = time.time() + timeout
    while currentMode.value != mode and time.time() < timeout:
        await asyncio.sleep(0.1)
        currentMode = await emulator_controller.getDisplayMode(_EMPTY_)
        logging.info("set_display_mode: currentMode:%s == %s", currentMode.value, mode)

    return currentMode.value


@pytest.mark.newresizable
@pytest.mark.parametrize(
    "width, height, mode",
    [
        (1080, 2340, DisplayModeValue.PHONE),
        (1768, 2208, DisplayModeValue.FOLDABLE),
        (1920, 1200, DisplayModeValue.TABLET),
        (1920, 1080, DisplayModeValue.DESKTOP),
    ],
)
@pytest.mark.timeout_win(timeout=60)
@pytest.mark.flaky(reruns=2, reruns_delay=2)
@pytest.mark.sanity
# @pytest.mark.skipos("all", "reason: b/309463427")
async def test_new_resizable_changes_resolution(
    avd, animation_app, emulator_controller, width, height, mode, get_screenshot
):
    if avd.api_level() < 34:
        pytest.skip(reason="Requires api level >=34!")

    await emulator_controller.setDisplayMode(DisplayMode(value=mode))

    async def display_is_set_to_mode():
        updated = await emulator_controller.getDisplayMode(_EMPTY_)
        logging.info("display_is_set_to_mode: %s == %s", updated.value, mode)
        return updated.value == mode

    # Eventually the currentMode is equal to the one we have set.
    # If this is broken the test will timeout
    assert await wait_until(display_is_set_to_mode, timeout=5)

    async def screenshot_is_sized_properly():
        image, _ = await get_screenshot(
            ImageFormat(
                format=ImageFormat.RGB888,
            )
        )

        format = image.format
        logging.info(
            "screenshot_is_sized_properly: %sx%s = %sx%s",
            format.width,
            format.height,
            width,
            height,
        )
        byte_count = len(image.image)

        return (
            format.width == width
            and format.height == height
            and byte_count == width * height * 3
        )

    # Eventually we should receive a screenshot that has the expected size.
    assert await wait_until(screenshot_is_sized_properly, timeout=5)


@pytest.mark.newresizable
@pytest.mark.parametrize(
    "fmt, bpp",
    [
        (ImageFormat.RGBA8888, 4),
        (ImageFormat.RGB888, 3),
    ],
)
async def test_new_resizable_observable_from_streaming(
    avd, at_home, animation_app, emulator_controller, stream_screenshot, fmt, bpp
):
    if avd.api_level() < 34:
        pytest.skip(reason="Requires api level >=34!")

    available_dimensions = iter(
        [
            (1080, 2340, DisplayModeValue.PHONE),
            (2208, 1840, DisplayModeValue.FOLDABLE),
            (1920, 1200, DisplayModeValue.TABLET),
            (1920, 1080, DisplayModeValue.DESKTOP),
        ]
    )

    # Start with moving to the intial dimension
    w, h, mode = next(available_dimensions)
    assert await set_display_mode(emulator_controller, mode) == mode

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
                assert await set_display_mode(emulator_controller, mode) == mode


@pytest.mark.newresizable
@pytest.mark.parametrize(
    "fmt, bpp",
    [
        (ImageFormat.RGBA8888, 4),
        (ImageFormat.RGB888, 3),
    ],
)
async def test_new_resizable_folding_observable_from_streaming(
    avd, animation_app, emulator_controller, stream_screenshot, fmt, bpp
):
    if avd.api_level() < 34:
        pytest.skip(reason="Requires api level >=34!")

    available_dimensions = iter(
        [
            (1080, 2340, DisplayModeValue.PHONE),
            (2208, 1840, DisplayModeValue.FOLDABLE),
            (1920, 1200, DisplayModeValue.TABLET),
            (1920, 1080, DisplayModeValue.DESKTOP),
        ]
    )

    # start with unfold
    await set_device_hinge_angle(emulator_controller, 180)
    await asyncio.sleep(1)

    foldedw = 1080
    foldedh = 2092
    # Start with moving to the intial dimension
    w, h, mode = next(available_dimensions)
    updated = await set_display_mode(emulator_controller, mode)
    assert updated == mode
    await asyncio.sleep(1)

    # Transition to the next.
    w, h, mode = next(available_dimensions)
    updated = await set_display_mode(emulator_controller, mode)
    assert updated == DisplayModeValue.FOLDABLE
    await asyncio.sleep(1)

    # Now fold it
    await set_device_hinge_angle(emulator_controller, 0)
    await asyncio.sleep(1)

    # Wait until we observe the expected dimension in the stream of screenshots
    def image_is_properly_sized(image):
        logging.info(
            "image_is_properly_sized %sx%s == %sx%s",
            image.format.width,
            image.format.height,
            foldedw,
            foldedh,
        )
        return (
            image.format.width == foldedw
            and image.format.height == foldedh
            and len(image.image) == foldedw * foldedh * bpp
        )

    stream = stream_screenshot(ImageFormat(format=fmt))
    assert await eventually(image_is_properly_sized, stream)
