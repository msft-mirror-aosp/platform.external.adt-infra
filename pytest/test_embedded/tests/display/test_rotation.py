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
import asyncio
import logging
import re
from functools import partial

import pytest
from aemu.proto.emulator_controller_pb2 import (
    ImageFormat,
    ParameterValue,
    PhysicalModelValue,
    Rotation,
)
from PIL import Image

from emu.images.convert import proto_to_pillow
from emu.timing import eventually

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


async def for_each_rotation(emulator_controller):
    """Loops to each rotation mapping setting the physical rotation model and yielding z-axis and symbolic value."""
    for fine, coarse in ROTATION_MAPPING:
        logging.info("Rotating to fine: %s, coarse: %s", fine, coarse)
        await emulator_controller.setPhysicalModel(
            PhysicalModelValue(
                target=PhysicalModelValue.ROTATION,
                value=ParameterValue(data=[0, 0, fine]),
            )
        )
        yield fine, coarse


@pytest.mark.graphics
@pytest.mark.flaky(reruns=0)
async def test_rotation_observable_through_screenshot(
    emulator_controller, animation_app
):
    """Test that setting the rotation, is observable through getting a screenshot."""

    async def image_rotated_correctly(coarse) -> bool:
        img = await emulator_controller.getScreenshot(ImageFormat())
        logging.info("Current state: %s", img.format.rotation)
        return img.format.rotation.rotation == coarse

    async for fine, coarse in for_each_rotation(emulator_controller):

        async def is_properly_rotated():
            return await image_rotated_correctly(coarse)

        assert await eventually(is_properly_rotated, timeout=2)


@pytest.mark.graphics
@pytest.mark.flaky(reruns=0)
async def test_rotation_observable_through_adbstream(
    avd, animation_app, emulator_controller
):
    """Test that setting the rotation, is observable the adb logstream.
    This makes sure that android itself reports the orientation we are expecting.
    """
    ROTATION_RE = re.compile(r".*Rotation: (\d+)")

    def rotation_from_logcat(angle: int, line: str) -> bool:
        """True if we observe the message `Rotation: angle` on the line."""
        logging.info("Received %s", line)
        m = ROTATION_RE.match(line)
        return m and int(m.group(1)) == angle

    async with await avd.adb.logcat(tag="aemu") as stream:
        async for fine, coarse in for_each_rotation(emulator_controller):
            angle = counter_clockwise_to_clockwise(fine)
            assert await eventually(
                partial(rotation_from_logcat, angle), stream
            ), f"Did not observe a rotation to {angle} in time"


@pytest.mark.graphics
@pytest.mark.flaky(reruns=0)
async def test_stream_update_should_be_fast_after_rotation(
    emulator_controller, stream_screenshot
):
    """Test that the stream should be quickly updated after each rotation."""
    # wait for guest to go quiet
    await asyncio.sleep(5)
    async for angle, coarse in for_each_rotation(emulator_controller):

        def is_rotated(img):
            logging.info("img: %s - %s", img.seq, img.format.rotation)
            return img.format.rotation.rotation == coarse

        stream = stream_screenshot(ImageFormat())
        # new stream should be returnning screenshot within 500 ms
        # after rotation
        assert await eventually(
            is_rotated, stream, 0.5
        ), f"Did not observe rotation to {angle}"

        # wait again for it to go quiet
        await asyncio.sleep(5)


@pytest.mark.graphics
@pytest.mark.flaky(reruns=0)
async def test_rotation_observable_through_stream_screenshot(
    animation_app, emulator_controller, stream_screenshot
):
    """Test that setting the rotation, is observable through streaming screenshot."""
    async for angle, coarse in for_each_rotation(emulator_controller):

        def is_rotated(img):
            logging.info("img: %s - %s", img.seq, img.format.rotation)
            return img.format.rotation.rotation == coarse

        stream = stream_screenshot(ImageFormat())
        assert await eventually(
            is_rotated, stream
        ), f"Did not observe rotation to {angle}"


RED_PIXEL = (255, 0, 0)


def get_first_red_pixel(img: Image) -> (int, int):
    """Finds the relative coordinate of the first red pixel.

    A relative coordinate is normalized between [0, 1].

    Args:
        img (Image): A PIL image we are inspecting

    Returns:
        (int, int): A tuple with the relative x,y coordinate, or (-1, -1) if there is no red pixel.
    """
    # Get the bounding box, this makes sure the image data structures are
    # properly initalized.
    box = img.getbbox()
    logging.info("Inspecting %s, %sx%s", box, img.width, img.height)
    for x in range(img.width):
        for y in range(img.height):
            co = (x, y)
            pixel = img.getpixel(co)
            if pixel == RED_PIXEL:
                return (x / img.width, y / img.height)

    return (-1, -1)


def square_is_visible(img: Image) -> bool:
    """True if a red square is visible.

    It basically checks to see if we have a red pixel visible.

    Args:
        img (Image): The PIL image used to check for colors

    Returns:
        bool: True if a red pixel is visible.
    """
    colors = img.getcolors()
    if colors:
        for count, color in colors:
            if color == RED_PIXEL and count > 0:
                logging.info("Found %s red pixels", count)
                return True

    return False


