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
import threading
import time

from ppadb.connection import Connection
from ppadb.device import Device

from emu.logging.log_handler import QueueLogHandler


class BufferedLineReader:
    """
    A buffered line reader for a `Connection` object.


    Yields:
        str: The next line of data from the connection.
    """

    def __init__(self, connection: Connection, logger: logging.Logger):
        """
        Initialize the `BufferedLineReader` object.

        Args:
            connection (Connection): The connection to read from.
            logger (logging.Logger): The logger to use for logging errors.
        """
        self.connection = connection
        self.buffer = b""
        self.buffer_size = 4096
        self.logger = logger

    def _read(self):
        while True:
            try:
                return self.connection.read(self.buffer_size)
            except TimeoutError:
                # Eventually someone will close the socker, which will result
                # in either us returning no data, or raising an OSError
                logging.debug("Ignoring read timeout from open socket.")

    def __iter__(self):
        """
        Iterate over the lines of data from the connection.

        Yields:
            str: The next line of data from the connection.
        """
        try:
            while True:
                data = self._read()
                if not data:
                    break

                self.buffer += data
                while True:
                    index = self.buffer.find(b"\n")
                    if index == -1:
                        break

                    yield self.buffer[:index].decode("utf-8")
                    self.buffer = self.buffer[index + 1 :]

        except Exception as err:
            self.logger.error("Finished BufferedLineReader due to %s", err)


class AdbStream:
    """Stream with emulator shell"""

    def __init__(
        self,
        logger: logging.Logger,
        device: Device,
        cmd: str,
        timeout=10,
    ):
        """Create a log stream iterator.

        Args:
            logger: The logger used to log information
            device (Device):
            cmd: The shell command to execute
            timeout: Timeout used on the stream, the maximum amount of time the stream will block
        """
        self.device = device
        self.queue = QueueLogHandler(logger, timeout=timeout)
        self.logger = logger
        self.connection: Connection = (
            None  # This will be obtained from the shell read callback
        )
        self.cmd = cmd
        self.thread = None

    def __enter__(self):
        self.thread = threading.Thread(target=self._execute_shell_cmd)
        self.thread.start()
        return self.queue

    def __exit__(self, exc_type, exc_val, exc_tb):
        # We left scope, cancel the adb shell reader, and wait
        # for thread completion.
        if self.connection:
            # Closing the connection, this will exit the BufferedLineReader
            # iterator
            self.logger.info("Closing connection to emulator.")
            self.connection.close()

        # Now join the thread, so we do not have any unexpected dangling
        # connections.
        self.logger.info("Waiting for _execute_shell_cmd completion.")
        start = time.time()
        self.thread.join(timeout=180)

        if self.thread.is_alive():
            self.logger.warning(
                "_execute_shell_cmd never completed, ignoring thread after %s seconds",
                time.time() - start,
            )
        else:
            self.logger.info(
                "_execute_shell_cmd completed after %s seconds", time.time() - start
            )

    def _execute_shell_cmd(self):
        """Execute the shell command and read the output in the callback."""
        self.logger.info("shell (%ss): %s", 1, self.cmd)
        self.device.shell(self.cmd, self._read_callback, timeout=1)

    def _read_callback(self, connection):
        """
        Read the output from the connection and log it.

        Args:
            connection (Connection): The connection to read from.
        """
        self.connection = connection
        buffered_reader = BufferedLineReader(self.connection, self.logger)

        for line in buffered_reader:
            self.logger.info(line)
            self.queue.log_to_queue(self.logger, line)
