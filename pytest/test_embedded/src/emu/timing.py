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
from typing import AsyncIterator


def true():
    return True


async def wait_until(predicate, timeout=15, pre_requisite=true, hz=2):
    """
    Wait until the given predicate function returns True, or until the timeout
    expires.

    The predicate function is called repeatedly until it returns True
    or the timeout expires.

    Args:
        predicate (function): A function that returns a boolean value. This
            function will be called repeatedly until it returns True or the
            timeout expires.
        pre_requisite (function): A function that returns a boolean value. This
            function will be called repeatedly. If this function returns False
            is assumed that we no longer need to call wait_until as the predicate
            can never be fullfilled. (i.e. the pre requisite for the predicate is not met.)
        timeout (int): The maximum number of seconds to wait for the predicate
            function to return True. Defaults to 10 seconds.
        hz (int): Frequency of how often we want to execute the predicate.

    Returns:
        bool: True if the predicate function returns True before the timeout
            expires, otherwise False.
    """
    start = time.time()
    end = time.time() + timeout

    if asyncio.iscoroutinefunction(predicate):
        predicate_state = await predicate()
    else:
        predicate_state = predicate()
    if asyncio.iscoroutinefunction(pre_requisite):
        pre_requisite_state = await pre_requisite()
    else:
        pre_requisite_state = pre_requisite()

    while not predicate_state and (time.time() < end and pre_requisite_state):
        await asyncio.sleep(1 / hz)
        if asyncio.iscoroutinefunction(predicate):
            predicate_state = await predicate()
        else:
            predicate_state = predicate()
        if asyncio.iscoroutinefunction(pre_requisite):
            pre_requisite_state = await pre_requisite()
        else:
            pre_requisite_state = pre_requisite()

    if time.time() >= end:
        logging.info("Operation timed out after %s seconds", time.time() - start)
    return predicate_state and pre_requisite_state


async def _eventually_async_iter(queue: AsyncIterator, predicate):
    """Special handler for queue logs, which are aysnc iterators. We need to special case those iterators."""
    async for event in queue:
        if asyncio.iscoroutinefunction(predicate):
            predicate_state = await predicate(event)
        else:
            predicate_state = predicate(event)

        if predicate_state:
            return event

    # We timed out.
    return None


async def _wait_for_event(predicate, iterator=None, timeout=5):
    """
    Returns the event for which the given `predicate` function returns True for any event
    produced by the given `iterator` within the given `timeout` period.
    Returns None if no event is produced by the iterator within the timeout period.

    Args:
        iterator: An iterable object that produces events.
        predicate: A function that takes an event produced by `iterator` and
                   returns True if the event satisfies some condition.
        timeout: An optional float representing the number of seconds to wait
                 before timing out. Default is 5 seconds.

    Returns:
        The event for which the given `predicate` function returns True. 'None'
        if none of the events satisfies `predicate` before timing out.
    """
    # We need to special case queue handlers as they use their own thread
    # and will handle timeouts themselves.
    try:
        return await asyncio.wait_for(
            _eventually_async_iter(iterator, predicate), timeout
        )
    except asyncio.TimeoutError:
        return None


async def eventually(predicate, iterator=None, timeout=5):
    """
    Returns True if the given `predicate` function returns True for any event
    produced by the given `iterator` within the given `timeout` period.
    Returns False if no event is produced by the iterator within the timeout period.

    Args:
        iterator: An iterable object that produces events.
        predicate: A function that takes an event produced by `iterator` and
                   returns True if the event satisfies some condition.
        timeout: An optional float representing the number of seconds to wait
                 before timing out. Default is 5 seconds.

    Returns:
        True if the `predicate` function returns True for any event produced
        by `iterator` within the given `timeout` period. False otherwise.
    """

    if iterator is None:
        try:
            return await wait_until(predicate, timeout)
        except asyncio.TimeoutError:
            return False

    return await _wait_for_event(predicate, iterator, timeout) is not None
