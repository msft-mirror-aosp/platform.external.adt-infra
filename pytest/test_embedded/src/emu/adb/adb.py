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
import asyncio
import logging
import platform
import time
from pathlib import Path

from emu.emulator_exceptions import EmulatorDiedException
from emu.logging.logcat_parser import parse_logcat
from emu.logging.log_handler import create_file_logger
from emu.process.command import Command
from emu.process.command_stream import AsyncCommandStream
from emu.timing import eventually


class Adb:
    """A class representing an ADB client for communication with an Android emulator.

    Attributes:
        name (str): Name of the emulator.
        avd_id (str): Identifier of the Android Virtual Device (AVD) associated with the emulator.
        logger (Logger): Logging object to handle logs for this ADB instance.
        adb_binary (Path): Path to the ADB executable.

    Args:
        avd_id (str): Identifier of the Android Virtual Device (AVD) associated with the emulator.
        emulator (str): Name of the emulator, this will be passed in as the -s parameter.
        adb (Path): Path to the adb executable.
    """

    def __init__(self, avd_id: str, name: str, adb: Path, emu=None) -> None:
        """Create an adb object that runs against the given emulator

        Args:
            name (str): Name of the emulator, this will be passed in as the -s parameter when making
                            calls with the adb executable
            adb (Path): path to the adb executable.
        """

        self.name = name
        self.avd_id = avd_id
        self.logger = logging.getLogger(f"{emu.log_id}-adb")
        self.emulator = emu

        if not adb.exists() and platform.system() == "Windows":
            adb = adb.with_suffix(".exe")
        self.adb_binary = adb.absolute()

    async def restart(self) -> None:
        """Restarts the adb server."""

        await Command([self.adb_binary, "kill-server"]).run_until_finished()
        await asyncio.sleep(1)
        await Command([self.adb_binary, "start-server"]).run_until_finished()
        await asyncio.sleep(1)

    async def is_installed(self, package: str) -> bool:
        """Check if the given package is installed on the device.

        Args:
            package (str): The name of the package to check.

        Returns:
            bool: True if the package is installed, False otherwise.
        """

        return "package:" in await self.shell(f"pm path {package}")

    async def install(self, apk: Path) -> None:
        """Install the given apk on the device.

        Args:
            apk (Path): The path to the APK file to be installed.
        """

        await self._check_adb_and_raise()
        await Command(
            [self.adb_binary, "-s", self.name, "install", "-r", "-g", apk]
        ).run_until_finished()

    async def pull(self, src: str, dest: str) -> None:
        """Pull a file from the device to the host.

        Args:
            src (str): The path of the file on the device.
            dest (str): The destination path on the host.
        """

        await self._check_adb_and_raise()
        await Command(
            [self.adb_binary, "-s", self.name, "pull", src, dest]
        ).run_until_finished()

    async def push(self, src: str, dest: str) -> None:
        """Push a file from the host to the device.

        Args:
            src (str): The path of the file on the host.
            dest (str): The destination path on the device.
        """
        cmd_array = [self.adb_binary, "-s", self.name, "push", src, dest]
        await self._check_adb_and_raise()
        await Command(cmd_array).run_until_finished()

    async def wait_boot_complete(self, timeout=60, timedelta=1):
        """
        Asynchronously waits for boot completion (up to a timeout) by polling a shell command.

        :param timeout: Maximum time to wait in seconds (default: 60).
        :param timedelta: Interval between polling attempts in seconds (default: 1).
        """

        cmd = "getprop sys.boot_completed"
        end_time = time.time() + timeout

        while True:
            try:
                # Execute shell command asynchronously
                result = await self.shell(cmd)
                if result.strip() == "1":
                    return True

            except RuntimeError as e:
                logging.error(e)

            # Check for timeout
            if time.time() > end_time:
                raise TimeoutError()

            # Wait before next check (asynchronously)
            if timedelta > 0:
                await asyncio.sleep(timedelta)

    async def online(self, try_restart=True) -> bool:
        """Check if the device is connected and accessible.

        This state indicates that the device is ready for
        communication with ADB commands.

        Args:
            try_restart (bool): If true, we will try to restart the adb
            server once, if the device is not online.

        Returns:
            bool: True if the device is online, False otherwise.
        """

        (exit_code, output) = await Command(
            [self.adb_binary, "devices"]
        ).run_until_finished()
        splits = " ".join(output).split()
        is_online = self.name in splits and "device" in splits

        if not is_online and try_restart:
            await self.restart()
            return await self.online(False)

        return is_online

    async def shell(self, cmd: str, timeout: int = 10) -> str:
        """Runs the given shell command on the emulator

        Args:
            cmd (str): Command to execute
            timeout (int, optional): Timeout. Defaults to 10s.
        Returns:
            str: Result of the shell command
        """

        await self._check_adb_and_raise()
        (exit_code, output) = await Command(
            [self.adb_binary, "-s", self.name, "shell", cmd]
        ).run_until_finished(timeout)
        return "\n".join(output)

    async def exec_out(self, cmd: str, timeout: int = 10) -> str:
        """Runs the given command using exec-out on the emulator

        Args:
            cmd (str): Command to execute
            timeout (int, optional): Timeout. Defaults to 10s.
        Returns:
            str: Result of the shell command
        """

        await self._check_adb_and_raise()
        (exit_code, output) = await Command(
            [self.adb_binary, "-s", self.name, "exec-out", cmd]
        ).run_until_finished(timeout)
        return "\n".join(output)

    async def run(self, cmd: list[str], timeout: int = 10) -> (int, [str]):
        """Runs the given command on the emulator

        Args:
            cmd (list[str]): Command to execute
            timeout (int, optional): Timeout. Defaults to 10s.

        Returns:
            str: Result of the adb invocation.

        Raises:
            subprocess.CalledProcessError
        """

        await self._check_adb_and_raise()
        return await Command(
            [self.adb_binary, "-s", self.name] + cmd
        ).run_until_finished(timeout)

    async def clear_logcat(self):
        """Clears the Android device's Logcat buffer and waits for a new log line to appear.

        Returns:
            True if the Logcat was successfully cleared, False if a timeout occurred (3s).
        """

        await self._check_adb_and_raise()
        lines = await self.shell("logcat -d | tail")
        old = parse_logcat(lines)
        await self.shell("logcat -c")

        async def logcat_cleared():
            """
            Checks if the logcat has been cleared by comparing timestamps.

            Returns:
                True if the logcat has a new entry with a later timestamp, False otherwise.
            """

            lines = await self.shell("logcat -d | tail")
            now = parse_logcat(lines)
            if len(now) == 0:
                return False
            if len(old) == 0:
                return True
            return now[0]["ts"] > old[0]["ts"]

        return await eventually(logcat_cleared, timeout=3)

    async def _check_adb_and_raise(self) -> None:
        """Checks if the device is available and online. Raises if not.

        Note:
            This method is for internal use and should not be called directly.
        """
        if not self.emulator.is_alive():
            raise EmulatorDiedException(f"Emulator with id: {self.name} is not alive.")
        elif not await self.online():
            self.logger.error("Emulator with id: %s is not online.", self.name)

    async def logcat_cmd(self):
        """Runs the `adb logcat` command asynchronously.

        Logcat output can be accessed via the logger named "emu-{id}-lct".

        Returns:
            asyncio.subprocess.Process: The process object representing the running command.
        """
        logger = create_file_logger(f"{self.emulator.log_id}-lct")
        cmd = Command([self.adb_binary, "-s", self.name, "logcat"], logger)
        return await cmd.run()

    async def logcat(self, clear: bool = False, tag: str = None) -> AsyncCommandStream:
        """Obtains the current logcat stream

        You usually want to use it like this:

        async with await adb.logcat(tag="my_tag) as stream:
            async for line in stream:
                print(f"Here's a logcat line: {line}")

        Args:
            tag (str): Tag to filter by
            clear (bool, optional): Clear the logcat buffer. Defaults to False.

        Returns:
            AsyncCommandStream: An AsyncIterator with logcat lines
        """

        if clear:
            await self.clear_logcat()

        cmd = ["logcat"]
        if tag:
            cmd += f" -s {tag}"

        return AsyncCommandStream([self.adb_binary, "-s", self.name] + cmd)

    async def stream(self, cmd: str) -> AsyncCommandStream:
        """Runs the given command on the emulator asynchronously

        You usually want to use this like this:

        async with await adb.stream("some shell cmd") as stream:
            # do some things.
            async for line in stream
                print(line)

        Args:
            cmd (str): Command to execute

        Returns:
            AdbStream: An observable stream with results from adb
        """

        return AsyncCommandStream([self.adb_binary, "-s", self.name] + cmd)

    async def wait_for_path(self, path: str, timeout: int = 60) -> None:
        """Waits for a path to exist on the device using an idiomatic async approach.

        Args:
            path (str): The path to wait for.
            timeout (int, optional): The timeout in seconds. Defaults to 60.

        Raises:
            asyncio.TimeoutError: If the path does not exist after the timeout.
        """
        self.logger.info("Waiting up to %ss for path %s to exist.", timeout, path)

        async def _path_exists():
            result = await self.shell(f"[ -e {path} ] && echo 'exists' || echo 'missing'")
            return "exists" in result

        try:
            await eventually(_path_exists, timeout=timeout)
            self.logger.info("Path %s found.", path)
        except Exception as e:
            self.logger.error("Timeout waiting for path %s.", path)
            raise e
