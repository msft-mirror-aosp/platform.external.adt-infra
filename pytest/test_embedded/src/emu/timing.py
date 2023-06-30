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
import logging
import time
import threading
import ctypes

from iterators import TimeoutIterator

from emu.logging.log_handler import QueueLogHandler


def wait_until(predicate, timeout=15, pre_requisite=lambda: True, hz=2):
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
    end = time.time() + timeout
    while not predicate() and (time.time() < end and pre_requisite()):
        time.sleep(1 / hz)

    return pre_requisite() and predicate()


def _eventually_queue(queue: QueueLogHandler, predicate, timeout=10):
    """Special handler for queue logs, which are aysnc iterators. We need to special case those iterators."""

    end = time.time() + timeout

    # Timeout (i.e. stop the queue), if we have no events before the timeout
    queue.set_timeout(timeout)
    for event in queue:

        # Check the case where we had events, but not one matching the predicate
        if time.time() > end:
            return None

        # Check our predicate.
        if predicate(event):
            return event

    # We timed out.
    return None


def wait_for_event(predicate, iterator=None, timeout=5):
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
    if isinstance(iterator, QueueLogHandler):
        return _eventually_queue(iterator, predicate, timeout)

    end = time.time() + timeout

    # Every 0.5 sec we check for a timeout.
    logging.info("Waiting for %s", iterator)
    timed_iterator = TimeoutIterator(iterator, timeout=0.5)
    for event in timed_iterator:
        if time.time() > end:
            return None

        if event == timed_iterator.get_sentinel():
            continue

        if predicate(event):
            return event

    return None


def eventually(predicate, iterator=None, timeout=5):
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
        return wait_until(predicate, timeout)

    return wait_for_event(predicate, iterator, timeout) != None


class TimeoutTrigger:
    def __init__(self, callback, timeout: int = 60):
        self.timer = threading.Timer(timeout, callback)
        self.timer.name = f"Timeout watch thread ({timeout})"

    def cancel(self):
        """
        Cancels the timer and waits for the timer thread to finish.
        """
        self.timer.cancel()
        self.timer.join()

    def __enter__(self):
        """Enters the context and starts the timer."""
        self.timer.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exits the context and cancels the timer."""
        logging.debug("Exit %s, %s", exc_type, exc_val)
        self.cancel()


class TimeoutExceptionTrigger(TimeoutTrigger):
    """
    A subclass of TimeoutTrigger that raises a TimeoutError exception in
    the context of the target thread.

    Note: This expects the code not to block! For example it will not work
    if the code block is using time.sleep(timeout), or is running a subprocess.

    Parameters:
        timeout: int
            The timeout duration in seconds. Default is 60 seconds.
    """

    def __init__(self, timeout: int = 60):
        super().__init__(self._handler, timeout)
        self.target_tid = 0

    def _handler(self):
        """Raises a TimeoutError exception in the context of the target thread."""
        logging.debug("Raising an exception in %s.", self.target_tid)
        ret = ctypes.pythonapi.PyThreadState_SetAsyncExc(
            ctypes.c_long(self.target_tid), ctypes.py_object(TimeoutError)
        )
        if ret > 1:
            # Oh oh.. Python is now in a bad state!
            ctypes.pythonapi.PyThreadState_SetAsyncExc(self.target_tid, None)
            raise SystemError("PyThreadState_SetAsyncExc failed, Timout Class failure!")

    def __enter__(self):
        """Enters the context and starts the timer."""
        self.target_tid = threading.current_thread().ident
        return super().__enter__()
