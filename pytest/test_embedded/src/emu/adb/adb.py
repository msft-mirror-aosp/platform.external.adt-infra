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
import platform
import subprocess
from pathlib import Path

from ppadb.client import Client as AdbClient
from ppadb.device import Device

from emu.adb.stream import AdbStream


class Adb:
    def __init__(self, avd_id: str, emulator: str, adb: Path) -> None:
        """Create an adb object that runs against the given emulator

        Args:
            emulator (str): Name of the emulator, this will be passed in as the -s parameter
            adb (Path): path to the adb executable.
        """
        self.name = emulator
        self.avd_id = avd_id
        self.logger = logging.getLogger(f"{avd_id}-adb")
        self.client: AdbClient = AdbClient()
        self.device: Device = self.client.device(emulator)

        if not adb.exists() and platform.system() == "Windows":
            adb = adb.with_suffix(".exe")

        self.adb_binary = adb.absolute()


    def start_server(self) -> None:
        """Starts the adb server."""
        subprocess.check_call([self.adb_binary, "start-server"])

    def is_installed(self, package: str) -> bool:
        """True if the given package is installed."""
        return self.device.is_installed(package)

    def install(self, apk: Path) -> None:
        """Install the given apk on the device."""
        self.device.install(apk)

    def pull(self, src: str, dest: str) -> None:
        """Pull the src of the device to the dest."""
        self.device.pull(src, dest)

    def push(self, src: str, dest: str) -> None:
        """Pushes the src to the dest on the device."""
        self.device.push(src, dest)

    def shell(self, cmd: str, timeout: int = 10) -> str:
        """Runs the given shell command on the emulator

        Args:
            cmd (str): Command to execute
            timeout (int, optional): Timeout. Defaults to 10s.

        Returns:
            str: Result of the shell command
        """
        self.logger.info("shell (%ss): %s", timeout, cmd)
        res = self.device.shell(cmd, timeout=timeout)
        self.logger.info("shell (result): %s", res)
        return res

    def run(self, cmd: list[str], timeout: int = 10) -> str:
        """Runs the given command on the emulator

        Please do not use this, it spawns an adb process.

        Args:
            cmd (list[str]): Command to execute
            timeout (int, optional): Timeout. Defaults to 10s.

        Returns:
            str: Result of the adb invocation.

        Raises:
            subprocess.CalledProcessError
        """
        self.logger.info("adb -s %s %s", self.name, " ".join(cmd))
        return subprocess.check_output(
            [self.adb_binary, "-s", self.name] + cmd, encoding="utf-8", timeout=timeout
        )

    def stream(self, cmd: str, timeout: int = 10) -> AdbStream:
        """Runs the given command on the emulator asynchronously

        You usually want to use this like this:

        with adb.stream("some shell cmd") as stream:
            # do some things.
            for line in stream
                print(line)

        Args:
            cmd (str): Command to execute
            timeout (int): Timeout in seconds for the iterator. The
                 iterator will exit if shell cmd does not produce output in
                 the given time.

        Returns:
            AdbStream: An observable stream with results from adb
        """
        return AdbStream(self.logger, self.device, cmd=cmd, timeout=timeout)

    def logcat(self, clear: bool = False, tag: str = None, timeout=2) -> AdbStream:
        """Obtains the current logcat stream

        Args:
            tag (str): Tag to filter by
            clear (bool, optional): Clear the logcat buffer. Defaults to True.
            timeout (int, optional): Timeout in seconds, happens if no logcat line
                          is produced with the given time

        Returns:
            LogcatStream: An iterator with logcat lines
        """
        if clear:
            self.shell("logcat -c")

        cmd = "logcat"
        if tag:
            cmd += f" -s {tag}"

        return AdbStream(
            logging.getLogger(f"{self.avd_id}-cat"),
            self.device,
            cmd=cmd,
            timeout=timeout,
        )
