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


class AdbDeviceNotFound(Exception):
    pass


class Adb:
    """A class representing an ADB client for communication with an Android emulator.

    Attributes:
        name (str): Name of the emulator.
        avd_id (str): Identifier of the Android Virtual Device (AVD) associated with the emulator.
        logger (Logger): Logging object to handle logs for this ADB instance.
        client (AdbClient): An instance of the AdbClient class for ADB communication.
        adb_binary (Path): Path to the ADB executable.

    Args:
        avd_id (str): Identifier of the Android Virtual Device (AVD) associated with the emulator.
        emulator (str): Name of the emulator, this will be passed in as the -s parameter.
        adb (Path): Path to the adb executable.
    """

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

        if not adb.exists() and platform.system() == "Windows":
            adb = adb.with_suffix(".exe")

        self.adb_binary = adb.absolute()

    def device(self) -> Device:
        """Get the Device object representing the Android emulator.

        Returns:
            Device: An instance of the Device class representing the emulator.

        Raises:
            AdbDeviceNotFound: If the device with the specified name is not found or has crashed.
        """
        device = self.client.device(self.name)
        if not device:
            raise AdbDeviceNotFound(
                f"Unable to find the device {self.name}, did it crash?"
            )
        return device

    def _with_adb_retry(self, method, params):
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
            return method(*params)
        except RuntimeError as rerr:
            logging.error(
                "Failed to invoke method due %s, retry after adb restart", rerr
            )
            self.stop_server()
            self.start_server()
            return method(*params)

    def stop_server(self) -> None:
        """Stops the adb server."""
        subprocess.check_call([self.adb_binary, "kill-server"])

    def start_server(self) -> None:
        """Starts the adb server."""
        subprocess.check_call([self.adb_binary, "start-server"])

    def is_installed(self, package: str) -> bool:
        """Check if the given package is installed on the device.

        Args:
            package (str): The name of the package to check.

        Returns:
            bool: True if the package is installed, False otherwise.
        """
        return self._with_adb_retry(self.device().is_installed, [package])

    def install(self, apk: Path) -> None:
        """Install the given apk on the device.

        Args:
            apk (Path): The path to the APK file to be installed.
        """
        self._with_adb_retry(self.device().install, [apk])

    def pull(self, src: str, dest: str) -> None:
        """Pull a file from the device to the host.

        Args:
            src (str): The path of the file on the device.
            dest (str): The destination path on the host.
        """
        self._with_adb_retry(self.device().pull, [src, dest])

    def push(self, src: str, dest: str) -> None:
        """Push a file from the host to the device.

        Args:
            src (str): The path of the file on the host.
            dest (str): The destination path on the device.
        """
        self._with_adb_retry(self.device().push, [src, dest])

    def wait_boot_complete(self, timeout=60, timedelta=1):
        """Wait for the device to complete the boot process.

        Args:
            timeout (int, optional): Maximum time to wait for boot completion in seconds. Default is 60 seconds.
            timedelta (int, optional): Time interval between boot status checks in seconds. Default is 1 second.
        """
        return self._with_adb_retry(
            self.device().wait_boot_complete, [timeout, timedelta]
        )

    def online(self):
        """Check if the device is connected and accessible.

        This state indicates that the device is ready for
        communication with ADB commands.

        Returns:
            bool: True if the device is online, False otherwise.
        """
        return "device" in self._with_adb_retry(self.device().get_state, [])

    def shell(self, cmd: str, timeout: int = 10) -> str:
        """Runs the given shell command on the emulator

        Args:
            cmd (str): Command to execute
            timeout (int, optional): Timeout. Defaults to 10s.

        Returns:
            str: Result of the shell command
        """
        self.logger.info("shell (%ss): %s", timeout, cmd)
        try:
            res = self.device().shell(cmd, timeout=timeout)
        except RuntimeError as rerr:
            logging.error(
                "Failed to invoke method due %s, retry after adb restart", rerr
            )
            self.stop_server()
            self.start_server()
            res = self.device().shell(cmd, timeout=timeout)

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
        return AdbStream(self.logger, self.device(), cmd=cmd, timeout=timeout)

    def logcat(self, clear: bool = False, tag: str = None, timeout=10) -> AdbStream:
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
            self.device(),
            cmd=cmd,
            timeout=timeout,
        )
