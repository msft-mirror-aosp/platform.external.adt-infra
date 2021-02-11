#!/usr/bin/env python
#
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
import subprocess

from aemu.proto.emulator_controller_pb2 import LogMessage
from emu.utils import run


class Logcat(object):
    """ Retrieves all the logcat entries. """

    def __init__(self, emu_grpc_stub):
        self.grpc = emu_grpc_stub
        self.logs = list()
        self.start = 0

    def _get_logcat(self):
        logcat = LogMessage(start=self.start, sort=1)
        response = self.grpc.getLogcat(logcat)
        self.start = response.__next__
        return response.entries

    def reset(self):
        """Reset the starting point from which we retrieve logs."""
        self.start = 0

    # // A parsed logcat entry.
    # message LogcatEntry {
    #   // The possible log levels.
    #   enum LogLevel {
    #     UNKNOWN = 0;
    #     DEFAULT = 1;
    #     VERBOSE = 2;
    #     DEBUG = 3;
    #     INFO = 4;
    #     WARN = 5;
    #     ERR = 6;
    #     FATAL = 7;
    #     SILENT = 8;
    #   };

    #   // A Unix timestamps in  milliseconds (The number of milliseconds that
    #   // have elapsed since January 1, 1970 (midnight UTC/GMT), not counting
    #   // leap seconds)
    #   uint64 timestamp = 1;

    #   // Process id.
    #   uint32 pid = 2;

    #   // Thread id.
    #   uint32 tid = 3;
    #   LogLevel level = 4;
    #   string tag = 5;
    #   string msg = 6;
    # }
    def log(self, by_tag=None):
        """Retrieves the log from the last timestamp, filtering by_tag if needed."""
        log = self._get_logcat()
        return [x for x in log if not by_tag or by_tag == x.tag]


class AdbStream(object):
    """Streaming adb command that can be observed"""

    def __init__(self, adb_binary, emulator_name, cmd):
        self._queue = None
        self.proc = None
        self.cmd = [adb_binary, "-s", emulator_name] + cmd

    def __enter__(self):
        self.proc, self._queue = run(self.cmd)
        return self._queue

    def __exit__(self, exc_type, exc_val, exc_tb):
        # We left scope, cancel from the client side.
        if self.proc:
            self.proc.send_signal(9)


class AdbLogcatStream(AdbStream):
    """
    Logcat stream that can be used to observe logcat
    """

    def __init__(self, adb_binary, emulator_name, tag, clear):
        super(AdbLogcatStream).__init__(adb_binary, emulator_name, ["logcat"])
        if clear:
            self.clear()

        if tag:
            self.cmd += ["-s", tag]

    def clear(self):
        logging.info("Clearing log")
        subprocess.check_call(self.cmd + ["-c"])
