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
import tempfile

import pytest
from emu.images.convert import proto_to_pillow
from aemu.proto.emulator_controller_pb2 import (
    ImageFormat,
    KeyboardEvent,
    ParameterValue,
    PhysicalModelValue,
)
from aemu.proto.emulator_controller_pb2_grpc import EmulatorControllerStub
from google.protobuf import empty_pb2
from grpc import RpcError, StatusCode
from emu.timing import eventually


async def wait_for_regex(stream, regex, max_wait):
    """Waits for the given regex to appear on the logcat stream,
    or until max_wait time has passed.

    Returns the match, or None in case of timeout.
    """
    compiled = re.compile(regex)
    return await eventually(compiled.match, stream, timeout=max_wait)


async def pause_animation_app(avd):
    """Pauses the animation app."""

    async with await avd.adb.logcat(tag="aemu") as stream:
        controller = EmulatorControllerStub(avd.channel)
        await controller.sendKey(
            KeyboardEvent(key="P", eventType=KeyboardEvent.keypress)
        )
        logging.info("Waiting for regex.")
        return await wait_for_regex(stream, r".*Pausing animation.", 5)


async def rotate_device(emu, angle):
    """Rotate the device to the given angle."""
    await emu.setPhysicalModel(
        PhysicalModelValue(
            target=PhysicalModelValue.ROTATION,
            value=ParameterValue(data=[0, 0, angle]),
        )
    )
    await asyncio.sleep(0.2)


EMU_TO_PIL_IMAGE_FORMATS = {
    ImageFormat.RGB888: "RGB",
    ImageFormat.RGBA8888: "RGBA",
    ImageFormat.PNG: "PNG",
}


@pytest.mark.embedded
@pytest.mark.fast
@pytest.mark.parametrize("w,h", [(0, 0), (320, 200), (1920, 1080)])
@pytest.mark.flaky(reruns=0)
async def test_screenshot_all_formats_are_equal(
    avd, get_screenshot, animation_app, w, h
):
    """Make sure that all the screenshots are exactly the same, regardless of format.

    This is done by launching the animation app, and pausing it. This should make sure
    we always have the same frame displayed on the device.
    """
    assert await pause_animation_app(avd)
    last_pixels = None
    for image_format in [ImageFormat.RGBA8888, ImageFormat.RGB888, ImageFormat.PNG]:
        _, pillow_image = await get_screenshot(
            ImageFormat(format=image_format, width=w, height=h)
        )

        # a == b, b == c --> a == c, so we can just compare the last known image
        # to the current one.
        pixels = list(pillow_image.convert("RGB").getdata())
        assert len(set(pixels)) > 1, "Pixels should not all be the same!"
        assert last_pixels == None or last_pixels == pixels
        last_pixels == pixels


@pytest.mark.embedded
@pytest.mark.sanity
@pytest.mark.parametrize(
    "image_format,bpp",
    [(ImageFormat.RGB888, 3), (ImageFormat.RGBA8888, 4)],
)
@pytest.mark.parametrize("degrees", [0, 90])
@pytest.mark.flaky(reruns=0)
async def test_screenshot_exact_amount_of_pixels(
    get_screenshot, emulator_controller, image_format, bpp, degrees
):
    """Tests that the screenshot API delivers exactly the right amount of pixels.

    The number of pixels is determined by the bytes per pixel * w * h, irrespective of rotation.
    """
    await rotate_device(emulator_controller, degrees)

    image, _ = await get_screenshot(
        ImageFormat(
            format=image_format,
        )
    )
    assert len(image.image) == (bpp * image.format.width * image.format.height)


@pytest.fixture
async def default_display_config(emulator_controller):
    """A fixture that provides the default (display 0) configuration of the emulator."""
    _EMPTY_ = empty_pb2.Empty()
    display_cfg = await emulator_controller.getDisplayConfigurations(_EMPTY_)
    default_display_config = display_cfg.displays[0]
    assert default_display_config.display == 0
    return default_display_config


@pytest.fixture(
    params=[
        "PORTRAIT",
        "LANDSCAPE",
        "REVERSE_PORTRAIT",
        "REVERSE_LANDSCAPE",
    ]
)
async def all_orientations(emulator_controller, request):
    """A fixture that will rotate the emulator in all possible orientations."""

    # Map labels to orientation, this is mainly so the tests are are named nicely.
    ROTATION_MAPPING = {
        "REVERSE_LANDSCAPE": -90,
        "REVERSE_PORTRAIT": -180,
        "LANDSCAPE": 90,
        "PORTRAIT": 0,
    }

    await emulator_controller.setPhysicalModel(
        PhysicalModelValue(
            target=PhysicalModelValue.ROTATION,
            value=ParameterValue(data=[0, 0, ROTATION_MAPPING[request.param]]),
        )
    )
    # Give the emulator a chance to actually rotate around.
    await asyncio.sleep(0.1)


# bug 299344829
@pytest.mark.embedded
@pytest.mark.async_timeout(120)
@pytest.mark.flaky(reruns=0)
async def test_screenshot_valid_width_and_height(
    avd, get_screenshot, default_display_config
):
    """Make sure that screenshot returns valid w and h"""

    image, _ = await get_screenshot(ImageFormat())
    fmt = image.format
    assert (
        fmt.width == default_display_config.width
        and fmt.height == default_display_config.height
    ), "The width and height should be equal to the device width and height"


