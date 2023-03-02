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
import os
import platform
import shutil
import subprocess
import sys
import time
from datetime import timedelta
from pathlib import Path
from timeit import default_timer as timer
from typing import Optional

from aemu.discovery.emulator_description import EmulatorDescription
from aemu.discovery.emulator_discovery import EmulatorDiscovery
from google.protobuf import empty_pb2
from grpc import RpcError

from emu.adb.adb import Adb
from emu.avd import AvdWriter
from emu.console.emulator_connection import EmulatorConnection
from emu.logging.log_handler import QueueLogHandler
from emu.process.command import Command
from emu.utils import LogObserver


class FailedToLaunchException(Exception):
    pass


class EmulatorNotFoundException(Exception):
    pass


class EmulatorDiedException(Exception):
    pass


class FailedToInstallApk(Exception):
    pass


class BaseEmulator(object):
    def __init__(self, android_home: Path, android_avd_home: Path) -> None:
        """An Emulator represents a running emulator which you can interact with.

        Usualy you want to either:

        - Launch one (Using the Emulator class)
        - Connect to one (Using DebugEmulator class)

        Raises:
            AndroidSdkRootNotSet: The ANDROID_SDK_ROOT environment variable is not set.
        """
        self.telnet = None
        self.description = None
        self.android_home = android_home.absolute()
        self.android_avd_home = android_avd_home.absolute()
        self.apk_installed = set()
        self.proc = None
        self.executable = None
        self.logger = logging.getLogger(__name__)
        self.logger.info(
            "Using android_home: %s, android_avd_home: %s",
            self.android_home,
            self.android_avd_home,
        )

    def __del__(self):
        if self.telnet:
            self.telnet.stop()

    def _initialize_with_description(self, description: Optional[EmulatorDescription]):
        """Setup the emulator given the description

        Args:
            description (EmulatorDescription): A description of the emulator, or none.

        Raises:
            EmulatorNotFoundException:  No emulator matching with the description could be found.
        """

    def _discover(self, avd_id: Optional[str]) -> None:
        """Discovers the running emulator with the given abvd id , or the first
        if no id is given. This is not a public method, and should
        be called after the object creation.

        Args:
            pid (Optional[str]): Process id

        Raises:
            EmulatorNotFoundException: No emulator matching the pid could be found.
        """
        self.logger.info("Looking for emulator: %s", avd_id)
        discovery = EmulatorDiscovery()
        if avd_id:
            self.description = discovery.find_emulator("avd.id", avd_id)
        else:
            self.description = discovery.first()

        if self.description is None:
            found = ", ".join([f"{x.name()}" for x in discovery.emulators()])
            raise EmulatorNotFoundException(
                f"No emulator with id: {avd_id} in [{found}], did the process terminate?"
            )

        self.adb = Adb(
            self.description.get("avd.id"),
            self.description.name(),
            self.android_home / "platform-tools" / "adb",
        )
        # This will sprinkle in logcat, which, well is excessive.
        # self.logcat = self.adb.logcat()
        # self.logcat.start()

        self.logger.info(
            "Discovered emulator pid: %s (%s), named: %s",
            self.description.pid(),
            self.description.name(),
            self.description.get("avd.id"),
        )

    def launch(self, flags: [str]) -> bool:
        """Launches the emulator

        Args:
            flags (str]): Additional set of flags that should be passed to the launcher

        Returns:
            bool: True if the emulator was launched and the corresponding discovery
                  file was written
        """
        return True

    def stop(self) -> None:
        """Stops the emulator from running"""
        pass

    def delete(self) -> None:
        """Delete the given emulator, removing data from disk if applicable."""
        pass

    def has_booted(self) -> bool:
        """Makes a check of bootcoompleted.ini to check if the emulator has booted.

        Returns:
            bool: False, the emulator has not booted, or is not accessible.
        """

        path = Path(
            self.android_avd_home, f"{self.configuration.name}.avd", "bootcompleted.ini"
        )
        self.logger.info("checking boot ini at %s", f"{path}")
        if path.is_file():
            return True
        return False

    def wait_for_boot(self, timeout: int = 600) -> bool:
        """Wait at most timeout seconds for the emulator to be booted.

        Args:
            timeout (int, optional): Timeout in seconds. Defaults to 600 seconds.

        Returns:
            bool: True if the emulator has booted, False otherwise.
        """
        until = time.time() + timeout
        start = timer()

        self.logger.info(
            "Waiting at most %s seconds for %s to boot",
            timeout,
            self.description.name(),
        )
        while self.is_alive() and not self.has_booted() and time.time() < until:
            time.sleep(1)

        if not self.is_alive():
            raise EmulatorDiedException("Emulator died while waiting for boot.")

        end = timer()
        booted = self.has_booted()
        self.logger.info(
            "Waited %s for boot of %s, boot status: %s",
            timedelta(seconds=end - start),
            self.description.name(),
            "succeeded" if booted else "failure",
        )
        return booted

    def console(self) -> EmulatorConnection:
        """Returns a connection to the emulator console, authenticating if needed.

        Returns:
            EmulatorConnection: A connection to the emulator.
        """
        if self.telnet is None or not self.telnet.is_connected():
            self.logger.info("Connecting to console")
            self.telnet = EmulatorConnection.connect(
                self.description.get("port.serial"), self.description.get("avd.id")
            )

        return self.telnet

    def disconnect(self) -> None:
        """Closes the connection to the emulator."""
        if self.telnet:
            self.telnet.stop()

    def is_alive(self) -> bool:
        """Returns true if we believe the emulator is still alive."""

        # We must have killed the emulator.
        if self.description is None:
            self.logger.error("No description (not launched yet?)!")
            return False

        return self.description.is_alive()

    def install_apk(self, apk: Path, force: bool = False) -> None:
        """Installs an apk in the emulator.

        Note: An apk will be installed only once unless force has been set to
        true.

        Args:
            apk (Path): Path to the apk that should be installed.
            force (bool, optional): True if we should re-install over the existing apk

        Raises:
            FailedToInstallApk: Failed to install the given apk.
        """
        if force or not apk.absolute() in self.apk_installed:
            try:
                self.logger.info("Installing %s", apk.absolute())
                self.adb.run(["install", str(apk.absolute())])
                self.apk_installed.add(apk.absolute())
            except subprocess.CalledProcessError as err:
                raise FailedToInstallApk(err) from err


