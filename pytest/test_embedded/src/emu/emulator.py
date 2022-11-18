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
import signal
import sys
import time
from datetime import timedelta
from pathlib import Path
from timeit import default_timer as timer
from typing import Optional

from aemu.discovery.emulator_description import EmulatorDescription
from aemu.discovery.emulator_discovery import EmulatorDiscovery
from aemu.proto.emulator_controller_pb2 import VmRunState
from google.protobuf import empty_pb2
from grpc import RpcError

from emu.adb.adb import Adb
from emu.avd import AvdWriter
from emu.console.emulator_connection import EmulatorConnection
from emu.utils import LogObserver, run


class FailedToLaunchException(Exception):
    pass


class EmulatorNotFoundException(Exception):
    pass


class AndroidSdkRootNotSet(Exception):
    pass


class BaseEmulator(object):
    def __init__(self) -> None:
        """An Emulator represents a running emulator which you can interact with.

        Usualy you want to either:

        - Launch one (Using the Emulator class)
        - Connect to one (Using DebugEmulator class)

        Raises:
            AndroidSdkRootNotSet: The ANDROID_SDK_ROOT environment variable is not set.
        """
        if not os.environ.get("ANDROID_SDK_ROOT"):
            raise AndroidSdkRootNotSet(
                "The environment variable ANDROID_SDK_ROOT is not set"
            )

        self.telnet = None
        self.description = None
        self.sdk_root = Path(os.environ.get("ANDROID_SDK_ROOT")).absolute()
        self.avd_home = Path(
            os.environ.get("ANDROID_AVD_HOME") or Path.home() / ".android" / "avd"
        ).absolute()

        logging.info("Using sdk_root: %s, avd_home: %s", self.sdk_root, self.avd_home)

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
        logging.info("Looking for emulator: %s", avd_id)
        discovery = EmulatorDiscovery()
        if avd_id:
            self.description = discovery.find_emulator("avd.id", avd_id)
        else:
            self.description = discovery.first()

        if self.description is None:
            raise EmulatorNotFoundException(
                f"No emulator with id: {avd_id} found, did the process terminate?"
            )

        self.adb = Adb(
            self.description.name(), self.sdk_root / "platform-tools" / "adb"
        )
        logging.info(
            "Discovered emulator pid: %s, named: %s",
            self.description.pid(),
            self.description.name(),
        )

    def stop(self) -> None:
        """Stops the emulator from running"""
        pass

    def delete(self) -> None:
        """Delete the given emulator, removing data from disk if applicable."""
        pass

    def has_booted(self) -> bool:
        """Makes a gRPC call to check if the emulator has booted.

        Returns:
            bool: False, the emulator has not booted, or is not accessible.
        """
        try:
            _EMPTY_ = empty_pb2.Empty()
            emu = self.description.get_emulator_controller()
            return emu.getStatus(_EMPTY_).booted
        except RpcError as err:
            logging.warning("Unable to determine boot state due to %s", err)

        return False

    def wait_for_boot(self, timeout: int = 600) -> bool:
        """Wait at most timeout seconds for the emulator to be booted.

        Args:
            timeout (int, optional): Timeout in seconds. Defaults to 600 seconds.

        Returns:
            bool: True if the emulator has booted, False otherwise.
        """
        timeout = time.time() + timeout
        start = timer()

        logging.info(
            "Waiting at most %s seconds for %s to boot",
            timeout,
            self.description.name(),
        )
        while not self.has_booted() and time.time() < timeout:
            time.sleep(1)

        end = timer()
        booted = self.has_booted()
        logging.info(
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
        if self.telnet is None:
            self.telnet = EmulatorConnection.connect(
                self.description.get("port.serial")
            )

        return self.telnet

    def disconnect(self) -> None:
        """Closes the connection to the emulator."""
        if self.telnet:
            self.telnet.stop()

    def _check_pid(self, pid: int) -> bool:
        """Checks to see if the given pid exists.

        Args:
            pid (int): The process id we are looking for

        Returns:
            bool: True if the process is running
        """
        if sys.platform == "win32":
            raise NotImplementedError("This does not work on windows.")

        try:
            os.kill(pid, 0)
        except OSError:
            return False

        return True

    def is_alive(self) -> bool:
        """Returns true if we believe the emulator is still alive."""

        # We must have killed the emulator..
        if self.description is None:
            logging.error("No description!")
            return False

        if sys.platform == "win32":
            # We will just check if we can find the pid in the discovery set.
            # We can't use os.kill as that does not work on windows.
            discovery = EmulatorDiscovery()
            return discovery.find_by_pid(self.description.pid()) is not None
        else:
            return self._check_pid(self.description.pid())


class DebugEmulator(BaseEmulator):
    def __init__(self, logfile: Path) -> None:
        """The first discovered running emulator.

        Use this to connect to an already running emulator.

        Args:
            logfile (Path): File where the emulator is writing logs
        """
        BaseEmulator.__init__(self)
        if logfile:
            self.logobserver = LogObserver(logfile)
            self.log = self.logobserver.queue
        self._discover(None)

    def stop(self) -> None:
        self.disconnect()


class Emulator(BaseEmulator):

    DEFAULT_ARGS = [
        # "-qt-hide-window",
        # "-grpc-use-token",
        "-idle-grpc-timeout",
        "300",
        "-log-detailed",
        "-gpu",
        "swiftshader_indirect",
        "-debug-events",
        "-debug-grpc",
    ]

    DEFAULT_CONFIG = {
        "api": "31",
        "tag.id": "google_apis",
    }

    def __init__(
        self, exe: Path, avd_config: dict[str, str], params: list[str] = DEFAULT_ARGS
    ) -> None:
        """Create and launches the emulator

        Args:
            exe (Path): Path to the emulator executable
            avd_config (dict[str, str]): Avd configuration used to create the emulator.
            params (list[str], optional): Flags to pass to the emulato executable
        """
        BaseEmulator.__init__(self)
        if not shutil.which(str(exe)):
            raise EmulatorNotFoundException(f"The binary {exe} was not found")

        avd_gen = AvdWriter(self.sdk_root, self.avd_home)
        if not "abi" in avd_config:
            avd_config["abi"] = self._default_abi()
        self.avd = avd_gen.create_from_config(avd_config)

        # Setup android sdk/avd etc.
        local_env = {
            "ANDROID_AVD_HOME": self.avd_home,
            "ANDROID_SDK_ROOT": self.sdk_root,
            "DISPLAY": os.environ.get("DISPLAY", ":0"),
        }

        self._launch(
            [
                shutil.which(exe),
                "-avd",
                self.avd,
                "-verbose",
                "-show-kernel",
                "-metrics-collection",  # Make sure we always send crash reports.
                # "-no-window",
                "-no-audio",
                "-debug",
                "console,snapshot",
            ]
            + params,
            local_env,
        )

    def __del__(self):
        self.stop()

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
        _, self.log = run(cmd, env)

        max_wait = 10
        logging.info("Waiting for an emulator to become available..")
        discovery = EmulatorDiscovery()

        while max_wait > 0 and discovery.find_emulator("avd.id", self.avd) is None:
            max_wait = max_wait - 1
            logging.info(
                "Waiting %d more seconds, found %d emulators so far.",
                max_wait,
                discovery.available(),
            )
            time.sleep(1)
            discovery.discover()

        self._discover(self.avd)

    def _terminate_emulator(self, gracefully) -> None:
        emu = self.description.get_emulator_controller()
        mode = VmRunState.SHUTDOWN if gracefully else VmRunState.TERMINATE
        with_signal = 0
        if sys.platform == "win32":
            with_signal = signal.CTRL_C_EVENT if gracefully else signal.SIGILL
        else:
            with_signal = signal.SIGINT if gracefully else signal.SIGKILL

        try:
            logging.info("Make gRPC call to stop emulator")
            emu.setVmState(VmRunState(state=mode))
        except RpcError as err:
            logging.error(
                "Failed to shutdown using gRPC (%s), using signal %s.", err, with_signal
            )
            os.kill(self.description.pid(), with_signal)

    def stop(self, timeout: int = 30) -> None:
        """Stops the emulator, terminating it does not exits gracefully within the given timeout

        Args:
            timeout (int, optional): Time in seconds before the emulator will be terminated.
            Defaults to 30.
        """
        self.disconnect()

        if not self.is_alive():
            return

        self._terminate_emulator(gracefully=True)
        # Wait until the process ends. Note that the emulator will kill itself
        # after 20 seconds.
        while self.is_alive() and timeout > 0:
            time.sleep(1)
            timeout = timeout - 1

        if self.is_alive():
            self._terminate_emulator(gracefully=False)

    def delete(self) -> None:
        """Deletes the created avd."""
        to_remove = self.avd_home / f"{self.avd}.ini"
        to_remove.unlink()

        to_remove = self.avd_home / f"{self.avd}.avd"
        logging.debug("Removing %s", to_remove)
        try:
            shutil.rmtree(to_remove.absolute())
        except OSError:
            logging.warning("Failed to remove %s", to_remove)
