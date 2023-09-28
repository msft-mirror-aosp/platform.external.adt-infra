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
import random
import re
import shutil
import socket
import sys
import time
import subprocess
from pathlib import Path
from typing import Optional, List


from aemu.discovery.emulator_description import EmulatorDescription
from aemu.discovery.emulator_discovery import EmulatorDiscovery
from aemu.proto.emulator_controller_pb2 import (
    KeyboardEvent,
    ParameterValue,
    PhysicalModelValue,
)
from google.protobuf import empty_pb2
from grpc import RpcError

from emu.adb.adb import Adb
from emu.avd import AvdWriter
from emu.console.emulator_connection import EmulatorConnection
from emu.logging.log_handler import QueueLogHandler
from emu.process.command import Command
from emu.utils import LogObserver
from emu.timing import wait_until


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
        self.description: EmulatorDescription = None
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
        self.adb: Adb = None
        adb = shutil.which("adb", path=self.android_home / "platform-tools")
        subprocess.check_call([adb, "start-server"])

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

        # Log spam!
        # logging.getLogger("ppadb").setLevel(logging.DEBUG)
        self.adb = Adb(
            self.description.get("avd.id"),
            self.description.name(),
            self.android_home / "platform-tools" / "adb",
        )

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
        try:
            _EMPTY_ = empty_pb2.Empty()
            emu = self.description.get_emulator_controller()
            return emu.getStatus(_EMPTY_).booted and self.adb.online()
        except Exception as err:
            self.logger.warning("Unable to determine boot state due to %s", err)

        return False

    def wait_for_boot(self, timeout: int = 600) -> bool:
        """Wait at most timeout seconds for the emulator to be booted.

        Args:
            timeout (int, optional): Timeout in seconds. Defaults to 600 seconds.

        Returns:
            bool: True if the emulator has booted, False otherwise.
        """
        assert (
            self.description is not None
        ), "You cannot call wait_for_boot on an undiscovered emulator."
        logging.info(
            "Waiting at most %s seconds until %s has booted, state: %s",
            timeout,
            self.description.name(),
            self.has_booted(),
        )
        return wait_until(self.has_booted, timeout=timeout)

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

    def install_apk(self, apk: Path, package_name: str) -> bool:
        """Installs an apk in the emulator.

        Note: An apk will be installed only once unless force has been set to
        true.

        Args:
            apk (Path): Path to the apk that should be installed.
            package (str): The name of the package.

        Returns;
            True if the package name is in `pm list packages`
        """
        count = 0
        while not self.adb.is_installed(package_name) and count < 10:
            self.adb.install(apk.absolute())
            time.sleep(1)
            count += 1

        return self.adb.is_installed(package_name)

    def start_activity(self, activity: str, params) -> bool:
        """Attempts to start the given activity.

        An activity is considered to be running when the activity is in the list returned
        by running `shell dumpsys activity activities`

        If the acitivity has failed to launch within 15 seconds, it will
        be considered a failure.

        Args:
            activity: The name of the activity to start.

        Returns:
            True if the activity was started successfully, False otherwise.
        """

        def activity_is_running():
            """Returns true if the given activity is running."""
            in_focus = self.adb.shell(
                "dumpsys activity activities | grep mFocusedWindow"
            )
            return activity in in_focus

        shell = f"am start -n {activity}"
        if params:
            shell += f" {params}"

        self.adb.shell(shell)
        count = 0
        while count < 10:
            self.adb.shell(shell)
            time.sleep(1)
            if activity_is_running():
                return True
            count += 1

        return False

    def stop_activity(self, activity: str) -> bool:
        """Attempts to stop the given activity.

        An activity is considered to be running when the activity is in the list returned
        by running `shell dumpsys activity activities`

        We will try to force-stop the activity for at most 15 seconds.

        Args:
            activity: The name of the package to stop.

        Returns:
            True if the activity is not running, False otherwise.
        """

        def activity_is_running():
            """Returns true if the given activity is running."""
            in_focus = self.adb.shell(
                "dumpsys activity activities | grep mFocusedWindow"
            )
            return activity in in_focus

        self.adb.shell(f"am force-stop {activity}")
        count = 0
        while activity_is_running() and count < 10:
            self.adb.shell(f"am force-stop {activity}")
            time.sleep(1)
            count += 1

        return not activity_is_running()

    def reset_state(self):
        """Resets this emulator to a well known state.

        This is a best effort operation that will:

        - Bring up the home screen. (i.e. press the home button)
        - Move the device upright
        - Wake up the device. (send the wake up event)
        """
        stub = self.description.get_emulator_controller()
        stub.sendKey(KeyboardEvent(key="WakeUp", eventType=KeyboardEvent.keypress))
        stub.sendKey(KeyboardEvent(key="GoHome", eventType=KeyboardEvent.keypress))
        stub.setPhysicalModel(
            PhysicalModelValue(
                target=PhysicalModelValue.ROTATION,
                value=ParameterValue(data=[0, 0, 0]),
            )
        )


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
            self.log = LogObserver(logfile)
        self._discover(None)
        self.logger = logging.getLogger(self.description.get("avd.id"))

    def launch(self, flags: List[str] = []) -> bool:
        self.logger.info("Debug emulators cannot be launched.")
        return True

    def restart(self, emu_flags: List[str]) -> bool:
        return self.launch(emu_flags)

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
        self.proc = None
        self.kernel_start = 0

    def restart(self, emu_flags: List[str]) -> bool:
        """Restarts the emulator, disabling snapshot save if a default snapshot exists.

        Args:
            emu_flags: The emulator flags to use, if any.

        Returns:
            True if the emulator has launched.
        """
        if self.is_alive():
            self.stop()

        assert not self.is_alive()

        mysnapshottexture = Path(
            self.configuration.directory, "snapshots", "default_boot", "textures.bin"
        )

        if mysnapshottexture.exists():
            emu_flags.append("-no-snapshot-save")

        return self.launch(flags=emu_flags)

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
        self.log = QueueLogHandler(logging.getLogger(f"{self.configuration.name}-exe"))
        self.kernel_start = 0

        cmd = Command(cmd).with_environment(env).with_log_handler(self.log)
        if sys.platform == "win32":
            cmd.in_directory(self.exe.parent)

        self.proc = cmd.run()

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

    def _get_free_port(self, port=5554, max_port=30):
        """
        Finds the first 2 available ports next to each other. This can be used to find
        two adjecent ports that can be used by the emulator to act as a console and adb
        port.

        For example, if the function is called with the arguments `port=5554` and
        `max_port=30`, it will first check if port 5554 and 5555 are available. If they are,
        it will return 5554. If it is not, it will check if port 5556 and 5557 is available.
        If it is, it will return 5556. This process will continue until the function finds
        two available ports or it reaches the `max_port` number.

        Args:
            port (int, optional): The starting port number to check. Defaults to 5554.
            max_port (int, optional): The maximum number of ports to check. Defaults to 30.

        Raises:
            IOError: If no free ports are found.

        Returns:
            int: The first free port number found.
        """
        max_attempt = port + max_port
        while port <= max_attempt:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.bind(("", port))
                sock.close()

                sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock2.bind(("", port + 1))
                sock2.close()
                return port
            except OSError:
                port += 2
        raise IOError("no free ports")

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

        # Pick a random "adb" supported port.
        port = random.randint(5554, 5584)
        port = self._get_free_port(port, 4096)

        # grpc port by default binds to console + 3000, let's try
        # to keep that.
        grpc_port = self._get_free_port(port + 3000, 4096)

        return self._launch(
            [
                self.exe,
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
                "-port",  # Bind to a known open port..
                str(port),
                "-grpc",
                str(grpc_port),
                "-debug-log",
                "-gpu",
                "swiftshader_indirect",
                # Vulkan will cause snapshot saving failure, disable it for now
                "-feature",
                "-Vulkan",
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
            if self.description.shutdown(timeout):
                logging.info("Terminated the emulator")
            else:
                logging.warning("Unable to terminate emulator!")
            self.description = None

    def has_booted(self) -> bool:
        """Check if the emulator has booted.

        This method will also observe the emulator kernel log to see if it sees
        a kernel start message.

        i.e. something like (Mac M1):

        [    0.000000][    T0] Linux version 5.15.41-android13-8-00055-g4f5025129fe8-ab8949913 (build-user@build-host) (Android (8508608, based on r450784e) clang version 14.0.7

        or (Linux X64):

        [    0.000000] Linux version 5.15.41-android13-8-00055-g4f5025129fe8-ab8949913 (build-user@build-host) (Android (8508608, based on r450784e)

        If we see 5 or more we will hit an assert and assume that we are bootlooping.

        Returns:
            bool: False, the emulator has not booted, or is not accessible.
        """

        kernel_start = re.compile(r"\[\s+0.0+\].* Linux version .* \((Android \(.*\))")
        for line in self.log.readlines():
            if kernel_start.match(line):
                self.kernel_start += 1
                logging.warning("Detected a kernel restart!")

        assert (
            self.kernel_start < 5
        ), f"Detected {self.kernel_start} kernel restarts.. This is likely a problem."

        try:
            _EMPTY_ = empty_pb2.Empty()
            emu = self.description.get_emulator_controller()
            return emu.getStatus(_EMPTY_).booted and self.adb.online()
        except Exception as err:
            self.logger.warning("Unable to determine boot state due to %s", err)

        return False

    def delete(self) -> None:
        self.configuration.delete()
