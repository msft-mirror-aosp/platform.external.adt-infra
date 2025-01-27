# Copyright 2023 - The Android Open Source Project
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
import time
from typing import (
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
    TypeVar,
    Coroutine,
    Type,
    Union,
)

T = TypeVar("T")


async def retry(
    operation: Callable[..., Coroutine[Any, Any, T]],
    attempts: int,
    delay: float = 1,
    name: str = "",
    retry_on_exception: Union[Type[Exception], tuple[Type[Exception], ...]] = Exception,
    retry_on_falsy: bool = True,
) -> T:
    """Retries an asynchronous operation a specified number of times.

    Args:
        operation: The asynchronous operation to retry.
        attempts: The maximum number of attempts to make.
        delay: The delay in seconds between attempts.
        name: An optional name to identify the operation in log messages.
        retry_on_exception: The exception type(s) to catch and retry on. Defaults to `Exception` (all exceptions).
        retry_on_falsy: Whether to retry if the operation returns a falsy value (e.g., None, False, 0, "").
                         Defaults to True.

    Returns:
        The result of the operation if successful.

    Raises:
        Exception: If all attempts fail, the exception from the last attempt is raised.
    """
    last_exception = None
    for attempt in range(attempts):
        try:
            result = await operation()
            if result or not retry_on_falsy:
                return result
            else:
                logging.warning(
                    "%s attempt %s/%s returned a falsy value: %s, retrying...",
                    name,
                    attempt + 1,
                    attempts,
                    result,
                )
        except retry_on_exception as e:
            last_exception = e
            logging.warning(
                "%s attempt %s/%s raised an exception: %s, retrying...",
                name,
                attempt + 1,
                attempts,
                e,
            )

        if attempt < attempts - 1:
            await asyncio.sleep(delay)

    error_message = "%s failed after %s attempts." % (name, attempts)
    if last_exception:
        error_message += " Last exception: %s" % last_exception
    logging.error(error_message)
    if last_exception:
        raise last_exception
    raise RuntimeError(error_message)


async def _true() -> bool:
    """Returns True. Used as a default pre_requisite for wait_until.

    Note: this is a simple function, hence can be awaited.
    """
    return True


async def ensure_awaitable(
    fn: Callable[[], Any] | Callable[[], Awaitable[Any]]
) -> bool:
    """Awaits a callable, whether it's synchronous or asynchronous.

    Args:
        fn: The callable to await.  Can be a regular function or a coroutine.

    Returns:
        The result of calling the callable.
    """
    if asyncio.iscoroutinefunction(fn):
        return await fn()
    else:
        return fn()


async def _wait_until(
    predicate: Callable[[], Awaitable[bool]],
    timeout: float,
    pre_requisite: Callable[[], Awaitable[bool]],
    hz: float,
) -> bool:
    """
    Waits until a predicate becomes True or a timeout is reached.

    This internal function periodically checks the `predicate` and `pre_requisite`.
    The wait continues as long as `predicate` is False, `pre_requisite` is True,
    and the timeout hasn't been reached.

    **Important:** Synchronous functions passed as `predicate`
    or `pre_requisite` will not be terminated when the timeout is reached.
    They can potentially block indefinitely.

    Args:
        predicate: A callable (regular function or coroutine) that returns a boolean value.
                   It's checked repeatedly until it returns True or the timeout expires.
        timeout: The maximum time to wait, in seconds.
        pre_requisite: A callable (regular function or coroutine) that also must
                       return True for the wait to continue.
        hz: The frequency at which to check the `predicate` and `pre_requisite`, in Hz.

    Returns:
        True if both `predicate` and `pre_requisite` returned True within the timeout, False otherwise.
    """

    start = time.time()
    end = time.time() + timeout

    predicate_state = await asyncio.wait_for(
        ensure_awaitable(predicate), timeout=end - time.time()
    )
    pre_requisite_state = await asyncio.wait_for(
        ensure_awaitable(pre_requisite), timeout=end - time.time()
    )

    while not predicate_state and (time.time() < end and pre_requisite_state):
        await asyncio.sleep(1 / hz)
        predicate_state = await asyncio.wait_for(
            ensure_awaitable(predicate), timeout=end - time.time()
        )
        pre_requisite_state = await asyncio.wait_for(
            ensure_awaitable(pre_requisite), timeout=end - time.time()
        )

    if time.time() >= end:
        logging.warning("Operation timed out after %s seconds", time.time() - start)
        if not asyncio.iscoroutinefunction(
            predicate
        ) or not asyncio.iscoroutinefunction(pre_requisite):
            logging.error(
                "Cannot guarantee timeouts for synchronous functions, please use async predicates if possible"
            )

    return predicate_state and pre_requisite_state


