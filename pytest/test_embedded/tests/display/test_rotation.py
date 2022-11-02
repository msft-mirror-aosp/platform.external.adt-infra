# Copyright 2020 The Android Open Source Project
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
import re
import time
from time import sleep

import pytest
from aemu.proto.emulator_controller_pb2 import (
    ImageFormat,
    ParameterValue,
    PhysicalModelValue,
    Rotation,
)

from tests.test_utils import StreamingCall, fmt_proto

# This test validates the behavior of rotating the device.
# The android device derives its orientation from the physical model.
#
# This test validates that we can observe the effects of setting the z-axis of the physical model.
# We can observe the rotation status as follows:
#
# - As reported on logcat by the animation app. The app will report orientation changes on the log as:
#   Rotation: x, where x is a number. For example:  03-15 09:18:55.834 22914 22914 I aemu    : Rotation: 90
# - As reported by the getScreeenshot/streamScreenshot api
# - The delivered image. The app will draw a square with the color #DECEBE in the corner (quadrant 1).
#   We can find the pixels of the square in the resulting image and make sure the display is matching
#   what we expect.
#
# Some things to note:
# - Android itself will report the rotation clockwise, the physical model is counter clockwise.
# - The z-axis mapping to symbolic mapping is given below:
#
#
# We can modify the rotation by:
# - Setting the physical model.
# - Calling rotate on the telnet interface.


# This contains the mapping of the Z-axis towards the symbolic name.
ROTATION_MAPPING = [
    (-90, Rotation.REVERSE_LANDSCAPE),
    (-180, Rotation.REVERSE_PORTRAIT),
    (90, Rotation.LANDSCAPE),
    (0, Rotation.PORTRAIT),
]


def counter_clockwise_to_clockwise(angle):
    return (360 - angle) % 360


def for_each_rotation(emulator_controller):
    """Loops to each rotation mapping setting the physical rotation model and yielding z-axis and symbolic value."""
    for (fine, coarse) in ROTATION_MAPPING:
        emulator_controller.setPhysicalModel(
            PhysicalModelValue(
                target=PhysicalModelValue.ROTATION,
                value=ParameterValue(data=[0, 0, fine]),
            )
        )
        # Make sure we are not slamming this endpoint, and give the emulator
        # a chance to respond.
        time.sleep(0.2)
        yield fine, coarse


@pytest.mark.e2e
@pytest.mark.timeout(timeout=10, func_only=True)
def test_rotation_observable_through_screenshot(emulator_controller):
    """Test that setting the rotation, is observable through getting a screenshot."""
    for (fine, coarse) in for_each_rotation(emulator_controller):
        img = emulator_controller.getScreenshot(ImageFormat())
        logging.info(img.format.rotation)
        assert img.format.rotation.rotation == coarse


@pytest.mark.e2e
@pytest.mark.timeout(timeout=10, func_only=True)
def test_rotation_observable_through_adbstream(avd,
    at_home, animation_app, emulator_controller
):
    """Test that setting the rotation, is observable the adb logstream.
    This makes sure that android itself reports the orientation we are expecting.
    """
    ROTATION_RE = re.compile(r".*Rotation: (\d+)")
    with avd.adb.stream(["logcat", "-s", "aemu"]) as stream:
        # Wait for the first rotation (should be set to 0).
        for line in iter(stream.get, None):
            m = ROTATION_RE.match(line)
            if m and int(m.group(1)) == 0:
                break

        for (fine, coarse) in for_each_rotation(emulator_controller):
            for line in iter(stream.get, None):
                m = ROTATION_RE.match(line)
                if m:
                    assert int(m.group(1)) == counter_clockwise_to_clockwise(fine)
                    break


@pytest.mark.e2e
@pytest.mark.timeout(timeout=10, func_only=True)
@pytest.mark.flaky(reruns=3, reruns_delay=2)
def test_rotation_observable_through_stream_screenshot(
    animation_app, emulator_controller
):
    """Test that setting the rotation, is observable through streaming screenshot."""
    for (angle, coarse) in for_each_rotation(emulator_controller):
        sleep(0.2)
        imgStream = emulator_controller.streamScreenshot(ImageFormat())
        with StreamingCall(imgStream) as stream:
            # Keep looking at the queue until we see what we need.
            # if we never see it we will timeout.
            seen_rotation = False
            for img in stream:
                if img.format.rotation.rotation == coarse:
                    seen_rotation = True
                    break
            assert seen_rotation, "Did not observe rotation to {} in time".format(angle)


