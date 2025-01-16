# Copyright 2024 The Android Open Source Project
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
import pytest
from aemu.proto.emulator_controller_pb2 import (
    FoldedDisplay,
    Image,
    ImageFormat,
    Notification,
    ParameterValue,
    PhysicalModelValue,
)
from google.protobuf import empty_pb2

BAD_MAX_INT = 4294967295
BAD_FOLDED_DISPLAY = FoldedDisplay(width=BAD_MAX_INT, height=BAD_MAX_INT)
BAD_IMAGE_FORMAT = ImageFormat(
    width=BAD_MAX_INT, height=BAD_MAX_INT, foldedDisplay=BAD_FOLDED_DISPLAY
)
BAD_IMAGE = Image(format=BAD_IMAGE_FORMAT)


@pytest.fixture
async def get_safe_screenshot(emulator_controller):
    """Provides a function to retrieve a screenshot, handling potential transient errors.

    This fixture addresses the `FAILED_PRECONDITION` error that can occur if the
    guest hasn't posted a new frame yet. It returns a predefined `BAD_IMAGE` if unsuccessful.

    Args:
        emulator_controller: The emulator controller instance.

    Returns:
        Callable[[ImageFormat], Awaitable[Image]]: An async function that takes
            an ImageFormat as input and returns a screenshot Image.
    """

    async def get_safe_screenshot_impl(fmt: ImageFormat = None):
        try:
            return await emulator_controller.getScreenshot(
                ImageFormat(format=ImageFormat.RGB888) if fmt is None else fmt
            )
        except Exception as e:
            logging.warning("Error getting screenshot: %s", e)
            return BAD_IMAGE

    return get_safe_screenshot_impl


@pytest.fixture
async def fold(emulator_controller):
    """Sets the emulator's hinge angle to 15 degrees, simulating a folded state.

    Returns:
        An async function that, when called, folds the emulator.
    """

    async def fold_impl():
        await emulator_controller.setPhysicalModel(
            PhysicalModelValue(
                target=PhysicalModelValue.HINGE_ANGLE0,
                value=ParameterValue(data=[15.0, 0.0, 0.0]),
            )
        )

    return fold_impl


@pytest.fixture
async def unfold(emulator_controller):
    """Sets the emulator's hinge angle to 180 degrees, simulating an unfolded state.

    Returns:
        An async function that, when called, unfolds the emulator.
    """

    async def unfold_impl():  # Renamed inner function for clarity
        await emulator_controller.setPhysicalModel(
            PhysicalModelValue(
                target=PhysicalModelValue.HINGE_ANGLE0,
                value=ParameterValue(data=[180.0, 0.0, 0.0]),
            )
        )

    return unfold_impl


@pytest.fixture
@pytest.mark.async_timeout(30)
async def start_unfolded(unfold, get_safe_screenshot):
    """Starts the emulator in an unfolded state and waits for a valid screenshot.

    Args:
        unfold: Fixture to unfold the emulator.
        get_safe_screenshot: Fixture to retrieve a screenshot safely.

    Returns:
        Image: A valid screenshot of the unfolded emulator.
    """
    await unfold()

    image = BAD_IMAGE
    while image == BAD_IMAGE:
        image = await get_safe_screenshot()

    return image


@pytest.fixture
@pytest.mark.async_timeout(30)
async def start_folded(fold, get_safe_screenshot):
    """Starts the emulator in a folded state and waits for a valid screenshot.


    Args:
        fold: Fixture to fold the emulator.
        get_safe_screenshot: Fixture to retrieve a screenshot safely.

    Returns:
        Image: A valid screenshot of the folded emulator.
    """
    await fold()

    image = BAD_IMAGE
    while image == BAD_IMAGE:
        image = await get_safe_screenshot()

    return image


@pytest.fixture
def notificationstream(emulator_controller):
    """Gets the emulator notification stream"""
    _EMPTY_ = empty_pb2.Empty()
    return emulator_controller.streamNotification(_EMPTY_)