async def wait_until(
    predicate: Callable[[], Awaitable[bool]],
    timeout: float = 15,
    pre_requisite: Callable[[], Awaitable[bool]] = _true,
    hz: float = 2,
) -> bool:
    """
    Waits until a predicate becomes True, a pre_requisite becomes False, or a timeout is reached.

    This function periodically checks the `predicate` and `pre_requisite` until either:

    1. `predicate` returns True
    2. `pre_requisite` returns False
    3. The specified `timeout` is reached.

    If `pre_requisite` returns False, the wait is aborted early.
    This is useful when `predicate` depends on a condition that's no longer possible.

    **Important:** Synchronous functions passed as `predicate` or `pre_requisite`
    will not be terminated when the timeout is reached. They can potentially block indefinitely.

    Args:
        predicate: A callable (regular function or coroutine) that returns a boolean value.
                   It's checked repeatedly until it returns True or the timeout expires.
        timeout: The maximum time to wait, in seconds. Defaults to 15.
        pre_requisite: A callable (regular function or coroutine) that returns a boolean value.
                       If it returns False, the wait is aborted.
                       Defaults to a function that always returns True.
        hz: The frequency at which to check `predicate` and `pre_requisite`, in Hz. Defaults to 2.

    Returns:
        True if `predicate` returned True before the timeout or if `pre_requisite` returned False.
        False if the timeout was reached.
    """
    try:
        return await _wait_until(predicate, timeout, pre_requisite, hz)
    except asyncio.TimeoutError:
        logging.error("Operation timed out after %s seconds", timeout)
        return False


async def _eventually_async_iter(
    queue: AsyncIterator[T], predicate: Callable[[T], Awaitable[bool]]
) -> T | None:
    """
    Iterates through an asynchronous iterator, checking a predicate against each item.

    This function is designed for asynchronous iterators where you
    need to find an item that satisfies a specific condition.

    Args:
        queue: The asynchronous iterator to search through.
        predicate: An asynchronous function that takes an item from
                   the iterator and returns True if it matches, False otherwise.

    Returns:
        The first item that satisfies the `predicate`, or None
        if no such item is found or the iterator is exhausted.
    """
    async for event in queue:
        if asyncio.iscoroutinefunction(predicate):
            if await predicate(event):
                return event
        else:
            if predicate(event):
                return event

    # We timed out or exhausted the iterator.
    return None


async def _wait_for_event(
    predicate: Callable[[Any], Awaitable[bool]],
    iterator: AsyncIterator[Any],
    timeout: float = 5,
) -> Any | None:
    """
    Waits for an event from an asynchronous iterator that satisfies a predicate.

    This function checks each event produced by the `iterator` against the `predicate`.

    Args:
        predicate: A function (regular or asynchronous) that takes an event from the `iterator`
                   and returns True if the event satisfies the condition.
        iterator: An asynchronous iterator that produces events.
        timeout: The maximum time to wait for a matching event, in seconds. Defaults to 5.

    Returns:
        The first event from the `iterator` for which `predicate` returns True,
        or None if no such event is found within the timeout.
    """
    # We need to special case queue handlers as they use their own thread
    # and will handle timeouts themselves.
    try:
        return await asyncio.wait_for(
            _eventually_async_iter(iterator, predicate), timeout
        )
    except asyncio.TimeoutError:
        return None


async def eventually(
    predicate: Callable[[Any], Awaitable[bool]] | Callable[[], Awaitable[bool]],
    iterator: AsyncIterator[Any] | None = None,
    timeout: float = 5,
) -> bool:
    """
    Checks if a predicate eventually becomes True within a timeout, optionally for events from an iterator.

    - If `iterator` is provided, it waits for an event from the iterator that makes `predicate` return True.
    - If `iterator` is None, it behaves like `wait_until`, periodically checking if `predicate` becomes True.

    **Important:** Synchronous functions passed as `predicate` will not be terminated when the timeout is reached.
    They can potentially block indefinitely.

    Args:
        predicate:
            - If `iterator` is provided: A function (regular or asynchronous) that takes an event
              from the iterator and returns True if the event satisfies the condition.
            - If `iterator` is None: A callable (regular function or coroutine)
              that returns a boolean value.
        iterator: An optional asynchronous iterator that produces events.
        timeout: The maximum time to wait, in seconds. Defaults to 5.

    Returns:
        - If `iterator` is provided: True if an event from the iterator makes `predicate`
          return True within the timeout, False otherwise.
        - If `iterator` is None: True if `predicate` returns
          True within the timeout, False otherwise.
    """
    if iterator is None:
        return await wait_until(predicate, timeout)

    return await _wait_for_event(predicate, iterator, timeout) is not None
