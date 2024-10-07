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
import re
import time
from collections import namedtuple
from functools import partial

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

# Define a namedtuple class for the device specifications
DeviceSpec = namedtuple("DeviceSpec", ["formfactor", "mode", "width", "height", "dpi"])
_EMPTY_ = empty_pb2.Empty()


async def set_device_hinge_angle(emu, angle):
    """Change the device's hinge angle"""
    await emu.setPhysicalModel(
        PhysicalModelValue(
            target=PhysicalModelValue.HINGE_ANGLE0,
            value=ParameterValue(data=[angle, 0.0, 0.0]),
        )
    )


@pytest.fixture
async def supported_resizable_resolutions(avd):
    api_level = await avd.api_level()
    if api_level < 34 or "hw.resizable.configs" not in avd.hardware:
        return []

    resolutions = []
    resize = re.compile(r"(phone|foldable|tablet|desktop)-(\d+)-(\d+)-(\d+)-(\d+)")
    cfg = avd.hardware["hw.resizable.configs"]

    for match in resize.findall(cfg):
        resolutions.append(
            DeviceSpec(
                match[0], int(match[1]), int(match[2]), int(match[3]), int(match[4])
            )
        )
    logging.info("Supported resolutions: %s", resolutions)
    return resolutions


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
        (2208, 1840, DisplayModeValue.FOLDABLE),
        (1920, 1200, DisplayModeValue.TABLET),
        (1920, 1080, DisplayModeValue.DESKTOP),
    ],
)
@pytest.mark.flaky
@pytest.mark.sanity
@pytest.mark.embedded_newresizable
async def test_new_resizable_changes_resolution(
    supported_resizable_resolutions,
    avd,
    animation_app,
    emulator_controller,
    width,
    height,
    mode,
    get_screenshot,
):
    api_level = await avd.api_level()
    if api_level < 34:
        pytest.skip(reason="Requires api level >=34!")

    if not any(
        [
            (d.width == width and d.height == height)
            for d in supported_resizable_resolutions
        ]
    ):

        pytest.skip(
            reason=f"Display mode {width}x{height} not available in {supported_resizable_resolutions}"
        )

    async def display_is_set_to_mode():
        updated = await emulator_controller.getDisplayMode(_EMPTY_)
        logging.info("display_is_set_to_mode: %s == %s", updated.value, mode)
        return updated.value == mode

    # Eventually the currentMode is equal to the one we have set.
    # If this is broken the test will timeout
    await emulator_controller.setDisplayMode(DisplayMode(value=mode))
    await asyncio.sleep(3)
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
@pytest.mark.flaky
async def test_new_resizable_observable_from_streaming(
    avd,
    supported_resizable_resolutions,
    at_home,
    animation_app,
    emulator_controller,
    stream_screenshot,
    fmt,
    bpp,
):
    api_level = await avd.api_level()
    if api_level < 34:
        pytest.skip(reason="Requires api level >=34!")

    available_dimensions = iter(supported_resizable_resolutions)

    # Start with moving to the intial dimension
    spec = next(available_dimensions)
    assert await set_display_mode(emulator_controller, spec.mode) == spec.mode
    await asyncio.sleep(3)

    # Wait until we observe the expected dimension in the stream of screenshots
    # If we see it we move to the next dimension we are going to check
    # Eventually we run out dimensions, resulting in a StopIteration
    # If things are broken we will timeout.
    with pytest.raises(StopIteration):
        stream = stream_screenshot(ImageFormat(format=fmt))
        async for image in stream:
            if image.format.width == spec.width and image.format.height == spec.height:
                pixel_count = len(image.image)
                assert pixel_count == spec.width * spec.height * bpp

                # Transition to the next.
                spec = next(available_dimensions)
                assert (
                    await set_display_mode(emulator_controller, spec.mode) == spec.mode
                )
                await asyncio.sleep(3)


