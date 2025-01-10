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
import re


async def async_sleep():
    """Async function that sleeps for 5 seconds."""
    await asyncio.sleep(5)


def sync_sleep():
    """Sync function that sleeps for 5 seconds."""
    time.sleep(1)


@pytest.mark.test_infra
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


@pytest.mark.test_infra
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


@pytest.mark.test_infra
async def async_string_iterator(strings):
    """Turns a list of strings into an async iterator."""
    for string in strings:
        yield string
        await asyncio.sleep(0)


@pytest.mark.test_infra
async def test_eventual_sync_stream_works():
    """Tests the 'eventually' function with a synchronous predicate and an asynchronous iterator.

    This test verifies that 'eventually' correctly processes items from an asynchronous iterator
    using a synchronous predicate function. It checks that the predicate is called for each
    item in the stream and returns True when the expected item is encountered.
    """
    called = 0

    def compare_fn(x):
        nonlocal called
        called += 1
        return x == "you"

    stream = async_string_iterator(["hi", "how", "are", "you"])
    assert await eventually(compare_fn, stream)
    assert called == 4


@pytest.mark.test_infra
async def test_eventual_async_stream_works():
    """Tests the 'eventually' function with an asynchronous predicate and an asynchronous iterator.


    This test verifies that 'eventually' correctly handles both an asynchronous iterator and
    an asynchronous predicate.  It checks that the predicate is called the expected number
    of times and returns True when the target item is found.
    """
    called = 0

    async def async_compare_fn(x):
        nonlocal called
        await asyncio.sleep(0)  # For async behavior.
        called += 1
        return x == "you"

    stream = async_string_iterator(["hi", "how", "are", "you"])
    assert await eventually(async_compare_fn, stream)
    assert called == 4