# Pixel color of the square.
BLOCK_PIXEL = bytes([0xDE, 0xCE, 0xBE])


def get_first_block_pixel(img):
    """Gets the relative position of the first pixel with the color BLOCK_PIXEL"""
    idx = int(img.image.find(BLOCK_PIXEL) / 3)

    y = int(idx / img.format.width)
    x = idx % img.format.width
    return x / img.format.width, y / img.format.height


def square_is_visible(img):
    """True if BLOCK_PIXEL is in the image."""
    return img.image.find(BLOCK_PIXEL) >= 0


def square_in_quadrant(img):
    """The quadrant where the square is rendered."""
    x, y = get_first_block_pixel(img)
    if x >= 0.5 and y <= 0.5:
        return 1
    if x < 0.5 and y <= 0.5:
        return 2
    if x < 0.5 and y > 0.5:
        return 3
    return 4


@pytest.mark.e2e
@pytest.mark.timeout(timeout=10, func_only=True)
@pytest.mark.flaky(reruns=3, reruns_delay=2)
@pytest.mark.skip(reason="Rotation is currently failing b/246780175")
def test_rotation_pixels_in_the_right_place(animation_app, emulator_controller):
    """Test the colored square is in the expected location.
    The animation app draws a square in the top right corner (first quadrant).
    During rotation we expect the square to end-up in the quadrant corresponding
    to the rotation.

    This tests make sure that we are rendering the screenshot properly.
    b/179172837, b/176886063
    """
    QUADRANT_MAP = {0: 1, 90: 2, -180: 3, -90: 4}
    imgStream = emulator_controller.streamScreenshot(
        ImageFormat(format=ImageFormat.RGB888), timeout=5
    )
    with StreamingCall(imgStream) as stream:
        for (angle, coarse) in for_each_rotation(emulator_controller):
            # Keep looking at the queue until we see what we need.
            # if we never see it we will timeout.
            seen_rotation = False
            for img in stream:
                if (
                    square_is_visible(img)
                    and square_in_quadrant(img) == QUADRANT_MAP[angle]
                ):
                    logging.info(
                        "Observered rotation to %s, found pixel in quadrant: %d",
                        fmt_proto(img.format.rotation),
                        square_in_quadrant(img),
                    )
                    seen_rotation = True
                    break
            assert seen_rotation, "Did not see the rotation to {} in time.".format(
                angle
            )


@pytest.mark.e2e
@pytest.mark.flaky(reruns=3, reruns_delay=2)
def test_rotation_through_console_observable_through_physical_model(
    emulator_controller, adb
):
    """Test that rotate through console, is observable through screenshot.
    bug: b/159635109
    """
    # Make sure we start straight!
    emulator_controller.setPhysicalModel(
        PhysicalModelValue(
            target=PhysicalModelValue.ROTATION,
            value=ParameterValue(data=[0, 0, 0]),
        )
    )
    for (angle, coarse) in ROTATION_MAPPING:
        sleep(0.5)
        adb(["emu", "rotate"])
        rotate = emulator_controller.getPhysicalModel(
            PhysicalModelValue(target=PhysicalModelValue.ROTATION)
        )
        assert rotate.value.data[2] == angle


@pytest.mark.e2e
@pytest.mark.timeout(timeout=10, func_only=True)
def test_rotation_through_console_observable_through_screenshot(
    at_home, emulator_controller, adb
):
    """Test that rotate through console, is observable through screenshot.
    bug: b/159635109
    """
    for (_, coarse) in ROTATION_MAPPING:
        sleep(0.2)
        adb(["emu", "rotate"])
        sleep(0.2)
        img = emulator_controller.getScreenshot(ImageFormat())
        assert img.format.rotation.rotation == coarse


@pytest.mark.e2e
@pytest.mark.timeout(timeout=10, func_only=True)
def test_rotation_through_console_observable_through_stream_screenshot(
    at_home, animation_app, emulator_controller, adb
):
    """Test that rotate through console, is observable through stream screenshot.

    bug: b/159635109, b/160171559
    """
    for (angle, coarse) in ROTATION_MAPPING:
        sleep(0.5)
        adb(["emu", "rotate"])
        imgStream = emulator_controller.streamScreenshot(
            ImageFormat(width=320, height=200), timeout=5
        )
        with StreamingCall(imgStream) as stream:
            # Keep looking at the queue until we see what we need.
            # if we never see it we will timeout.
            for img in stream:
                if img.format.rotation.rotation == coarse:
                    seen_rotation = True
                    break

            assert seen_rotation, "Did not observe rotation to {} in time".format(angle)