class DebugEmulator(BaseEmulator):
    def __init__(
        self, android_home: Path, android_avd_home: Path, logfile: Path
    ) -> None:
        """The first discovered running emulator.

        Use this to connect to an already running emulator.

        Args:
            logfile (Path): File where the emulator is writing logs
        """
        BaseEmulator.__init__(self, android_home, android_avd_home)
        if logfile:
            self.logobserver = LogObserver(logfile)
            self.log = self.logobserver.queue
        self._discover(None)
        self.logger = logging.getLogger(self.description.get("avd.id"))

    def launch(self, flags: [str] = []) -> bool:
        self.logger.info("Debug emulators cannot be launched.")
        return True

    def stop(self) -> None:
        self.disconnect()


class Emulator(BaseEmulator):

    DEFAULT_CONFIG = {
        "api": "31",
        "tag.id": "google_apis",
    }

    def __init__(
        self,
        android_home: Path,
        android_avd_home: Path,
        exe: Path,
        avd_config: dict[str, str],
    ) -> None:
        """Create and launches the emulator

        Args:
            exe (Path): Path to the emulator executable
            avd_config (dict[str, str]): Avd configuration used to create the emulator.
            params (list[str], optional): Flags to pass to the emulato executable
        """
        BaseEmulator.__init__(self, android_home, android_avd_home)
        if not shutil.which(str(exe)):
            raise EmulatorNotFoundException(f"The binary {exe} was not found")

        avd_gen = AvdWriter(self.android_home, self.android_avd_home)
        if "abi" not in avd_config:
            avd_config["abi"] = self._default_abi()
        self.configuration = avd_gen.create_from_config(avd_config)
        self.exe = Path(exe)
        self.proc

    def _default_abi(self) -> str:
        """Returns the abi that is natively supported by this machine.

        This will detect Arm M1 even when running Python under rosetta.

        Returns:
            str: The default ABI that does not require QEMU dynamic translation.
        """
        uname = platform.uname()
        if "ARM64" in uname.version and uname.system == "Darwin":
            return "arm64-v8a"
        return "x86_64"

    def _launch(self, cmd: list[str], env: dict[str, str]) -> None:
        self.logger = logging.getLogger(self.configuration.name)
        handler = QueueLogHandler(logging.getLogger(f"{self.configuration.name}-exe"))

        cmd = Command(cmd).with_environment(env).with_log_handler(handler)
        if sys.platform == "win32":
            cmd.in_directory(self.exe.parent)

        self.proc = cmd.run()
        self.log = handler.queue

        max_wait = 20
        self.logger.info("Waiting for an emulator to become available.")
        discovery = EmulatorDiscovery()

        while (
            max_wait > 0
            and discovery.find_emulator("avd.id", self.configuration.name) is None
        ):
            max_wait = max_wait - 1
            self.logger.info(
                "Waiting %d more seconds, found %d emulators so far.",
                max_wait,
                discovery.available(),
            )
            time.sleep(1)

        self._discover(self.configuration.name)
        return self.is_alive()

    def launch(self, flags: [str] = []) -> bool:
        """Launches the emulator

        Args:
            flags (str]): Additional set of flags that should be passed to the launcher

        Returns:
            bool: True if the emulator was launched and the corresponding discovery
                  file was written
        """
        # Setup android sdk/avd etc.
        local_env = {
            "ANDROID_AVD_HOME": self.android_avd_home,
            "ANDROID_SDK_ROOT": self.android_home,
            "DISPLAY": os.environ.get("DISPLAY", ":0"),
        }

        return self._launch(
            [
                shutil.which(self.exe),
                "-avd",
                self.configuration.name,
                "-verbose",
                "-show-kernel",
                "-no-location-ui",
                "-no-boot-anim",
                "-metrics-collection",
                "-no-audio",
                # "-idle-grpc-timeout", # We will explicitly shutdown the device.
                # "300",
                "-log-detailed",
                "-gpu",
                "swiftshader_indirect",
                "-debug-events",
                "-debug-grpc",
                "-debug",
                "console,snapshot",
            ]
            + flags,
            local_env,
        )

    def stop(self, timeout: int = 30) -> None:
        """Stops the emulator, terminating it does not exits gracefully within the given timeout

        Args:
            timeout (int, optional): Time in seconds before the emulator will be terminated.
            Defaults to 10.
        """
        self.disconnect()
        if self.description is not None:
            self.description.shutdown(timeout)
            # prevent double termination.
            self.description = None

        # Only needed for the case where we were partially launched
        # self.description is likely None, and we failed to stop cleanly.
        if self.proc is not None:
            self.proc.terminate()

    def delete(self) -> None:
        self.configuration.delete()
