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
from pathlib import Path
import platform
from shutil import which

from emu.adb.stream import AdbStream, AdbLogcatStream
from emu.process.command import Command


class Adb(object):
    def __init__(self, avd_id: str, emulator: str, adb: Path) -> None:
        """Create an adb object that runs against the given emulator

        Args:
            emulator (str): Name of the emulator, this will be passed in as the -s parameter
            adb (Path): path to the adb executable.
        """
        self.name = emulator
        self.avd_id = avd_id
        self.logger = logging.getLogger(f"{avd_id}-adb")

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
        if (
            logging.getLogger().isEnabledFor(logging.DEBUG)
            and "ADB_TRACE" not in my_env
        ):
            my_env["ADB_TRACE"] = "all"
        return my_env

    def start_server(self) -> None:
        """Starts the adb server."""
        cmd = Command([self.adb_binary, "start-server"]).with_environment(
            self._enable_tracing()
        )
        cmd.run_until_finished(timeout=10)

    def run(self, cmd: list[str], timeout: int = 10) -> str:
        """Runs the given command on the emulator

        Args:
            cmd (list[str]): Command to execute
            timeout (int, optional): Timeout. Defaults to 10s.

        Returns:
            str: Result of the adb invocation.

        Raises:
            subprocess.CalledProcessError
        """
        self.logger.info("adb -s %s %s", self.name, " ".join(cmd))
        command = Command([self.adb_binary, "-s", self.name] + cmd).with_environment(
            self._enable_tracing()
        )
        _, result = command.run_until_finished(timeout)
        return "\n".join(result)

    def stream(self, cmd: list[str], timeout: int = 2) -> AdbStream:
        """Runs the given command on the emulator

        You usually want to use this like this:

        with adb.stream(["logcat", "-s", "aemu"]) as stream:
            for line in stream
                print(line)

        Args:
            cmd (list[str]): Command to execute
            timeout (int): Timeout in seconds for the iterator. The
                 iterator will exit if adb does not produce output in
                 the given time.

        Returns:
            AdbStream: An observable stream with results from adb
        """
        self.logger.info("adb -s %s %s", self.name, " ".join(cmd))
        return AdbStream(self.logger, self.adb_binary, self.name, cmd)

    def logcat(self, clear: bool = True, tag: str = None) -> AdbLogcatStream:
        """Obtains the current logcat stream

        Args:
            tag (str): Tag to filter by
            clear (bool, optional): Clear the logcat buffer. Defaults to True.

        Returns:
            AdbLogcatStream: _description_
        """
        return AdbLogcatStream(
            logging.getLogger(f"{self.avd_id}-cat"),
            self.adb_binary,
            self.name,
            tag,
            clear,
        )
