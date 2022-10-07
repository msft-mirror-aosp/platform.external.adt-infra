# Copyright 2022 - The Android Open Source Project
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
import os
import subprocess
from pathlib import Path
from shutil import which

from emu.adb.stream import AdbStream


class Adb(object):
    def __init__(self, emulator: str, adb: Path) -> None:
        """Create an adb object that runs against the given emulator

        Args:
            emulator (str): Name of the emulator, this will be passed in as the -s parameter
            adb (Path): path to the adb executable.
        """
        self.name = emulator
        self.adb_binary = which(adb)

    def start_server(self) -> None:
        """Starts the adb server."""
        my_env = os.environ.copy()
        my_env["ADB_TRACE"] = "all"
        subprocess.run(
            [self.adb_binary, "start-server"],
            env=my_env,
            timeout=10,
        )

    def run(self, cmd: list[str], timeout: int = 10) -> str:
        """Runs the given command on the emulator

        Args:
            cmd (list[str]): Command to execute
            timeout (int, optional): Timeout. Defaults to 10s.

        Returns:
            str: Result of the adb invocation.
        """
        logging.info("adb -s %s %s", self.name, " ".join(cmd))
        cmd = subprocess.check_output(
            [self.adb_binary, "-s", self.name] + cmd, timeout=timeout
        )
        logging.debug("result: %s", cmd)
        return cmd

    def stream(self, cmd: list[str]) -> AdbStream:
        """Runs the given command on the emulator

        You usually want to use this like this:

        with adb.stream(["logcat", "-s", "aemu"]) as stream:
            for line in iter(stream.get, None):
                print(line)

        Args:
            cmd (list[str]): Command to execute

        Returns:
            AdbStream: An observable stream with results from adb
        """
        logging.info("adb -s %s %s", self.name, " ".join(cmd))
        return AdbStream(self.adb_binary, self.name, cmd)
