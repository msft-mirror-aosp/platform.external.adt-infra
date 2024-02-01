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
from pathlib import Path

from ppadb.client_async import ClientAsync as AdbClientAsync

from emu.adb.async_device import AdbDeviceAsync, DeviceStream
from emu.logging.logcat_parser import parse_logcat
from emu.process.command import Command
from emu.timing import eventually


class AdbDeviceNotFound(Exception):
    pass


class Adb:
    """A class representing an ADB client for communication with an Android emulator.

    Attributes:
        name (str): Name of the emulator.
        avd_id (str): Identifier of the Android Virtual Device (AVD) associated with the emulator.
        logger (Logger): Logging object to handle logs for this ADB instance.
        client (AdbClientAsync): An instance of the AdbClientAsync class for ADB communication.
        adb_binary (Path): Path to the ADB executable.

    Args:
        avd_id (str): Identifier of the Android Virtual Device (AVD) associated with the emulator.
        emulator (str): Name of the emulator, this will be passed in as the -s parameter.
        adb (Path): Path to the adb executable.
    """

    def __init__(self, avd_id: str, emulator: str, adb: Path) -> None:
        """Create an adb object that runs against the given emulator

        Args:
            emulator (str): Name of the emulator, this will be passed in as the -s parameter when making
                            calls with the adb executable
            adb (Path): path to the adb executable.
        """
        self.name = emulator
        self.avd_id = avd_id
        self.logger = logging.getLogger(f"{avd_id}-adb")
        self.client: AdbClientAsync = AdbClientAsync()

        if not adb.exists() and platform.system() == "Windows":
            adb = adb.with_suffix(".exe")

        self.adb_binary = adb.absolute()

    async def device(self) -> AdbDeviceAsync:
        """Get the DeviceAsync object representing the Android emulator.

        Returns:
            DeviceAsync: An instance of the Device class representing the emulator.

        Raises:
            AdbDeviceNotFound: If the device with the specified name is not found or has crashed.
        """
        device = await self.client.device(self.name)
        if not device:
            raise AdbDeviceNotFound(
                f"Unable to find the device {self.name}, did it crash?"
            )
        return AdbDeviceAsync(device, self.client, self.logger)

    async def _with_adb_retry(self, method, params):
        """Executes the given ADB method with retry logic in case of failure.

        Args:
            method: The ADB method to be executed.
            params: List of parameters to be passed to the ADB method.

        Returns:
            The result of the ADB method.

        Note:
            This method is for internal use and should not be called directly.
        """
        try:
            logging.info(
                "adb: %s(%s)", method.__name__, ", ".join([str(x) for x in params])
            )
            return await method(*params)
        except Exception as rerr:
            logging.error(
                "Failed to invoke method due %s, retry after adb restart",
                rerr,
                exc_info=True,
            )
            await self.stop_server()
            await self.start_server()
            return await method(*params)

    async def stop_server(self) -> None:
        """Stops the adb server."""
        await Command([self.adb_binary, "kill-server"]).run_until_finished()

    async def start_server(self) -> None:
        """Starts the adb server."""
        await Command([self.adb_binary, "start-server"]).run_until_finished()

    async def restart(self) -> None:
        """Restarts the adb server."""
        await self.stop_server()
        await self.start_server()

    async def is_installed(self, package: str) -> bool:
        """Check if the given package is installed on the device.

        Args:
            package (str): The name of the package to check.

        Returns:
            bool: True if the package is installed, False otherwise.
        """
        device = await self.device()
        return await self._with_adb_retry(device.is_installed, [package])

    async def install(self, apk: Path) -> None:
        """Install the given apk on the device.

        Args:
            apk (Path): The path to the APK file to be installed.
        """
        device = await self.device()
        await self._with_adb_retry(device.install, [apk])

    async def pull(self, src: str, dest: str) -> None:
        """Pull a file from the device to the host.

        Args:
            src (str): The path of the file on the device.
            dest (str): The destination path on the host.
        """
        device = await self.device()
        await self._with_adb_retry(device.pull, [src, dest])

    async def push(self, src: str, dest: str) -> None:
        """Push a file from the host to the device.

        Args:
            src (str): The path of the file on the host.
            dest (str): The destination path on the device.
        """
        device = await self.device()
        await self._with_adb_retry(device.push, [src, dest])

    async def wait_boot_complete(self, timeout=60, timedelta=1):
        """Wait for the device to complete the boot process.

        Args:
            timeout (int, optional): Maximum time to wait for boot completion in seconds. Default is 60 seconds.
            timedelta (int, optional): Time interval between boot status checks in seconds. Default is 1 second.
        """
        device = await self.device()
        return await self._with_adb_retry(
            device.wait_boot_complete, [timeout, timedelta]
        )

    async def online(self):
        """Check if the device is connected and accessible.

        This state indicates that the device is ready for
        communication with ADB commands.

        Returns:
            bool: True if the device is online, False otherwise.
        """
        device = await self.device()
        return "device" in await self._with_adb_retry(device.get_state, [])

    async def shell(self, cmd: str, timeout: int = 10) -> str:
        """Runs the given shell command on the emulator

        Args:
            cmd (str): Command to execute
            timeout (int, optional): Timeout. Defaults to 10s.

        Returns:
            str: Result of the shell command
        """
        device = await self.device()
        res = await device.shell(cmd, timeout=timeout)
        return res

    async def run(self, cmd: list[str], timeout: int = 10) -> (int, [str]):
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
        return await Command(
            [self.adb_binary, "-s", self.name] + cmd
        ).run_until_finished(timeout)

    async def stream(self, cmd: str, timeout: int = 10) -> DeviceStream:
        """Runs the given command on the emulator asynchronously

        You usually want to use this like this:

        async with adb.stream("some shell cmd") as stream:
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
        device = await self.device()
        return await device.shell_stream(cmd, timeout)

    async def clear_logcat(self):
        """
        Clears the Android device's Logcat buffer and waits for a new log line to appear.

        Returns:
            True if the Logcat was successfully cleared, False if a timeout occurred (3s).
        """
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

    async def logcat(
        self, clear: bool = False, tag: str = None, timeout=180
    ) -> DeviceStream:
        """Obtains the current logcat stream

        You usually want to use it like this:

        async with await adb.logcat(tag="my_tag) as stream:
            async for line in stream:
                print(f"Here's a logcat line: {line}")


        Args:
            tag (str): Tag to filter by
            clear (bool, optional): Clear the logcat buffer. Defaults to True.
            timeout (int, optional): Timeout in seconds, happens if no logcat line
                          is produced with the given time

        Returns:
            DeviceStream: An AsyncIterator with logcat lines
        """
        if clear:
            self.clear_logcat()

        cmd = "logcat"
        if tag:
            cmd += f" -s {tag}"

        device = await self.device()
        return await device.shell_stream(cmd, timeout)
