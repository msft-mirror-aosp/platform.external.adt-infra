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
import datetime
import logging
import time


class TimeFormatter(logging.Formatter):
    """
    A formatter used by the build system that:
    - Strips whitespace from the message.
    - Formats the time since the start of the build.
    """

    def __init__(self, fmt=None):
        """
        Args:
            fmt: The format string to use for the message.
        """
        self.start_time = time.time()
        super(TimeFormatter, self).__init__(fmt)

    def formatTime(self, record, datefmt=None):
        """
        Formats the time since the start of the build.

        Args:
            record: The log record.
            datefmt: The date format string to use.

        Returns:
            The formatted time string.
        """
        fmt = datefmt or "%H:%M:%S"
        creation_time = self.converter(record.created)
        time_delta = datetime.timedelta(seconds=record.created - self.start_time)
        hours = time_delta.seconds // 3600
        minutes = (time_delta.seconds % 3600) // 60
        seconds = time_delta.seconds % 60
        microseconds = time_delta.microseconds
        return f"{time.strftime(fmt or '%H:%M:%S', creation_time)} ({hours:02d}:{minutes:02d}:{seconds:02d}.{microseconds:06d})"

    def format(self, record):
        """
        Formats the log record.

        Args:
            record: The log record.

        Returns:
            The formatted log record.
        """
        record.msg = str(record.msg).strip()
        return super(TimeFormatter, self).format(record)