def square_in_quadrant(img: Image) -> int:
    """Finds the quadrant containing the first red pixel.

    Args:
        img (Image): The pillow image we are inspecting

    Returns:
        int: The number of the quadrant, on of {1, 2, 3, 4} or 0 when not found
    """
    if not square_is_visible(img):
        return 0

    x, y = get_first_red_pixel(img)
    if x >= 0.5 and y <= 0.5:
        return 1
    if x < 0.5 and y <= 0.5:
        return 2
    if x < 0.5 and y > 0.5:
        return 3
    return 4


async def rotation_through_console_observable_through_screenshot(
    emulator_controller, telnet
):
    """Verify that rotation through console is observable through screenshot."""
    default = ImageFormat()
    for _, coarse in ROTATION_MAPPING:

        async def expected_rotation():
            screen = await emulator_controller.getScreenshot(default)
            return screen.format.rotation.rotation == coarse

        await telnet.send("rotate")
        assert await eventually(
            expected_rotation
        ), f"Did not observe rotation to {coarse}"


async def rotation_through_console_observable_through_stream_screenshot(
    stream_screenshot, telnet
):
    """Verify that rotation through console is observable through stream screenshot."""
    for angle, coarse in ROTATION_MAPPING:
        await telnet.send("rotate")

        async def image_has_coarse_rotation(img: Image) -> bool:
            """True if the rotation matches the coarse rotation."""
            return img.format.rotation.rotation == coarse

        stream = stream_screenshot(ImageFormat(width=320, height=200))
        # Keep looking at the queue until we see what we need.
        # if we never see it we will timeout.
        assert await eventually(
            image_has_coarse_rotation, stream
        ), f"Did not observe rotation to {angle} in time"


@pytest.mark.graphics
@pytest.mark.sanity
@pytest.mark.parametrize(
    "rotation, quadrant",
    [(0, 1), (90, 2), (-180, 3), (-90, 4)],
)
@pytest.mark.flaky(reruns=0)
@pytest.mark.async_timeout(120)
async def test_rotation_pixels_in_the_right_place(
    animation_app, emulator_controller, rotation, quadrant, stream_screenshot
):
    """Test the colored square is in the expected location.
    The animation app draws a square in the top right corner (first quadrant).
    During rotation we expect the square to end-up in the quadrant corresponding
    to the rotation.

    This tests make sure that we are rendering the screenshot properly.
    b/179172837, b/176886063
    """
    await emulator_controller.setPhysicalModel(
        PhysicalModelValue(
            target=PhysicalModelValue.ROTATION,
            value=ParameterValue(data=[0, 0, rotation]),
        )
    )

    def find_square_in_image(img: Image) -> bool:
        logging.info(
            "Checking if %s (%s) is in the right quadrant", img.seq, img.timestampUs
        )
        pillow_img = proto_to_pillow(img)
        return square_in_quadrant(pillow_img) == quadrant

    stream = stream_screenshot(ImageFormat(format=ImageFormat.RGB888))
    assert await eventually(
        find_square_in_image, stream, timeout=120
    ), f"Did not see the rotation to {rotation} in time."


@pytest.mark.graphics
@pytest.mark.flaky(reruns=0)
async def test_rotation_through_console_observable_through_physical_model(
    emulator_controller, telnet
):
    """Test that rotate through console, is observable through screenshot.
    bug: b/159635109
    """

    async def emulator_is_rotated_to(expected_angle):
        rotate = await emulator_controller.getPhysicalModel(
            PhysicalModelValue(target=PhysicalModelValue.ROTATION)
        )
        logging.info(
            "emulator_is_rotated_to %s == %s", rotate.value.data[2], expected_angle
        )
        return rotate.value.data[2] == expected_angle

    for angle, _ in ROTATION_MAPPING:

        async def emulator_is_rotated():
            return await emulator_is_rotated_to(angle)

        await telnet.send("rotate")
        assert await eventually(emulator_is_rotated)


@pytest.mark.graphics
@pytest.mark.flaky(reruns=0)
async def test_rotation_through_console_observable_through_screenshot(
    emulator_controller, telnet
):
    """Test that rotate through console, is observable through screenshot.
    bug: b/159635109
    """
    await rotation_through_console_observable_through_screenshot(
        emulator_controller, telnet
    )


@pytest.mark.graphics
@pytest.mark.flaky(reruns=0)
async def test_rotation_through_console_observable_through_stream_screenshot(
    animation_app, emulator_controller, telnet, stream_screenshot
):
    """Test that rotate through console, is observable through stream screenshot.

    bug: b/159635109, b/160171559
    """
    await rotation_through_console_observable_through_stream_screenshot(
        stream_screenshot, telnet
    )


@pytest.mark.embedded
@pytest.mark.sanity
@pytest.mark.flaky(reruns=0)
async def test_rotation_observable_through_screenshot_embedded_mode(
    emulator_controller, telnet, avd
):
    await rotation_through_console_observable_through_screenshot(
        emulator_controller, telnet
    )


@pytest.mark.embedded
@pytest.mark.flaky(reruns=0)
async def test_rotation_observable_through_stream_screenshot_embedded_mode(
    emulator_controller, telnet, avd, stream_screenshot
):
    await rotation_through_console_observable_through_stream_screenshot(
        stream_screenshot, telnet
    )
