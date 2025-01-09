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

import pytest
from aemu.proto.emulator_controller_pb2 import Posture, Notification

from tests.foldable.fixtures import (
    fold,
    unfold,
    start_unfolded,
    start_folded,
    notificationstream,
    get_safe_screenshot,
)
from emu.timing import eventually


def is_posture_closed(notification: Notification):
    """Checks if the notification indicates a closed posture.

    Args:
        notification: The notification to check.

    Returns:
        True if the notification's posture is POSTURE_CLOSED, False otherwise.
    """
    return notification.posture.value == Posture.PostureValue.POSTURE_CLOSED


def is_posture_opened(notification: Notification):
    """Checks if the notification indicates an opened posture.

    Args:
        notification: The notification to check.

    Returns:
        True if the notification's posture is POSTURE_OPENED, False otherwise.
    """
    return notification.posture.value == Posture.PostureValue.POSTURE_OPENED


@pytest.mark.newfoldable
@pytest.mark.async_timeout(10)
async def test_new_foldable_immediately_receives_an_unfolded_notification(
    notificationstream, start_unfolded
):
    """Tests that a new foldable emulator immediately receives an unfolded notification.

    Args:
        notificationstream: The emulator's notification stream.
        start_unfolded: Fixture to start the emulator in unfolded state.
    """
    assert await eventually(
        is_posture_opened, notificationstream
    ), f"Did not observe initial unfolded state."


@pytest.mark.newfoldable
@pytest.mark.async_timeout(10)
async def test_new_foldable_receives_a_fold_notification(
    notificationstream, start_unfolded, fold
):
    """Tests that a new foldable emulator receives a fold notification after folding.

    Args:
        notificationstream: The emulator's notification stream.
        start_unfolded: Fixture to start the emulator in unfolded state.
        fold: Fixture to fold the emulator.
    """
    await fold()
    assert await eventually(
        is_posture_closed, notificationstream
    ), f"Did not receive a folded event"


@pytest.mark.newfoldable
@pytest.mark.async_timeout(10)
async def test_new_foldable_immediately_receives_a_folded_notification(
    notificationstream, start_folded
):
    """Tests that a new foldable emulator immediately receives a folded notification.

    Args:
        notificationstream: The emulator's notification stream.
        start_folded: Fixture to start the emulator in folded state.
    """
    assert await eventually(
        is_posture_closed, notificationstream
    ), f"Did not observe initial folded state."


@pytest.mark.newfoldable
@pytest.mark.async_timeout(10)
async def test_new_foldable_receives_an_unfold_notification(
    notificationstream, start_folded, unfold
):
    """Tests that a new foldable emulator receives an unfold notification after unfolding.

    Args:
        notificationstream: The emulator's notification stream.
        start_folded: Fixture to start the emulator in folded state.
        unfold: Fixture to unfold the emulator.
    """
    await unfold()
    assert await eventually(
        is_posture_opened, notificationstream
    ), f"Did not receive an unfolded event"
