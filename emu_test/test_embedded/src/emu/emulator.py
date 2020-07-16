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
"""A basic emulator launcher and discoverer."""
import logging
import os
import subprocess
import time

from aemu.discovery.emulator_discovery import EmulatorDiscovery
from snaptool.snapshot import SnapshotService
from google.protobuf import empty_pb2

from emu.logcat import Logcat
from emu.utils import run
from emu.avd import AvdGenerator

_EMPTY_ = empty_pb2.Empty()


class Emulator(object):
    """A launcher for the android emulator.

       This launcher mimics how studio will launch the emulator.
    """

    def __init__(self, emulator_exe, sdk_root=None):
        self.sdk_root = os.path.abspath(sdk_root or os.environ.get("ANDROID_SDK_ROOT"))
        self.adb_binary = os.path.join(self.sdk_root, "platform-tools", "adb")
        self.avd_gen = None
        self.desc = None
        self.proc = None
        if emulator_exe and os.path.exists(emulator_exe):
            self.emulator = emulator_exe
        else:
            logging.warning(
                "Falling back to ANDROID_SDK_ROOT: %s instead of %s",
                self.sdk_root,
                emulator_exe,
            )
            self.emulator = os.path.join(self.sdk_root, "emulator", "emulator")

    def get_emulator_controller(self):
        """Gets the emulator controller stub to this emulator."""
        return self.desc.get_emulator_controller()

    def get_snapshot_service(self):
        """Gets a snapshot service to interact with snaphsots."""
        return SnapshotService(snapshot_service = self.desc.get_snapshot_service())

    def get_logcat(self):
        """Gets access to logcat of this device."""
        return Logcat(self.get_emulator_controller())

    def adb(self, cmd):
        """Executes the given adb command.

           cmd should be an array of strings, adb will be configured
           to talk to this emulator.
        """
        logging.info("adb %s", " ".join(cmd))
        return subprocess.check_output([self.adb_binary, "-s", self.desc.name()] + cmd).decode("utf-8")

    def wait_for_boot(self, max_wait=120):
        """Wait at most max_wait seconds until the status of the device says it is booted.

           This is done by querying the gRPC endpoint.
        """
        emu = self.get_emulator_controller()
        response = emu.getStatus(_EMPTY_)
        while not response.booted and max_wait > 0:
            logging.info("Waiting for boot..")
            time.sleep(1)
            response = emu.getStatus(_EMPTY_)

        return response.booted

    def stop(self, graceful_timeout=10):
        """Stops the emulator, first by sending sigint. If that fails, kill -9!."""
        logging.info("Sending SIGINT to emulator.")
        self.proc.send_signal(2)

        # Gracefully end the adb server, this makes sure we do not have any dangling process.
        self.adb(["kill-server"])

        # Wait until the process ends.
        while self.proc.poll() and graceful_timeout > 0:
            time.sleep(1)
            graceful_timeout = graceful_timeout - 1

        # Kill -9 and your process is mine!
        if self.proc.poll():
            logging.warning("Sending KILL to emulator.")
            self.proc.send_signal(9)

        logging.info("Bye bye!")
        self.avd_gen = None

        # Kill adb!

    def first_running(self):
        """Discover the first running emulator."""
        discovery = EmulatorDiscovery()
        self.desc = discovery.first()

    def launch_like_studio(self):
        """Launches the emulator similarly as how studio will invoke it."""
        self.launch(
            [
                "-netdelay",
                "none",
                "-netspeed",
                "full",
                "-no-window",
                "-gpu",
                "auto-no-window",
                "-grpc-use-token",
                "-idle-grpc-timeout",
                "300",
            ]
        )

    def launch(self, additional_args=None):
        """Launches an emulator with a clean avd.

        This will start the emulator with the configured avd, and will wait
        until the discovery file has been written.
        """
        self.avd_gen = AvdGenerator(self.sdk_root)
        avd = self.avd_gen.get_avd()
        cmd = [self.emulator, "-avd", avd]

        if additional_args:
            cmd += additional_args

        # Setup android sdk/avd etc.
        local_env = os.environ.copy()
        local_env.pop("ANDROID_SDK_HOME", None)
        local_env["ANDROID_AVD_HOME"] = self.avd_gen.get_avd_home()
        local_env["ANDROID_SDK_ROOT"] = self.sdk_root

        self.proc = run(cmd, local_env)
        logging.info("Emulator running as pid: %s", self.proc.pid)

        # The emulator immediately writes a discovery file,
        # so we should be up within a few seconds.
        max_wait = 10
        logging.info("Waiting for an emulator to become available..")
        discovery = EmulatorDiscovery()

        while (
            self.proc.poll() is None  # Process is still running.
            and max_wait > 0
            and discovery.find_by_pid(self.proc.pid) is None
        ):
            max_wait = max_wait - 1
            logging.info(
                "Waiting %d more seconds, found %d emulators so far.",
                max_wait,
                discovery.available(),
            )
            time.sleep(1)
            discovery.discover()

        self.desc = discovery.find_by_pid(self.proc.pid)
        if self.desc is None:
            raise Exception("Failed to launch {} - {}".format(self.emulator, avd))
