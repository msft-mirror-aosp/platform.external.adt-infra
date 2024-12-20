# -*- coding: utf-8 -*-
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
"""Tests that the default configuration will attempt to retry the tests."""
from emu.timing import eventually
import pytest
import time
import asyncio


async def async_sleep():
    """Async function that sleeps for 5 seconds."""
    await asyncio.sleep(5)


def sync_sleep():
    """Sync function that sleeps for 5 seconds."""
    time.sleep(1)


async def test_timeout_async_exit_fast():
    """Test that eventually times out quickly with async functions.

    This test verifies that the `eventually` function correctly handles timeouts
    when used with asynchronous functions. It checks that if the provided
    async function takes longer than the specified timeout, `eventually`
    returns False and does not wait for the async function to complete.

    Bug: 385348775
    """
    start = time.time()
    assert not await eventually(async_sleep, timeout=0.2)
    assert (
        time.time() - start < 1
    ), "Eventually should timeout immediately in async methods"


async def test_timeout_sync_works():
    """Test that eventually can handle synchronous functions

    This test verifies that the `eventually` function correctly handles timeouts
    when used with synchronous functions.

    **Important:** This demonstrates that using synchronous functions with `eventually`'s
    timeout can lead to unexpected behavior.

    The synchronous function will block for its entire duration, regardless of the timeout.

    Bug: 385348775
    """
    start = time.time()
    assert not await eventually(sync_sleep, timeout=0.2)
    assert time.time() - start > 0.5, (
        "Expected the test to take at least 0.9 seconds (due to sync_sleep's 1 second sleep)"
        f", but it only took {time.time() - start} seconds."
        "This likely means the synchronous function was unexpectedly terminated, which should not happen."
    )
