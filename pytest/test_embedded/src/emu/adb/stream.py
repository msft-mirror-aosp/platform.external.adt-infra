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
from emu.process.command import Command
from emu.logging.log_handler import QueueLogHandler


class AdbStream(object):
    """Streaming adb command that can be observed"""

    def __init__(
        self,
        logger: logging.Logger,
        adb_binary: str,
        emulator_name: str,
        cmd: list[str],
        timeout: int = 60,
    ):
        """Run an adb command, streaming the results as queue.
        You usually want to use this like this:


        with AdbStream("adb.exe", "emulator-5554", ["logcat", "-s", "aemu"]) as stream:
            for line in iter(stream.get, None):
                print(line)

        Args:
            logger: The logger used to log information
            adb_binary (str): Adb executable.
            emulator_name (str): Name of the emulator, passed as -s to adb
            cmd (list[str]): Command to execute.
            timeout (int): Timeout for the queue iterator (defaults to 60 seconds)
        """
        self.proc = None
        self.logger = logger
        self.cmd = [adb_binary, "-s", emulator_name] + cmd
        self.handler = QueueLogHandler(self.logger, timeout)

    def start(self):
        self.proc = Command(self.cmd).with_log_handler(self.handler).run()

    def stop(self):
        if self.proc:
            self.proc.terminate()

    def __enter__(self):
        self.start()
        return self.handler

    def __exit__(self, exc_type, exc_val, exc_tb):
        # We left scope, cancel from the client side.
        self.stop()


class AdbLogcatStream(AdbStream):
    """Stream with emulator logcat"""

    def __init__(
        self,
        logger: logging.Logger,
        adb_binary: str,
        emulator_name: str,
        timeout: int,
        tag: str,
        clear: bool,
    ):
        """Create a log stream

        Args:
            logger: The logger used to log information
            adb_binary (str): Adb executable.
            emulator_name (str): Name of the emulator, passed as -s to adb
            tag (str): Tag to filter by
            clear (bool): true if logcat should be flushed first
        """
        super().__init__(logger, adb_binary, emulator_name, ["logcat"], timeout)
        if clear:
            self.clear()

        if tag:
            self.cmd += ["-s", tag]

    def clear(self) -> None:
        """Clear logcat"""
        self.logger.info("Clearing logcat log")
        subprocess.check_call(self.cmd + ["-c"])
