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

import pytest

from emu.timing import eventually
from tests.foldable.fixtures import (
    BAD_IMAGE,
    fold,
    get_safe_screenshot,
    start_folded,
    start_unfolded,
    unfold,
)


@pytest.mark.newfoldable
@pytest.mark.async_timeout(30)
async def test_zero_folded_display_size_when_unfolded(
    animation_app, get_safe_screenshot, unfold, start_folded
):
    """Verifies the folded display size is zero when the emulator is unfolded.

    Args:
        animation_app: Fixture for the animation app.
        get_safe_screenshot: Fixture to get a safe screenshot.
        unfold: Fixture to unfold the emulator.
        start_folded: Fixture to start the emulator in a folded state.
    """
    unfolded_screenshot = BAD_IMAGE

    async def is_folded_display_size_zero():
        nonlocal unfolded_screenshot
        unfolded_screenshot = await get_safe_screenshot()
        fmt = unfolded_screenshot.format.foldedDisplay
        return fmt.width == 0 and fmt.height == 0

    await unfold()

    assert await eventually(
        is_folded_display_size_zero, timeout=20
    ), f"Folded display size is not zero when unfolded: {unfolded_screenshot.format}"


@pytest.mark.newfoldable
@pytest.mark.async_timeout(30)
async def test_display_width_increases_when_unfolded(
    animation_app, get_safe_screenshot, unfold, start_folded
):
    """Verifies display width increases when the emulator is unfolded.

    Args:
        animation_app: Fixture for the animation app.
        get_safe_screenshot: Fixture to get a safe screenshot.
        unfold: Fixture to unfold the emulator.
        start_folded: Fixture to start the emulator in a folded state.
    """
    unfolded_screenshot = BAD_IMAGE

    async def is_display_wider_than_folded():
        nonlocal unfolded_screenshot
        unfolded_screenshot = await get_safe_screenshot()
        return (
            unfolded_screenshot != BAD_IMAGE
            and unfolded_screenshot.format.width > start_folded.format.width
        )

    await unfold()

    assert await eventually(
        is_display_wider_than_folded, timeout=20
    ), f"Unfolded display width is not larger than folded: unfolded={unfolded_screenshot.format}, folded={start_folded.format}"


@pytest.mark.newfoldable
@pytest.mark.async_timeout(30)
async def test_display_width_decreases_when_folded(
    animation_app, get_safe_screenshot, fold, start_unfolded
):
    """Verifies display width decreases when the emulator is folded.

    Args:
        animation_app: Fixture for the animation app.
        get_safe_screenshot: Fixture to get a safe screenshot.
        fold: Fixture to fold the emulator.
        start_unfolded: Fixture to start the emulator unfolded.
    """
    folded_screenshot = BAD_IMAGE

    async def is_display_narrower_than_unfolded():
        nonlocal folded_screenshot
        folded_screenshot = await get_safe_screenshot()
        return (
            folded_screenshot != BAD_IMAGE
            and start_unfolded.format.width > folded_screenshot.format.width
        )

    await fold()

    assert await eventually(
        is_display_narrower_than_unfolded, timeout=20
    ), f"Folded display width is not smaller than unfolded: folded={folded_screenshot.format}, unfolded={start_unfolded.format}"


@pytest.mark.newfoldable
@pytest.mark.async_timeout(30)
async def test_folded_display_format_matches_screenshot_format(
    animation_app, get_safe_screenshot, fold, start_unfolded
):
    """Verifies the folded display format matches the screenshot format when folded.

    Args:
        animation_app: Fixture for the animation app.
        get_safe_screenshot: Fixture to get a safe screenshot.
        fold: Fixture to fold the emulator.
        start_unfolded: Fixture to start the emulator unfolded.
    """
    folded_screenshot = BAD_IMAGE

    async def is_folded_display_format_correct():
        nonlocal folded_screenshot
        folded_screenshot = await get_safe_screenshot()
        fmt = folded_screenshot.format.foldedDisplay
        return (
            folded_screenshot != BAD_IMAGE
            and fmt.width == folded_screenshot.format.width
            and fmt.height == folded_screenshot.format.height
        )

    await fold()

    assert await eventually(
        is_folded_display_format_correct, timeout=20
    ), f"Folded display and image format do not match: folded_display={folded_screenshot.format.foldedDisplay}, image_format={folded_screenshot.format}"
