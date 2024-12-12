# Copyright 2022 - The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the',  help='License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an',  help='AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import asyncio
import logging
import sys

from .time_formatter import TimeFormatter


class LogBelowLevel(logging.Filter):
    """A logging filter that only logs a line if it is below the given level."""

    def __init__(self, exclusive_maximum, name=""):
        super(LogBelowLevel, self).__init__(name)
        self.max_level = exclusive_maximum

    def filter(self, record):
        return True if record.levelno < self.max_level else False


def configure_logging(logging_level, split_to_stderr=False, log_path=None):
    """Configures the logging system to log at the given level

    Args:
        logging_level (int): A logging level, or number.
        split_to_stderr (bool): Whether to split warning and above messages to
            stderr.
    """
    logging_handler_out = logging.StreamHandler(sys.stdout)
    logging_handler_out.setLevel(logging.DEBUG)
    logging_handler_out.setFormatter(
        TimeFormatter("%(asctime)s  %(filename)s:%(lineno)d | %(message)s")
    )

    logging.root = logging.getLogger("root")
    logging.root.setLevel(logging_level)
    logging.root.addHandler(logging_handler_out)

    if log_path:
        logging_handler_file = logging.FileHandler(log_path)
        logging_handler_file.setLevel(logging.DEBUG)
        logging_handler_file.setFormatter(
            TimeFormatter("%(asctime)s  %(filename)s:%(lineno)d  | %(message)s")
        )
        logging.root.addHandler(logging_handler_file)

    # Filter warning and above to stderr
    if split_to_stderr:
        logging_handler_out.addFilter(LogBelowLevel(logging.WARNING))

        logging_handler_err = logging.StreamHandler(sys.stderr)
        logging_handler_err.setLevel(logging.WARNING)
        logging_handler_err.setFormatter(
            TimeFormatter("%(asctime)s  %(filename)s:%(lineno)d  EEE | %(message)s")
        )
        logging.root.addHandler(logging_handler_err)


class AsyncLogHandler:
    def __init__(
        self,
        logger=logging,
        std_out_logger=None,
        std_err_logger=None,
    ):
        """Initializes the LogHandler instance.

        Args:
            logger (logging.Logger, optional): The logger instance to use for logging.
                Defaults to the root logger.
            std_out_logger (function, optional): The function to use for logging the
                standard output of the subprocess. Defaults to `logger.info`.
            std_err_logger (function, optional): The function to use for logging the
                standard error of the subprocess. Defaults to `logger.error`.
        """
        self.logger = logger
        self.std_out_log = std_out_logger or self.logger.info
        self.std_err_log = std_err_logger or self.logger.error
        self.queue = asyncio.Queue(maxsize=64 * 1024)

    __FINISHED_SENTINEL__ = {"Finished": True}

    async def _log_stream(self, stream, log_function, queue):
        try:
            async for line in stream:
                try:
                    item = line.decode("utf-8").rstrip()
                except UnicodeDecodeError:
                    item = str(line)
                log_function(item)
                while queue.full():
                    queue.get_nowait()
                queue.put_nowait(item)
        except Exception as err:
            logging.error("log_stream encountered an error: %s", err)
        finally:
            while queue.full():
                queue.get_nowait()
            queue.put_nowait(AsyncLogHandler.__FINISHED_SENTINEL__)

    async def async_log(self, process):
        try:
            await asyncio.gather(
                self._log_stream(process.stdout, self.std_out_log, self.queue),
                self._log_stream(process.stderr, self.std_err_log, self.queue),
            )
        except asyncio.CancelledError:
            pass

    def __aiter__(self):
        return self

    async def __anext__(self):
        item = await self.queue.get()
        if item == AsyncLogHandler.__FINISHED_SENTINEL__:
            raise StopAsyncIteration
        return item

    def readlines(self) -> [str]:
        """
        Reads all log messages from the queue without blocking.

        Returns:
            [str]: A list of log messages from the queue.
        """
        lines = []
        try:
            while not self.queue.empty():
                item = self.queue.get_nowait()
                if item != AsyncLogHandler.__FINISHED_SENTINEL__:
                    lines.append(item)
        except Exception as e:
            logging.error(
                "Failure while attempting to read queue: %s", e, exc_info=True
            )
        finally:
            return lines

    async def read_all(self) -> str:
        lines = []
        while True:
            item = await self.queue.get()
            if item == AsyncLogHandler.__FINISHED_SENTINEL__:
                return "\n".join(lines)
            lines.append(item)
