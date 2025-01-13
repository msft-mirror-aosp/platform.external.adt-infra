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
from emu.timing import eventually, retry
import pytest
import time
import asyncio
import re


class MockLogger:
    def __init__(self):
        self.messages = []

    def warning(self, *msg):
        self.messages.append(("WARNING", msg))

    def error(self, *msg):
        self.messages.append(("ERROR", msg))


@pytest.fixture
def mock_logger(monkeypatch):
    logger = MockLogger()
    monkeypatch.setattr("logging.warning", logger.warning)
    monkeypatch.setattr("logging.error", logger.error)
    return logger


# Test cases
async def test_retry_success_immediately(mock_logger):
    async def succeed():
        return "success"

    result = await retry(succeed, attempts=3)
    assert result == "success"
    assert len(mock_logger.messages) == 0  # No warnings or errors should be logged


async def test_retry_success_after_retries(mock_logger):
    attempts_counter = 0

    async def succeed_on_second_try():
        nonlocal attempts_counter
        attempts_counter += 1
        if attempts_counter < 2:
            return None  # Falsy value
        else:
            return "success"

    result = await retry(succeed_on_second_try, attempts=3, delay=0.1)
    assert result == "success"
    assert attempts_counter == 2
    assert len(mock_logger.messages) == 1
    assert mock_logger.messages[0][0] == "WARNING"
    assert "returned a falsy value: None" in mock_logger.messages[0][1]


async def test_retry_failure_all_attempts_falsy(mock_logger):
    async def always_fail():
        return None

    with pytest.raises(RuntimeError) as excinfo:
        await retry(always_fail, attempts=3, delay=0.1)
    assert "failed after 3 attempts" in str(excinfo.value)
    assert len(mock_logger.messages) == 4


async def test_retry_failure_all_attempts_exception(mock_logger):
    async def always_fail():
        raise ValueError("oops")

    with pytest.raises(ValueError) as excinfo:
        await retry(always_fail, attempts=3, delay=0.1)
    assert "oops" in str(excinfo.value)
    assert len(mock_logger.messages) == 4


async def test_retry_with_custom_exception(mock_logger):
    async def fail_with_custom_exception():
        raise KeyError("key not found")

    with pytest.raises(KeyError) as excinfo:
        await retry(
            fail_with_custom_exception,
            attempts=3,
            delay=0.1,
            retry_on_exception=KeyError,
        )
    assert "key not found" in str(excinfo.value)


async def test_retry_no_retry_on_different_exception(mock_logger):
    async def fail_with_different_exception():
        raise ValueError("invalid value")

    with pytest.raises(ValueError) as excinfo:
        await retry(
            fail_with_different_exception,
            attempts=3,
            delay=0.1,
            retry_on_exception=KeyError,
        )
    assert "invalid value" in str(excinfo.value)
    assert (
        len(mock_logger.messages) == 0
    )  # No warnings or errors should be logged, since we didn't retry


async def test_retry_no_retry_on_falsy_success(mock_logger):
    async def return_falsy_but_we_accept_it():
        return None

    result = await retry(
        return_falsy_but_we_accept_it, attempts=3, retry_on_falsy=False
    )
    assert result is None
    assert len(mock_logger.messages) == 0


async def test_retry_named_operation(mock_logger):
    async def succeed_eventually():
        return "ok"

    result = await retry(succeed_eventually, attempts=3, name="My Operation")
    assert result == "ok"
    assert len(mock_logger.messages) == 0


async def test_retry_with_arguments(mock_logger):
    attempts_counter = 0

    async def succeed_with_args(a, b):
        nonlocal attempts_counter
        attempts_counter += 1
        if attempts_counter < 3:
            raise ValueError("Not enough attempts")
        else:
            return a + b

    result = await retry(
        lambda: succeed_with_args(5, 10), attempts=5, delay=0.1, name="Addition"
    )
    assert result == 15
    assert attempts_counter == 3


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
