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
import logging
import subprocess
import sys
import threading
from functools import partial
from queue import Empty, Queue

from .time_formatter import TimeFormatter


class LogBelowLevel(logging.Filter):
    """A logging filter that only logs a line if it is below the given level."""

    def __init__(self, exclusive_maximum, name=""):
        super(LogBelowLevel, self).__init__(name)
        self.max_level = exclusive_maximum

    def filter(self, record):
        return True if record.levelno < self.max_level else False


def configure_logging(logging_level, split_to_stderr=False):
    """Configures the logging system to log at the given level

    Args:
        logging_level (int): A logging level, or number.
        split_to_stderr (bool): Whether to split warning and above messages to
            stderr.
    """
    logging_handler_out = logging.StreamHandler(sys.stdout)
    logging_handler_out.setLevel(logging.DEBUG)
    logging_handler_out.setFormatter(TimeFormatter("%(asctime)s | %(message)s"))

    logging.root = logging.getLogger("root")
    logging.root.setLevel(logging_level)
    logging.root.addHandler(logging_handler_out)

    # Filter warning and above to stderr
    if split_to_stderr:
        logging_handler_out.addFilter(LogBelowLevel(logging.WARNING))

        logging_handler_err = logging.StreamHandler(sys.stderr)
        logging_handler_err.setLevel(logging.WARNING)
        logging_handler_err.setFormatter(TimeFormatter("%(asctime)s | %(message)s"))
        logging.root.addHandler(logging_handler_err)


class LogHandler:
    """A handler that logs lines from a process."""

    def __init__(
        self,
        logger=logging,
        std_out_logger=None,
        std_err_logger=None,
        on_exit=None,
        name=None,
    ):
        """Initializes the LogHandler instance.

        Args:
            logger (logging.Logger, optional): The logger instance to use for logging.
                Defaults to the root logger.
            std_out_logger (function, optional): The function to use for logging the
                standard output of the subprocess. Defaults to `logger.info`.
            std_err_logger (function, optional): The function to use for logging the
                standard error of the subprocess. Defaults to `logger.error`.
            on_exit (function, optional): The function to be called when the
                subprocess exits.
            name (str, optional): The name to be used for the logging threads.
        """
        self.logger = logger
        self.std_out_log = std_out_logger or self.logger.info
        self.std_err_log = std_err_logger or self.logger.error
        self.on_exit = on_exit
        self.name = name

    def with_std_out_logger(self, log_transform):
        """Changes the function used for logging the standard output.

        Args:
            log_transform (function): The new function to use for logging the
                standard output.

        Returns:
            LogHandler: The updated LogHandler instance.
        """
        self.std_out_log = log_transform
        return self

    def with_std_err_logger(self, log_transform):
        """Changes the function used for logging the standard error.

        Args:
            log_transform (function): The new function to use for logging the
                standard error.

        Returns:
            LogHandler: The updated LogHandler instance.
        """
        self.std_err_log = log_transform
        return self

    def _reader(self, pipe, logfn):
        """Log every line from the pipe, by calling the log function for every line.

        Args:
            pipe (file-like object): Pipe with lines in utf-8 encoding.
            logfn (callable): Function used to log a line.
        """
        try:
            for line in iter(pipe.readline, ""):
                logfn(line[:-1].strip())
        finally:
            if self.on_exit:
                self.on_exit()

    def start_log_proc(self, proc: subprocess.Popen):
        """Start logging the output of the subprocess in the background.

        The stdout will be logged to the `info` level and the stderr will be logged
        to the `error` level.

        Args:
            proc (subprocess.Popen): The subprocess to observe.
        """

        for args in [
            ["stdout", proc.stdout, self.std_out_log],
            ["stderr", proc.stderr, self.std_err_log],
        ]:
            logthread = threading.Thread(target=self._reader, args=args[1:])
            if self.name:
                logthread.name = f"{self.name}-{args[0]}"
            logthread.start()


class QueueLogHandler(LogHandler):
    """A LogHandler that logs info and error messages to a queue.

    This handler can be used to log output from a subprocess to a queue,
    which can then be observed and processed as needed.

    Attributes:
        queue (Queue): A queue for storing log messages.
        lock (threading.Lock): A lock for synchronizing access to the queue.
        timeout (int): The time in seconds to wait for a log message from the queue.
    """

    __FINISHED_SENTINEL__ = {"Finished": True}

    def __init__(
        self, logger=logging, timeout=60, thread_name=None, max_lines_to_log=512
    ):
        """
        Initializes a new `QueueLogHandler` object.

        Args:
            logger (logging.Logger, optional): A logger object from the `logging`
                module. Defaults to `logging`, which is the root logger.
            timeout (int, optional): A timeout in seconds for how long the logging
                thread should wait before attempting to log messages from the queue
                again. Defaults to 60 seconds.
            thread_name (str, optional): A string that will be used as the name of the
                logging thread. If not provided, it will default to the name of the
                `logger`.
            max_lines_to_log (int, optional): An integer that specifies the maximum
                number of log lines that can be stored in the queue. If max_lines_to_log
                is <= 0, the queue size is infinite. Defaults to 512.
        """
        self.queue = Queue(max_lines_to_log)
        self.lock = threading.Lock()
        self.timeout = timeout
        self.open_loggers = 2
        log_to_info = partial(self.log_to_queue, logger.info)
        log_to_err = partial(self.log_to_queue, logger.error)

        if not thread_name:
            thread_name = logger.name

        super().__init__(
            logger, log_to_info, log_to_err, on_exit=self.finished, name=thread_name
        )

    def __iter__(self):
        return self

    def __next__(self):
        try:
            result = self.queue.get(timeout=self.timeout)
            if result == self.__FINISHED_SENTINEL__:
                raise StopIteration
            return result
        except Empty:
            raise StopIteration

    def available(self) -> int:
        """
        Returns the number of log messages that are currently in the queue.

        Returns:
            int: The number of log messages in the queue.
        """
        return self.queue.qsize()

    def readlines(self) -> [str]:
        """
        Reads all log messages from the queue without blocking.

        Returns:
            [str]: A list of log messages from the queue.
        """
        lines = []
        while not self.queue.empty():
            elem = self.queue.get()
            if elem != self.__FINISHED_SENTINEL__:
                lines.append(elem)

        return lines

    def set_timeout(self, timeout: int):
        """
        Sets the timeout for reading log messages from the queue.

        Args:
            timeout (int): The timeout in seconds.
        """
        self.timeout = timeout

    def log_to_queue(self, logfn, line):
        """Logs the output of the given process."""
        with self.lock:
            if self.queue.full():
                self.queue.get_nowait()

            strip = line.strip()
            try:
                logfn(strip)
            except:
                pass
            self.queue.put_nowait(strip)

    def finished(self):
        """Adds a "finished" sentinel message to the end, exiting the iterator."""
        with self.lock:
            # We are observing two streams: stderr, stdout.. We should write out a
            # close marker once both are finished!
            self.open_loggers = self.open_loggers - 1
            if self.open_loggers == 0:
                if self.queue.full():
                    self.queue.get_nowait()

                self.queue.put_nowait(QueueLogHandler.__FINISHED_SENTINEL__)
