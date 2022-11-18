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
import platform
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

        if not adb.exists() and platform.system() == "Windows":
            adb = adb.with_suffix(".exe")

        self.adb_binary = which(adb)

    def _enable_tracing(self) -> dict[str, str]:
        """Returns a copy of the default environment with ADB_TRACE
        set to all if it not yet set

        Returns:
            dict[str, str]: The environment that can be passed to subprocess
        """
        my_env = os.environ.copy()
        if "ADB_TRACE" not in my_env:
            my_env["ADB_TRACE"] = "all"
        return my_env

    def start_server(self) -> None:
        """Starts the adb server."""
        subprocess.run(
            [self.adb_binary, "start-server"],
            env=self._enable_tracing(),
            timeout=10,
            check=False,
        )

    def run(self, cmd: list[str], timeout: int = 30) -> str:
        """Runs the given command on the emulator

        Args:
            cmd (list[str]): Command to execute
            timeout (int, optional): Timeout. Defaults to 30s.

        Returns:
            str: Result of the adb invocation.
        """
        logging.info("adb -s %s %s", self.name, " ".join(cmd))
        cmd = subprocess.check_output(
            [self.adb_binary, "-s", self.name] + cmd,
            env=self._enable_tracing(),
            timeout=timeout,
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
