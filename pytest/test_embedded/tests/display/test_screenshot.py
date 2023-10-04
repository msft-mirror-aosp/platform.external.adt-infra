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
import logging
import time
from time import sleep

import pytest
from aemu.proto.emulator_controller_pb2 import (
    ImageFormat,
    KeyboardEvent,
    ParameterValue,
    PhysicalModelValue,
)
from google.protobuf import empty_pb2
from grpc import RpcError, StatusCode

from emu.images.convert import proto_to_pillow
from tests.test_utils import wait_for_regex


def pause_animation_app(avd):
    """Pauses the animation app."""

    with avd.adb.logcat(tag="aemu") as stream:
        avd.description.get_emulator_controller().sendKey(
            KeyboardEvent(key="P", eventType=KeyboardEvent.keypress)
        )
        logging.info("Waiting for regex.")
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



@pytest.mark.graphics
@pytest.mark.embedded
@pytest.mark.parametrize("w,h", [(0, 0), (320, 200), (1920, 1080)])
@pytest.mark.timeout(timeout=60, func_only=True)
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_screenshot_all_formats_are_equal(
    avd, get_screenshot, animation_app, w, h
):
    """Make sure that all the screenshots are exactly the same, regardless of format.

    This is done by launching the animation app, and pausing it. This should make sure
    we always have the same frame displayed on the device.
    """
    assert pause_animation_app(avd)
    last_pixels = None
    for image_format in [ImageFormat.RGBA8888, ImageFormat.RGB888, ImageFormat.PNG]:
        _, pillow_image = get_screenshot(
            ImageFormat(format=image_format, width=w, height=h)
        )

        # a == b, b == c --> a == c, so we can just compare the last known image
        # to the current one.
        pixels = list(pillow_image.convert("RGB").getdata())
        assert len(set(pixels)) > 1, "Pixels should not all be the same!"
        assert last_pixels == None or last_pixels == pixels
        last_pixels == pixels


@pytest.mark.graphics
@pytest.mark.embedded
@pytest.mark.parametrize(
    "image_format,bpp",
    [(ImageFormat.RGB888, 3), (ImageFormat.RGBA8888, 4)],
)
@pytest.mark.parametrize("degrees", [0, 90])
@pytest.mark.timeout(timeout=60, func_only=True)
def test_screenshot_exact_amount_of_pixels(
    at_home, get_screenshot, emulator_controller, image_format, bpp, degrees
):
    """Tests that the screenshot API delivers exactly the right amount of pixels.

    The number of pixels is determined by the bytes per pixel * w * h, irrespective of rotation.
    """
    rotate_device(emulator_controller, degrees)

    image, _ = get_screenshot(
        ImageFormat(
            format=image_format,
        )
    )
    assert len(image.image) == (bpp * image.format.width * image.format.height)


@pytest.fixture
def default_display_config(emulator_controller):
    """A fixture that provides the default (display 0) configuration of the emulator."""
    _EMPTY_ = empty_pb2.Empty()
    display_cfg = emulator_controller.getDisplayConfigurations(_EMPTY_)
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
def all_orientations(emulator_controller, request):
    """A fixture that will rotate the emulator in all possible orientations."""

    # Map labels to orientation, this is mainly so the tests are are named nicely.
    ROTATION_MAPPING = {
        "REVERSE_LANDSCAPE": -90,
        "REVERSE_PORTRAIT": -180,
        "LANDSCAPE": 90,
        "PORTRAIT": 0,
    }

    emulator_controller.setPhysicalModel(
        PhysicalModelValue(
            target=PhysicalModelValue.ROTATION,
            value=ParameterValue(data=[0, 0, ROTATION_MAPPING[request.param]]),
        )
    )
    # Give the emulator a chance to actually rotate around.
    sleep(0.1)


@pytest.mark.timeout(timeout=60, func_only=True)
@pytest.mark.graphics
@pytest.mark.embedded
def test_screenshot_gets_default_resolution(
    at_home, get_screenshot, default_display_config, all_orientations
):
    """Verifies that the default resolution will match the emulator display dimensions"""
    image, _ = get_screenshot(ImageFormat())
    fmt = image.format
    assert (
        fmt.width == default_display_config.width
        or fmt.width == default_display_config.height
    ), "The width should be equal to the device width (portrait), or device height (landscape)"
    assert (
        fmt.height == default_display_config.height
        or fmt.height == default_display_config.width
    ), "The height should be equal to the device height (portrait), or device width (landscape)"


@pytest.mark.timeout(timeout=60, func_only=True)
@pytest.mark.graphics
@pytest.mark.embedded
def test_screenshot_never_scales_up(
    at_home, get_screenshot, default_display_config, all_orientations
):
    """Verifies b/238205075, streamScreenshot should not scale display images up."""
    # The width and height are guaranteed to be larger than the actual screen
    max_width = default_display_config.width + default_display_config.height
    max_height = default_display_config.height + default_display_config.width

    image, _ = get_screenshot(
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


@pytest.mark.timeout(timeout=60, func_only=True)
@pytest.mark.graphics
@pytest.mark.embedded
def test_screenshot_should_fail_if_does_not_exist(
    at_home, emulator_controller, default_display_config
):
    """Verifies b/206033509 streamScreenshot/getScreenshot should fail with INVALID_ARGUMENT if the display doesn't exist"""
    _EMPTY_ = empty_pb2.Empty()
    cfg = emulator_controller.getDisplayConfigurations(_EMPTY_)
    non_existing_display = len(cfg.displays) + 1
    with pytest.raises(RpcError) as e:
        image = emulator_controller.getScreenshot(
            ImageFormat(display=non_existing_display)
        )

    assert e.value.code() == StatusCode.INVALID_ARGUMENT
    assert e.value.details() == "Invalid display: {}".format(non_existing_display)
