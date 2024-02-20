# Copyright 2024 - The Android Open Source Project
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
import re
import time
from datetime import datetime

logcat_pattern = (
    r"^(?P<date>\d{2}-\d{2})"  # Match date (MM-DD)
    r"\s+(?P<time>\d{2}:\d{2}:\d{2}.\d{3})"  # Match time (HH:MM:SS.mmm)
    r"\s+(?P<pid>\d+)"  # Match process ID
    r"\s+(?P<tid>\d+)"  # Match thread ID
    r"\s+(?P<level>[VDIWEF])"  # Match log level
    r"\s+(?P<tag>[\w.]+):"  # Match tag
    r"\s+(?P<message>.*)$"  # Match the rest as the message
)
LOGCAT_LINE = re.compile(logcat_pattern)


def parse_logcat(lines: str):
    """
    Parses a the output of logcat and returns a list of parsed log entries.

    Args:
        lines: The output of logcat.

    Returns:
       A list of dictionaries, where each dictionary represents a parsed log entry.
       The dictionary contains the following keys:
           * date: The date of the log entry (MM-DD format).
           * time: The time of the log entry (HH:MM:SS.mmm format).
           * pid: The process ID.
           * tid: The thread ID.
           * level: The log level (V, D, I, W, E, or F).
           * tag: The log tag.
           * message: The log message.
           * ts: A datetime object representing the timestamp of the log entry.
    """
    parsed = []
    time_format = "%H:%M:%S.%f"  # Matches hours, minutes, seconds, milliseconds
    for line in lines.splitlines():
        match = LOGCAT_LINE.match(line)
        if match:
            data = match.groupdict()
            data["ts"] = datetime.strptime(data["time"], time_format)
            parsed.append(data)
    return parsed