@pytest.mark.newresizable
@pytest.mark.parametrize(
    "fmt, bpp",
    [
        (ImageFormat.RGBA8888, 4),
        (ImageFormat.RGB888, 3),
    ],
)
@pytest.mark.flaky
async def test_new_resizable_folding_observable_from_streaming(
    avd,
    supported_resizable_resolutions,
    animation_app,
    emulator_controller,
    stream_screenshot,
    fmt,
    bpp,
):
    api_level = await avd.api_level()
    if api_level < 34:
        pytest.skip(reason="Requires api level >=34!")

    available_dimensions = iter(supported_resizable_resolutions)

    # start with unfold
    await set_device_hinge_angle(emulator_controller, 180)
    await asyncio.sleep(3)

    foldedw = 1080
    foldedh = 2092
    # Start with moving to the intial dimension
    spec = next(available_dimensions)
    updated = await set_display_mode(emulator_controller, spec.mode)
    assert updated == spec.mode
    await asyncio.sleep(3)

    # Transition to the next.
    spec = next(available_dimensions)
    updated = await set_display_mode(emulator_controller, spec.mode)
    assert updated == DisplayModeValue.FOLDABLE
    await asyncio.sleep(3)

    # Now fold it
    await set_device_hinge_angle(emulator_controller, 0)

    # Wait until we observe the expected dimension in the stream of screenshots
    def image_is_properly_sized(image):
        logging.info(
            "image_is_properly_sized %sx%s == %sx%s",
            image.format.width,
            image.format.height,
            foldedw,
            foldedh,
        )
        # cannot have empty frame
        assert len(image.image) > 0
        return (
            image.format.width == foldedw
            and image.format.height == foldedh
            and len(image.image) == foldedw * foldedh * bpp
        )

    stream = stream_screenshot(ImageFormat(format=fmt))
    assert await eventually(image_is_properly_sized, stream)


async def assertDisplayMode(expected_mode, emulator_controller):
    # Return 'True' if the current display mode is equal to 'expected_mode'
    mode = await emulator_controller.getDisplayMode(_EMPTY_)
    return mode.value == expected_mode


@pytest.mark.parametrize(
    "index, name, expected_mode",
    [
        (0, "Phone", DisplayModeValue.PHONE),
        (1, "Foldable", DisplayModeValue.FOLDABLE),
        (2, "Tablet", DisplayModeValue.TABLET),
        (3, "Desktop", DisplayModeValue.DESKTOP),
    ],
)
@pytest.mark.newresizable
@pytest.mark.fast
async def test_new_resizable_changes_resolution_from_console(
    index, name, expected_mode, telnet, emulator_controller
):
    """Verify the display mode can be changed from the emulator console.

    Args:
        index (int): Display mode index.
        name (str): Display mode description.
        expected_mode (DisplayModeValue): Display mode enumeration value.
        telnet (EmulatorConnection): Fixture that gives access to the emulator console.
        emulator_controller (EmulatorControllerStub): Emulator controller fixture.

    Test Steps:
        1. Launch a Resizable AVD.
        2. Using the emulator console, run the command "resize-display <index>".

    Verification:
        1. The screen size (observed from the updated display mode) is adjusted in
           accordance with the display mode selected, as following:
                0 = Phone
                1 = Foldable
                2 = Tablet
                3 = Desktop
    """
    logging.info(f"Resizing display to '{name}' ...")
    await telnet.send(f"resize-display {index}")

    assert await eventually(
        partial(assertDisplayMode, expected_mode, emulator_controller)
    ), "Couldn't set display to {name} mode"


@pytest.mark.fast
@pytest.mark.newresizable
@pytest.mark.async_timeout(2020)
async def test_new_resizable_snapshot_saves_display_mode(avd, emulator_controller):
    """Verify display mode is saved when a snapshot is created and loaded.

    Args:
        avd (BaseEmulator): Fixture that gives access to the running emulator.
        emulator_controller (EmulatorControllerStub): Emulator controller fixture.

    Test Steps:
        1. Launch a Resizable AVD.
        2. Change the display mode to Phone.
        3. Take a snapshot.
        4. Change the display mode to Foldable
        5. Load the snapshot created in step 3.
        6. Repeat step  2-5 for Tablet and Desktop display mode.

    Verification:
        1. When the snapshot is loaded, the original ('Phone') display mode is loaded.
    """
    # Set the display mode to 'Phone' and take a snapshot.
    console = await avd.console()
    await console.send(f"resize-display 0")
    await console.send("avd snapshot save phone_snapshot")

    for index, name, expected_mode in [
        (1, "Foldable", DisplayModeValue.FOLDABLE),
        (2, "Tablet", DisplayModeValue.TABLET),
        (3, "Desktop", DisplayModeValue.DESKTOP),
    ]:

        # Set a new display mode.
        logging.info(f"Setting display mode to '{name}' ...")
        await console.send(f"resize-display {index}")
        assert await eventually(
            partial(assertDisplayMode, expected_mode, emulator_controller)
        ), "Couldn't set the display mode to {name}."

        # Load the Phone snapshot.
        await console.send("avd snapshot load phone_snapshot")
        await avd.wait_for_boot()

        # Make sure the display mode reverts back to 'Phone'.
        assert await eventually(
            partial(assertDisplayMode, 0, emulator_controller)
        ), "The display mode didn't revert to {name} after the snapshot was loaded."

    await console.send("avd snapshot delete phone_snapshot")
