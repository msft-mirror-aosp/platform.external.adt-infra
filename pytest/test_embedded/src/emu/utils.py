# Copyright 2020 - The Android Open Source Project
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
import platform
import time
from pathlib import Path
from queue import Queue
import threading


def wait_until(predicate, timeout=10, hz=2):
    """
    Wait until the given predicate function returns True, or until the timeout
    expires.

    The predicate function is called repeatedly until it returns True
    or the timeout expires.

    Args:
        predicate (function): A function that returns a boolean value. This
            function will be called repeatedly until it returns True or the
            timeout expires.
        timeout (int): The maximum number of seconds to wait for the predicate
            function to return True. Defaults to 10 seconds.
        hz (int): Frequency of how often we want to execute the predicate.

    Returns:
        bool: True if the predicate function returns True before the timeout
            expires, otherwise False.
    """
    end = time.time() + timeout
    while not predicate() and time.time() < end:
        time.sleep(1 / hz)

    return predicate()


def system_cpu() -> str:
    """Returns the native system cpu

    Returns:
        str: The native system cpu, either x86_64|arm64
    """
    aarch = platform.machine()
    if aarch == "x86_64":
        # Ok maybe python is running under rosetta, if so the uname.version
        # will have have something along RELEASE_ARM64_T6000 in it
        uname = platform.uname()
        if "ARM64" in uname.version and uname.system == "Darwin":
            return "arm64"

    # We consider AMD64 to be compatible with x86_64
    if aarch == "AMD64":
        aarch = "x86_64"

    return aarch


class LogObserver:
    """A LogObserver allows you to observe an active log file."""

    def __init__(self, logfile: Path):
        """Attaches a log queue to a file."""
        self.queue = Queue()
        self.lock = threading.Lock()
        self.tail = open(logfile, "rb")
        self.thread = threading.Thread(target=self.__tail_reader__)
        self.thread.start()

    def __tail_reader__(self):
        try:
            while not self.tail.closed:
                curr_position = self.tail.tell()
                line = self.tail.readline()
                if not line:
                    self.tail.seek(curr_position)
                    time.sleep(0.1)
                else:
                    self.log_to_queue(line.decode("utf-8"))
        except Exception as err:
            logging.warning(
                "Encountered error while accessing file %s", err, exc_info=err
            )

    def log_to_queue(self, line):
        """Logs the output of the given process."""
        with self.lock:
            if self.queue.full():
                self.queue.get_nowait()

            strip = line.strip()
            self.queue.put_nowait(strip)

    def __enter__(self):
        return self.queue

    def __exit__(self, exc_type, exc_val, exc_tb):
        # We left scope, cancel from the client side.
        if self.tail:
            self.tail.close()

    def __del__(self):
        if self.tail:
            self.tail.close()
        if (
            self.thread
            and self.thread.native_id != threading.current_thread().native_id
        ):
            self.thread.join()