@pytest.mark.embedded
@pytest.mark.flaky(reruns=0)
async def test_screenshot_gets_default_resolution(
    get_screenshot, default_display_config, all_orientations
):
    """Verifies that the default resolution will match the emulator display dimensions"""
    image, _ = await get_screenshot(ImageFormat())
    fmt = image.format
    assert (
        fmt.width == default_display_config.width
        or fmt.width == default_display_config.height
    ), "The width should be equal to the device width (portrait), or device height (landscape)"
    assert (
        fmt.height == default_display_config.height
        or fmt.height == default_display_config.width
    ), "The height should be equal to the device height (portrait), or device width (landscape)"


@pytest.mark.embedded
@pytest.mark.flaky(reruns=0)
async def test_screenshot_never_scales_up(
    get_screenshot, default_display_config, all_orientations
):
    """Verifies b/238205075, streamScreenshot should not scale display images up."""
    # The width and height are guaranteed to be larger than the actual screen
    max_width = default_display_config.width + default_display_config.height
    max_height = default_display_config.height + default_display_config.width

    image, _ = await get_screenshot(
        ImageFormat(width=max_width, height=max_height, display=0)
    )

    fmt = image.format
    assert (
        fmt.width == default_display_config.width
        or fmt.width == default_display_config.height
    ), "The width should be equal to the device width (portrait), or device height (landscape)"
    assert (
        fmt.height == default_display_config.height
        or fmt.height == default_display_config.width
    ), "The height should be equal to the device height (portrait), or device width (landscape)"


@pytest.mark.embedded
@pytest.mark.flaky(reruns=0)
async def test_screenshot_should_fail_if_does_not_exist(
    emulator_controller, default_display_config
):
    """Verifies b/206033509 streamScreenshot/getScreenshot should fail with INVALID_ARGUMENT if the display doesn't exist"""
    _EMPTY_ = empty_pb2.Empty()
    cfg = await emulator_controller.getDisplayConfigurations(_EMPTY_)
    non_existing_display = len(cfg.displays) + 1
    with pytest.raises(RpcError) as e:
        _ = await emulator_controller.getScreenshot(
            ImageFormat(display=non_existing_display)
        )

    assert e.value.code() == StatusCode.INVALID_ARGUMENT
    assert e.value.details() == "Invalid display: {}".format(non_existing_display)


@pytest.mark.graphics
async def test_screenshot_saved_to_other_folder(get_screenshot):
    """Ensure a screenshot can be saved to a non-default location.

    Args:
        get_screenshot: Screenshot fixture

    Test UUID: 2505c26f-0d87-4b2a-81c1-e504787cb5ac

    Test steps:
      1. Create a temporary screenshot folder.
      2. Take a screenshot and save to the temporary folder.

    Verify:
      Screen capture file should appear in the specified location.
    """
    with tempfile.TemporaryDirectory() as screenshot_dir:
        _, pillow_image = await get_screenshot(screenshot_dir=screenshot_dir)
        assert pillow_image.filename.exists(), "Temporary screenshot not created."


@pytest.mark.slow
@pytest.mark.graphics
@pytest.mark.fast
@pytest.mark.async_timeout(1080)
async def test_screenshot_capture_stress(emulator, tmp_path):
    """Verify screenshot task under repeated requests.

    Args:
        emulator (BaseEmulator): Fixture that gives access to the configured emulator.
        tmp_path (Path): Fixture that provides a temporary working directory.

    Test Steps:
        1. Launch an AVD.
        2. Use the emulator console to take a screenshot (Verify 1 and 2).

    Verification:
        1. Screenshots appear in the temporary path.
        2. Not every screenshot requests generates an image.
    """

    async def take_screenshots(n):
        # Take n sequential screenshots using the emulator console.
        console = await emulator.console()
        for _ in range(n):
            await console.send(f"screenrecord screenshot {tmp_path}")
            await asyncio.sleep(0.1)

    def _get_screenshots_list():
        screenshots_dir = tmp_path
        screenshots = list(screenshots_dir.glob("Screenshot_*.png"))
        return screenshots

    async def screenshots_completed():
        # Wait until no screenshots are saved within a 5-seconds interval.
        current_screenshots = _get_screenshots_list()
        await asyncio.sleep(5)
        screenshots = _get_screenshots_list()
        return None if len(current_screenshots) != len(screenshots) else True

    # Configure the emulator to save the screenshots to tmp_path
    myflags = ["-save-path", tmp_path]
    await emulator.launch(emulator.launch_flags + myflags)
    await emulator.wait_for_boot()

    # Repeatedly take screenshots.
    num_requests = 250
    await take_screenshots(num_requests)

    await eventually(screenshots_completed, timeout=600)
    screenshots = _get_screenshots_list()
    logging.info(f"{len(screenshots)} (out of {num_requests}) screenshots were taken.")

    # Verify screenshots appear in the default save location.
    assert (
        len(screenshots) != 0
    ), "Coudn't take any screenshot using the emulator console."

    # Verify not every Ctrl+S screenshot keystroke generates a screenshot.
    assert (
        len(screenshots) != num_requests
    ), f"All requested screenshots were saved (expected less than {num_requests})."
