# Copyright 2023 - The Android Open Source Project
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

from mobly.controllers import android_device
from mobly.controllers.android_device_lib.adb import AdbError

from emu.emulator_exceptions import EmulatorNotFoundException


class Mobly:
    """
    Class for managing Mobly operations on Android devices.

    Attributes:
        ads: An instance of the Android device.
        name (str): The name of the device.
    """

    def __init__(self, device_name):
        """
        Initializes the Mobly class.

        Args:
            adb: An instance of the ADB (Android Debug Bridge) controller.
            device_name (str): The name of the device.
        """
        self.ads = None
        self.name = device_name

    def _connect(self):
        """
        Connects to the Android device using Mobly.

        Raises:
            EmulatorNotFoundException: If the Android device cannot be found.
        """
        devices = android_device.get_instances([self.name])
        if len(devices) != 1:
            raise EmulatorNotFoundException(
                f"Unable to find the mobly android device, found: {devices}"
            )
        self.ads = devices[0]

    def _load_snippet(self, name, package):
        """
        Loads the specified snippet on the Android device.

        Args:
            name (str): The name of the snippet.
            package (str): The package of the snippet.

        Raises:
            AdbError: If an ADB-related error occurs.
        """
        try:
            self.ads.load_snippet(name, package)
        except AdbError as err:
            logging.error("Adb failure, trying again. Error: %s", err)
            self.ads.load_snippet(name, package)

    def snippet(self, name: str):
        """
        Returns the specified snippet from the Android device.

        Args:
            name (str): The name of the snippet.

        Returns:
            Any: The specified snippet if found, None otherwise.
        """
        package = {
            "mbs": "com.google.android.mobly.snippet.bundled",
            "animation": "com.google.AnimateBox",
        }

        if self.ads is None:
            self._connect()

        if hasattr(self.ads, name):
            return getattr(self.ads, name)

        self._load_snippet(name, package[name])
        return getattr(self.ads, name)

    def get_device(self):
        """
        Returns the Android device instance.
        """
        if self.ads is None:
            self._connect()
        return self.ads