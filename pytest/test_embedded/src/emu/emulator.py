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
import platform
import shutil
import subprocess
import time
from pathlib import Path

from aemu.discovery.emulator_discovery import EmulatorDiscovery
from google.protobuf import empty_pb2
from snaptool.snapshot import SnapshotService

from emu.avd import AvdGenerator
from emu.emulator_connection import EmulatorConnection
from emu.logcat import AdbLogcatStream, AdbStream, Logcat
from emu.utils import LogObserver, run

_EMPTY_ = empty_pb2.Empty()


class Emulator(object):
    """A launcher for the android emulator.

    This launcher mimics how studio will launch the emulator.
    """

    here = os.path.abspath(os.path.dirname(__file__))

    def __init__(self, emulator_exe, sdk_root=None, avd_home=None):
        self.sdk_root = os.path.abspath(sdk_root or os.environ.get("ANDROID_SDK_ROOT"))
        self.avd_home = (
            avd_home
            or os.environ.get("ANDROID_AVD_HOME")
            or os.path.join(Path.home(), ".android", "avd")
        )
        self.adb_binary = os.path.join(self.sdk_root, "platform-tools", "adb")
        self.avd_gen = None
        self.avd = None
        self.desc = None
        self.proc = None
        self.log = None
        self.telnet = None
        self.observer = None
        self.height = 1920
        self.width = 1080
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

    def get_ui_controller(self):
        return self.desc.get_ui_controller_service()

    def get_snapshot_service(self):
        """Gets a snapshot service to interact with snaphsots."""
        return SnapshotService(snapshot_service=self.desc.get_snapshot_service())

    def name(self):
        return self.desc.name()

    def adb_stream(self, cmd):
        return AdbStream(self.adb_binary, self.desc.name(), cmd)

    def get_emu_logqueue(self):
        """Gets access to the log queue."""
        return self.log

    def start_adb(self):
        my_env = os.environ.copy()
        my_env["ADB_TRACE"] = "all"
        subprocess.run(
            [self.adb_binary, "start-server"],
            env=my_env,
            timeout=10,
        )

    def delete(self):
        """Deletes the created avd."""
        if not self.avd:
            logging.info("Not deleting avd that was not created.")
            return

        to_remove = os.path.join(self.avd_home, "{}.ini".format(self.avd))
        logging.debug("Removing %s", to_remove)
        os.remove(to_remove)

        to_remove = os.path.join(self.avd_home, "{}.avd".format(self.avd))
        logging.debug("Removing %s", to_remove)
        shutil.rmtree(os.path.join(self.avd_home, "{}.avd".format(self.avd)))

    def check_adb(self):
        my_env = os.environ.copy()
        my_env["ADB_TRACE"] = "all"
        cmd = subprocess.run(
            [self.adb_binary, "devices"],
            env=my_env,
            timeout=10,
        )
        cmd = subprocess.check_output(
            [self.adb_binary, "-s", self.desc.name(), "shell", "true"],
            env=my_env,
            timeout=10,
        )
        return True

    def adb(self, cmd):
        """Executes the given adb command.

        cmd should be an array of strings, adb will be configured
        to talk to this emulator.
        """
        name = ["-s", self.desc.name()]
        logging.info("adb %s", " ".join(name + cmd))
        cmd = subprocess.check_output([self.adb_binary] + name + cmd, timeout=60)
        logging.info("Result: %s", cmd)
        return cmd

    def get_telnet(self):
        return self.telnet

    def disconnect(self):
        self.telnet.stop()
        self.desc = None

    def _get_dimensions(self):
        response = self.get_emulator_controller().getStatus(_EMPTY_)
        cfg = response.hardwareConfig
        for entry in cfg.entry:
            if entry.key == "hw.lcd.width":
                self.width = int(entry.value)
            if entry.key == "hw.lcd.height":
                self.height = int(entry.value)
        logging.info("Dimensions: %d x %d", self.width, self.height)

    def wait_for_boot(self, max_wait=600):
        """Wait at most max_wait seconds until the status of the device says it is booted.

        This is done by querying the gRPC endpoint.
        """
        subprocess.run(
            [self.adb_binary, "wait-for-device"],
            timeout=max_wait,
        )
        logging.info(
            "%s", subprocess.check_output([self.adb_binary, "devices"]).decode("utf-8")
        )

        timeout = time.time() + max_wait
        emu = self.get_emulator_controller()
        response = emu.getStatus(_EMPTY_)

        while not response.booted and time.time() < timeout:
            logging.info("Waiting for boot of %s", self.desc.name())
            time.sleep(1)
            response = emu.getStatus(_EMPTY_)

        return response.booted

    def stop(self, graceful_timeout=10):
        """Stops the emulator, first by sending sigint. If that fails, kill -9!."""
        if not self.proc:
            return

        logging.info("Sending SIGINT to emulator.")
        self.proc.send_signal(2)

        # Wait until the process ends.
        while self.proc.poll() and graceful_timeout > 0:
            time.sleep(1)
            graceful_timeout = graceful_timeout - 1

        # Kill -9 and your process is mine!
        if self.proc.poll():
            logging.warning("Sending KILL to emulator.")
            self.proc.send_signal(9)

        logging.info("Bye bye!")

    def first_running(self, logfile):
        """Discover the first running emulator."""
        discovery = EmulatorDiscovery()
        self.desc = discovery.first()
        self.connect()
        self._get_dimensions()
        if logfile:
            self.logobserver = LogObserver(logfile)
            self.log = self.logobserver.queue

    def connect(self):
        self.telnet = EmulatorConnection.connect(self.desc.get("port.serial"))

    def launch_like_studio(self, cfg):
        """Launches the emulator similarly as how studio will invoke it."""
        self.launch(
            cfg,
            [
                "-netdelay",
                "none",
                "-netspeed",
                "full",
                "-qt-hide-window",
                "-grpc-use-token",
                "-idle-grpc-timeout",
                "300",
                "-debug-events",  # Needed for some tests.
                "-wipe-data",
                "-gpu",
                "swiftshader"
                # "-verbose",
                # Enabling the onese below will cause a huge amount of logging.
                # "-show-kernel",
                # "-logcat",
                # "v:*",
            ],
        )

    def launch(self, cfg, additional_args=None):
        """Launches an emulator with a clean avd.

        This will start the emulator with the configured avd, and will wait
        until the discovery file has been written.
        """
        self.avd_gen = AvdGenerator(self.sdk_root, self.avd_home)
        self.avd = self.avd_gen.get_avd_by_config(cfg)
        cmd = [self.emulator, "-avd", self.avd]

        if additional_args:
            cmd += additional_args

        self.start_adb()

        # Setup android sdk/avd etc.
        local_env = {
            "ANDROID_AVD_HOME": self.avd_gen.get_avd_home(),
            "ANDROID_SDK_ROOT": self.sdk_root,
            "DISPLAY": os.environ.get("DISPLAY", ":0"),
        }

        self.proc, self.log = run(cmd, local_env)
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
            logging.info("Have %s", discovery.emulators())

        logging.info("Looking for pid: %s", self.proc.pid)
        self.desc = discovery.find_by_pid(self.proc.pid)

        if self.desc is None:
            logging.error("Discovered: %s", discovery.emulators())
            raise Exception("Failed to launch {} - {}".format(self.emulator, avd))

        logging.info(
            "From available device: %s, connecting to: %s",
            self.adb(["devices"]),
            self.desc.name(),
        )
        self._get_dimensions()
        self.connect()
