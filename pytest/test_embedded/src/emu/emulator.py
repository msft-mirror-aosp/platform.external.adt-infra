# Copyright 2024 - The Android Open Source Project
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
import os
import platform
import random
import re
import shutil
import socket
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from aemu.discovery.emulator_description import EmulatorDescription
from aemu.discovery.emulator_discovery import EmulatorDiscovery
from aemu.proto.emulator_controller_pb2 import (
    KeyboardEvent,
    ParameterValue,
    PhysicalModelValue,
)
from aemu.proto.emulator_controller_pb2_grpc import EmulatorControllerStub
from google.protobuf import empty_pb2
from grpc import RpcError, StatusCode
from grpc.aio import AioRpcError

from emu.adb.adb import Adb
from emu.avd import AvdWriter
from emu.console.emulator_connection import EmulatorClient
from emu.emulator_exceptions import EmulatorNotFoundException
from emu.mobly.snippet import Mobly
from emu.process.command import Command
from emu.timing import eventually, wait_until
from emu.utils import LogObserver


class BaseEmulator(object):
    def __init__(self, android_home: Path, android_avd_home: Path) -> None:
        """An Emulator represents a running emulator which you can interact with.

        Usualy you want to either:

        - Launch one (Using the Emulator class)
        - Connect to one (Using DebugEmulator class)

        Raises:
            AndroidSdkRootNotSet: The ANDROID_SDK_ROOT environment variable is not set.
        """
        self.description: EmulatorDescription = None
        self.android_home = android_home.absolute()
        self.android_avd_home = android_avd_home.absolute()
        self.apk_installed = set()
        self.proc = None
        self.executable = None
        self.logger = logging.getLogger("emulator")
        self.logger.info(
            "Using android_home: %s, android_avd_home: %s",
            self.android_home,
            self.android_avd_home,
        )
        self.hardware = None
        self.cmd = None
        self.adb: Adb = None
        self.mobly_device: Mobly = None
        self.channel = None
        self.log_id = "emu-0"
        adb = shutil.which("adb", path=self.android_home / "platform-tools")
        subprocess.check_call([adb, "start-server"])

    def __str__(self):
        return str(self.description)

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
            self,
        )
        self.mobly_device = Mobly(self.description.name())
        self.logger.info(
            "Discovered emulator pid: %s (%s), named: %s",
            self.description.pid(),
            self.description.name(),
            self.description.get("avd.id"),
        )
        self.channel = self.description.get_async_grpc_channel(
            [("emulator.security", "token")]
        )

    async def _hardware(self):
        _EMPTY_ = empty_pb2.Empty()
        emu = EmulatorControllerStub(self.channel)
        status = await emu.getStatus(_EMPTY_)
        self.hardware = dict([(x.key, x.value) for x in status.hardwareConfig.entry])

    async def api_level(self) -> int:
        # This assumes we have called has_booted..
        if not self.hardware:
            await self._hardware()

        return int(self.hardware.get("avd.api_level", "0"))

    def mobly(self, name: str):
        return self.mobly_device.snippet(name)

    async def launch(self, flags: [str]) -> bool:
        """Launches the emulator

        Args:
            flags (str]): Additional set of flags that should be passed to the launcher

        Returns:
            bool: True if the emulator was launched and the corresponding discovery
                  file was written
        """
        return True

    async def stop(self) -> None:
        """Stops the emulator from running"""

    def delete(self) -> None:
        """Delete the given emulator, removing data from disk if applicable."""

    async def has_booted(self) -> bool:
        """Makes a check of bootcoompleted.ini to check if the emulator has booted.

        Returns:
            bool: False, the emulator has not booted, or is not accessible.
        """
        try:
            _EMPTY_ = empty_pb2.Empty()
            emu = EmulatorControllerStub(self.channel)
            status = await emu.getStatus(_EMPTY_)
            self.hardware = dict(
                [(x.key, x.value) for x in status.hardwareConfig.entry]
            )
            online = await self.adb.online()
            return status.booted and online
        except (RpcError, AioRpcError) as exc:
            if exc.value.code() == StatusCode.UNAVAILABLE:
                raise EmulatorNotFoundException(
                    "The emulator %s is no longer around.", self.description.name
                )
            self.logger.error(
                "gRPC error while determining boot state, details: %s",
                exc,
                exc_info=True,
            )
        except Exception as err:
            self.logger.error(
                "Unable to determine boot state due to %s", err, exc_info=True
            )

        return False

    async def wait_for_boot(self, timeout: int = 600) -> bool:
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
            await self.has_booted(),
        )
        return await wait_until(self.has_booted, timeout=timeout)

    async def console(self) -> EmulatorClient:
        """Returns a connection to the emulator console, authenticating if needed.

        Returns:
            EmulatorConnection: A connection to the emulator.
        """
        return await EmulatorClient.connect(
            self.description.get("port.serial"),
            self.log_id
        )

    def is_alive(self) -> bool:
        """Returns true if we believe the emulator is still alive."""

        # We must have killed the emulator.
        if self.description is None:
            self.logger.error("No description (not launched yet?)!")
            return False

        return self.description.is_alive()

    async def install_apk(self, apk: Path, package_name: str) -> bool:
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
        try:
            while not await self.adb.is_installed(package_name) and count < 3:
                await self.adb.install(apk.absolute())
                await asyncio.sleep(2)
                count += 1
        finally:
            return await self.adb.is_installed(package_name)

    async def pgrep(self, process_name: str) -> bool:
        shell = await self.adb.shell(f"ps -A | grep {process_name}")
        return process_name in shell

    async def activity_is_running(self, activity: str):
        """Returns true if the given activity is running."""
        return await self.pgrep(activity[: activity.find("/")])

    async def start_activity(self, activity: str, params=None) -> bool:
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

        shell = f"am start -n {activity}"
        if params:
            shell += f" {params}"

        count = 0
        while count < 3:
            await self.adb.shell(shell)
            await asyncio.sleep(2)
            if await self.activity_is_running(activity):
                return True
            count += 1

        return await self.activity_is_running(activity)

    async def stop_activity(self, activity: str) -> bool:
        """Attempts to stop the given activity.

        An activity is considered to be running when the activity is in the list returned
        by running `shell dumpsys activity activities`

        We will try to force-stop the activity for at most 15 seconds.

        Args:
            activity: The name of the package to stop.

        Returns:
            True if the activity is not running, False otherwise.
        """

        shell = f"am force-stop {activity}"

        count = 0
        while count < 3:
            await self.adb.shell(shell)
            await asyncio.sleep(2)
            if not await self.activity_is_running(activity):
                return True
            count += 1

        return not await self.activity_is_running(activity)

    async def reset_state(self):
        """Resets this emulator to a well known state.

        This is a best effort operation that will:

        - Bring up the home screen. (i.e. press the home button)
        - Move the device upright
        - Wake up the device. (send the wake up event)
        """
        stub = EmulatorControllerStub(self.channel)
        await stub.sendKey(
            KeyboardEvent(key="WakeUp", eventType=KeyboardEvent.keypress)
        )
        await stub.sendKey(
            KeyboardEvent(key="GoHome", eventType=KeyboardEvent.keypress)
        )
        await stub.setPhysicalModel(
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
        self.log_id = self.description.get("avd.id")

    async def launch(self, flags: List[str] = []) -> bool:
        self.logger.info("Debug emulators cannot be launched.")
        return True

    async def restart(self, emu_flags: List[str]) -> bool:
        return await self.launch(emu_flags)


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
        fetcher: Path | None,
        log_id: str | None,
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

        avd_gen = AvdWriter(self.android_home, self.android_avd_home, fetcher)
        if "abi" not in avd_config:
            avd_config["abi"] = self._default_abi()
        self.configuration = avd_gen.create_from_config(avd_config)
        self.exe = Path(exe)
        self.proc = None
        self.kernel_start = 0
        self.log_id = log_id or "emu-1"

    async def restart(self, emu_flags: List[str]) -> bool:
        """Restarts the emulator, disabling snapshot save if a default snapshot exists.

        Args:
            emu_flags: The emulator flags to use, if any.

        Returns:
            True if the emulator has launched.
        """
        if self.is_alive():
            await self.stop()

        assert not self.is_alive()

        mysnapshottexture = Path(
            self.configuration.directory, "snapshots", "default_boot", "textures.bin"
        )

        if mysnapshottexture.exists():
            emu_flags.append("-no-snapshot-save")

        return await self.launch(flags=emu_flags)

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

    async def _launch(self, cmd: list[str], env: dict[str, str]) -> None:
        self.logger = logging.getLogger(self.log_id)

        self.cmd = Command(cmd, self.logger).with_environment(env)
        if sys.platform == "win32":
            self.cmd.in_directory(self.exe.parent)

        proc = await self.cmd.run()
        self.log = proc.handler

        self.logger.info("Waiting for an emulator to become available.")
        discovery = EmulatorDiscovery()

        def discover_emulator():
            self.logger.info(
                "Found %d emulators so far, looking for pid: %s",
                discovery.available(),
                proc.process.pid,
            )
            return (
                discovery.find_emulator("avd.id", self.configuration.name) is not None
            )

        await eventually(discover_emulator, timeout=30)

        self.kernel_start = 0
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

    async def launch(self, flags: [str] = []) -> bool:
        """Launches the emulator

        Args:
            flags (str]): Additional set of flags that should be passed to the launcher

        Returns:
            bool: True if the emulator was launched and the corresponding discovery
                  file was written
        """
        # Setup android sdk/avd etc.
        local_env = {
            "ANDROID_AVD_HOME": str(self.android_avd_home),
            "ANDROID_SDK_ROOT": str(self.android_home),
            "DISPLAY": os.environ.get("DISPLAY", ":0"),
        }

        # Pick a random "adb" supported port.
        port = random.randint(5554, 5584)
        port = self._get_free_port(port, 4096)

        # grpc port by default binds to console + 3000, let's try
        # to keep that.
        grpc_port = self._get_free_port(port + 3000, 4096)

        # The security file.
        access_file = Path(__file__).parent / "templates" / "emulator_test_access.json"

        default_flags = [
            "-avd",
            self.configuration.name,
            "-verbose",
            "-show-kernel",
            "-no-location-ui",
            "-no-boot-anim",
            "-no-audio",
            # "-idle-grpc-timeout", # We will explicitly shutdown the device.
            # "300",
            "-port",  # Bind to a known open port..
            str(port),
            "-grpc",
            str(grpc_port),
            "-grpc-allowlist",
            str(access_file),
            "-debug-log",
            "-gpu",
            "swiftshader_indirect",
            "-debug-events",
            "-debug-grpc",
            "-debug",
            "console,snapshot",
        ]

        if "Vulkan" not in flags:
            # Vulkan will cause snapshot saving failure, disable it for now
            default_flags = default_flags + [ "-feature", "-Vulkan"]

        if "-no-metrics" not in flags:
            # The option '-no-metrics' is ignored if used alongside "-metrics-collection"
            default_flags = default_flags + [ "-metrics-collection"]

        return await self._launch(
            [ self.exe ]
            + default_flags
            + flags,
            local_env,
        )

    async def stop(self, timeout: int = 30) -> None:
        """Stops the emulator, terminating it does not exits gracefully within the given timeout

        Args:
            timeout (int, optional): Time in seconds before the emulator will be terminated.
            Defaults to 10.
        """
        logging.info("Stopping the emulator.")
        if self.description is not None:
            if self.description.shutdown(timeout):
                logging.info("Terminated the emulator")
            else:
                logging.warning("Unable to terminate emulator!")
            self.description = None
        if self.cmd:
            logging.info("Cancelling cmd task.")
            await self.cmd.cancel()

    async def has_booted(self) -> bool:
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
            emu = EmulatorControllerStub(self.channel)
            status = await emu.getStatus(_EMPTY_)
            return status.booted and await self.adb.online()
        except AioRpcError as exc:
            if exc.code() == StatusCode.UNAVAILABLE:
                raise EmulatorNotFoundException(
                    "The emulator %s is no longer around.", self.description.name
                )
            self.logger.error(
                "gRPC error while determining boot state, details: %s",
                exc,
                exc_info=True,
            )
        except Exception as err:
            self.logger.warning("Unable to determine boot state due to %s", err)

        return False

    def delete(self) -> None:
        self.configuration.delete()
