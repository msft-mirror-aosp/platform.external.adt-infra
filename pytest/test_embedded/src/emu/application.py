# -*- coding: utf-8 -*-
# Copyright 2024 The Android Open Source Project
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
from typing import Callable, Any, Coroutine, TypeVar, Type, Union

from emu.apk import APP_DEBUG_APK
from emu.timing import retry
from emu.emulator_exceptions import FailedToInstallApkException
from pathlib import Path


class BaseEmulator:
    pass


class Application:
    """Represents an application that can be installed and run on an emulator."""

    def __init__(
        self,
        avd: BaseEmulator,
        package_name: str = None,
        default_activity: str = None,
        apk_path: Path = None,
    ):
        self.avd = avd
        self.adb = avd.adb
        self.apk_path = apk_path  # Could be none for install apks.
        self.default_activity = default_activity
        if package_name is None and default_activity is not None:
            self.package_name = self.extract_package_name(default_activity)
        else:
            self.package_name = package_name
        if not self.package_name:
            raise ValueError(
                "Package name not specified or could not be extracted from activity"
            )

    def extract_package_name(self, activity_string: str) -> str:
        """
        Extracts the package name from an activity string.

        Args:
            activity_string: The activity string in the format "package_name/activity_name".

        Returns:
            The package name or None if extraction fails.
        """
        try:
            parts = activity_string.split("/")
            if len(parts) == 2:
                return parts[0]
            else:
                logging.warning("Invalid activity format: %s", activity_string)
                return None
        except Exception as e:
            logging.error(
                "Error extracting package name from activity '%s': %s",
                activity_string,
                e,
            )
            return None

    async def _install_operation(self):
        try:
            if not await self.adb.is_installed(self.package_name):
                await self.adb.install(self.apk_path.absolute())
        finally:
            return await self.adb.is_installed(self.package_name)

    async def _uninstall_operation(self):
        await self.adb.exec_out(f"uninstall {self.package_name}")
        return not await self.adb.is_installed(self.package_name)

    async def _stop_activity(self):
        await self.adb.shell(f"am force-stop {self.package_name}")
        return not await self.is_running()

    async def _start_activity(self, wait_for_started, activity, params, timeout):
        params = params if params is not None else ""
        await self.adb.shell(f"am start -n {activity} {params}")
        return await self.is_running() and await asyncio.wait_for(
            wait_for_started(), timeout=timeout
        )

    async def is_running(self):
        shell = await self.adb.exec_out(f"ps -A | grep {self.package_name}")
        return self.package_name in shell

    async def install(self, attempts: int = 3, delay: float = 1) -> bool:
        """Installs the application on the emulator.

        Args:
            attempts: The maximum number of attempts to make.
            delay: The delay in seconds between attempts.

        Returns:
            True if installation was successful, False otherwise.

        Raises:
            FailedToInstallApkException: If the installation fails after the specified number of attempts.
        """
        logging.info("Installing %s from %s", self.package_name, self.apk_path)
        try:
            success = await retry(
                self._install_operation,
                attempts=attempts,
                delay=delay,
                name=f"Install {self.package_name}",
                retry_on_falsy=True,
            )
            logging.info("Successfully installed %s", self.package_name)
            return success
        except Exception as e:
            logging.error(
                "Failed to install %s after %s attempts.", self.package_name, attempts
            )
            raise FailedToInstallApkException(
                f"Failed to install {self.package_name} after {attempts} attempts. Reason: {e}"
            )

    async def uninstall(self) -> bool:
        """Uninstalls the application from the emulator.

        Returns:
            True if uninstallation was successful, False otherwise.
        """
        logging.info("Removing %s", self.package_name)
        try:
            success = await retry(
                self._uninstall_operation,
                attempts=3,
                name=f"Removing {self.package_name}",
            )
            logging.info("Successfully removed %s", self.package_name)
            return success
        except Exception as e:
            logging.error("Failed to remove %s after 3 attempts.", self.package_name)
            return False

    async def start(
        self,
        activity=None,
        params: str = "",
        wait_for_started: Callable[[], Coroutine[Any, Any, bool]] = lambda: True,
        timeout: float = 5,
    ) -> bool:
        """Starts the application on the emulator.

        Args:
            params: Additional parameters to pass to the activity.
            wait_for_started: A callable that determines if the application has started.
            timeout: The maximum time to wait for the application to start, in seconds.

        Returns:
            True if the application started successfully, False otherwise.
        """
        activity = (
            f"{self.default_activity}"
            if activity is None
            else f"{self.package_name}/{activity}"
        )
        logging.info("Starting %s with params: %s", self.package_name, params)
        try:
            success = await retry(
                lambda: self._start_activity(
                    wait_for_started, activity, params, timeout
                ),
                attempts=3,
                name=f"Starting {self.default_activity}",
            )
            logging.info("Successfully started %s", self.default_activity)
            return success
        except Exception as e:
            logging.error("Failed to start %s after 4 attempts.", self.default_activity)
            return False

    async def stop(self) -> bool:
        """Stops the application on the emulator.

        Returns:
            True if the application stopped successfully, False otherwise.
        """
        logging.info("Stopping %s", self.package_name)
        try:
            success = await retry(
                self._stop_activity,
                attempts=3,
                name=f"Stopping {self.package_name}",
            )
            logging.info("Successfully stopped %s", self.package_name)
            return success
        except Exception as e:
            logging.error("Failed to stop %s after 3 attempts.", self.package_name)
            return False


class AnimationApplication(Application):
    """Represents the rotating triangle application used for testing."""

    def __init__(self, avd: BaseEmulator):
        super().__init__(
            avd,
            default_activity="com.google.AnimateBox/com.google.emu.MainActivity",
            apk_path=APP_DEBUG_APK.absolute(),
        )

    async def start(self, activity=None, params=None, timeout: float = 5) -> bool:
        async def wait_for_animation_app_started():
            async with await self.avd.adb.logcat(tag="aemu") as stream:
                logging.info("Waiting for --STARTED-- in logcat stream.")
                async for line in stream:
                    if "--STARTED--" in line:
                        return True
            return False

        await self.adb.clear_logcat()
        return await super().start(
            activity=activity,
            params=params,
            wait_for_started=wait_for_animation_app_started,
            timeout=timeout,
        )


def create_application_subclass(activity: str):
    """
    Factory function to create Application subclasses with a specific activity.

    Args:
        activity: The default activity for the application.

    Returns:
        A subclass of Application with the specified activity.
    """

    class App(Application):
        def __init__(self, avd: BaseEmulator):
            super().__init__(avd, default_activity=activity)

    return App


# Set of pre-installed applications.
ChromeApplication = create_application_subclass(
    "com.android.chrome/com.google.android.apps.chrome.Main"
)
GooglePhotosApplication = create_application_subclass(
    "com.google.android.apps.photos/.pager.HostPhotoPagerActivity"
)
MessagingApplication = create_application_subclass(
    "com.google.android.apps.messaging/.ui.ConversationListActivity"
)
DialerApplication = create_application_subclass(
    "com.android.dialer/com.android.dialer.main.impl.MainActivity"
)
YouTubeApplication = create_application_subclass(
    "com.google.android.youtube/com.google.android.apps.youtube.app.watchwhile.WatchWhileActivity"
)
CameraApplication = create_application_subclass(
    "com.android.camera2/com.android.camera.CameraActivity"
)
