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
from typing import Callable, Any, Coroutine

from emu.apk import (
    APP_DEBUG_APK,
    APP_GEARS_APK,
    APP_GLTF_VIEWER_APK,
    APP_HELLOVK_APK,
    APP_MAPS_DEMO_APK,
    APP_TRIANGLE_APK,
    APP_VULKANCAPSVIEWER_APK,
    APP_VULKAN_SAMPLES_APK,
    APP_VULKAN_SAMPLES_ASSETS,
    APP_GFXBENCH_APK,
    APP_GFXBENCH_ASSETS,
    PREBUILT_GEARS_APK,
    PREBUILT_GLTF_VIEWER_APK,
    PREBUILT_HELLOVK_APK,
    PREBUILT_MAPS_DEMO_APK,
    PREBUILT_TRIANGLE_APK,
    PREBUILT_VULKANCAPSVIEWER_APK,
    PREBUILT_VULKAN_SAMPLES_APK,
    PREBUILT_VULKAN_SAMPLES_ASSETS,
    PREBUILT_GFXBENCH_APK,
    PREBUILT_GFXBENCH_ASSETS
)
from emu.timing import retry
from emu.emulator_exceptions import (
    FailedToInstallApkException,
    FailedToStartActivityException
)
from pathlib import Path


class BaseEmulator:
    pass


class Application:
    """Represents an application that can be installed and run on an emulator."""

    @staticmethod
    def extract_package_name(activity_string: str) -> str:
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

    @staticmethod
    async def start_strategy_no_wait():
        await asyncio.sleep(0)
        return True

    @staticmethod
    def  start_strategy_wait_for_activity_manager_signal(avd, package_name):
        async def start():
            async with await avd.adb.logcat(tag="ActivityManager") as stream:
                    async for line in stream:
                        if f"Displayed {package_name}" in line:
                            return True
                    return False
        return start

    def __init__(
        self,
        avd: BaseEmulator,
        package_name: str = None,
        default_activity: str = None,
        apk_path: Path = None,
        wait_for_start_strategy: Callable[
            [], Coroutine[Any, Any, bool]
        ] = start_strategy_no_wait,
        local_run: bool = False,
    ):
        self.avd = avd
        self.apk_path = apk_path
        self.default_activity = default_activity
        self.local_run = local_run
        if package_name is None and default_activity is not None:
            self.package_name = Application.extract_package_name(default_activity)
        else:
            self.package_name = package_name
        if not self.package_name:
            raise ValueError(
                "Package name not specified or could not be extracted from activity"
            )

        self.wait_for_started = wait_for_start_strategy

    @property
    def adb(self):
        return self.avd.adb



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
        if self.local_run and not self.apk_path.exists():
            logging.error(f"APK not found at {self.apk_path}")
            logging.error("For local runs, you must manually download and extract the test APKs.")
            logging.error(f"Please ensure the APK is available at the specified path.")
            raise FileNotFoundError(f"APK not found: {self.apk_path}")

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
        timeout: float = 5,
        attempts: int = 3,
        delay: float = 1,
    ) -> bool:
        """Starts the application on the emulator.

        Args:
            activity: The activity to start. If None, the default activity is used.
            params: Additional parameters to pass to the activity.
            timeout: The maximum time to wait for the application to start, in seconds.
            attempts: The maximum number of attempts to make.
            delay: The delay in seconds between attempts.

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
            await self.adb.clear_logcat()
            success = await retry(
                lambda: self._start_activity(
                    self.wait_for_started, activity, params, timeout
                ),
                attempts=attempts,
                name=f"Starting {self.default_activity}",
                delay=delay,
            )
            logging.info("Successfully started %s", self.default_activity)
            return success
        except RuntimeError:
            raise FailedToStartActivityException
        except Exception as e:
            logging.error(
                "Failed to start %s after %d attempts.",
                self.default_activity,
                attempts,
            )
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

    async def start_as_broadcast(self, action: str, receiver: str, params: str = "") -> bool:
        """Starts the application on the emulator using a broadcast intent.

        Args:
            action: The action to broadcast.
            receiver: The receiver to start.
            params: Additional parameters to pass to the broadcast.

        Returns:
            True if the broadcast was sent successfully, False otherwise.
        """
        logging.info("Starting %s with broadcast action: %s and receiver: %s", self.package_name, action, receiver)
        if not receiver:
            logging.error("No receiver specified.")
            return False

        try:
            logging.info(f"Running: am broadcast -a {action} -n {self.package_name}/{receiver} {params}")
            await self.adb.shell(f"am broadcast -a {action} -n {self.package_name}/{receiver} {params}")
            return True
        except Exception as e:
            logging.error("Failed to send broadcast %s: %s", action, e)
            return False


class AnimationApplication(Application):
    """Represents the rotating triangle application used for testing."""

    def __init__(self, avd: BaseEmulator, local_run: bool = False):
        async def wait_for_animation_app_started():
            async with await avd.adb.logcat(tag="aemu") as stream:
                logging.info("Waiting for --STARTED-- in logcat stream.")
                async for line in stream:
                    if "--STARTED--" in line:
                        return True
            return False

        super().__init__(
            avd,
            default_activity="com.google.AnimateBox/com.google.emu.MainActivity",
            apk_path=APP_DEBUG_APK,
            wait_for_start_strategy=wait_for_animation_app_started,
            local_run=local_run,
        )


class HelloVKApplication(Application):
    """Represents HelloVK App."""

    def __init__(self, avd: BaseEmulator, local_run: bool = False):
        app_activity = "com.android.hellovk/com.android.hellovk.VulkanActivity"
        apk_path = APP_HELLOVK_APK if local_run else PREBUILT_HELLOVK_APK
        super().__init__(
            avd,
            default_activity=app_activity,
            apk_path=apk_path,
            wait_for_start_strategy=Application.start_strategy_wait_for_activity_manager_signal(avd, Application.extract_package_name(app_activity))
        )


class VulkanSamplesApplication(Application):
    """Represents Vulkan Samples App."""

    async def ensure_assets(self, avd : BaseEmulator):
        install_path=Path(f"/storage/emulated/0/Android/data/{self.package_name}/files")
        tmp_dir_base = Path("/data/local/tmp")
        # Push assets to a temporary location
        await avd.adb.shell(f"mkdir -p {install_path}")

        assets_to_push = ["assets", "shaders"]
        for asset_dir_name in assets_to_push:
            source_dir = self.assets_path / asset_dir_name
            if source_dir.exists():
                    tmp_asset = tmp_dir_base / asset_dir_name
                    await avd.adb.push(f"{source_dir}", tmp_asset)
                    await avd.adb.shell(f"cp -r {tmp_asset} {install_path}")
                    await avd.adb.shell(f"chmod 777 -R {install_path / asset_dir_name}")
            else:
                if self.local_run:
                    logging.error(f"Asset directory not found at {source_dir}")
                    logging.error("For local runs, you must manually download and extract the vulkan samples assets.")
                    logging.error(f"Please download the assets from the Vulkan samples repository and place them in {self.assets_path}")
                else:
                    logging.warning(f"Asset directory not found, skipping: {source_dir}")

    def __init__(self, avd: BaseEmulator, local_run: bool = False):
        self.app_activity = "com.khronos.vulkan_samples/com.khronos.vulkan_samples.SampleLauncherActivity"
        self.local_run = local_run

        if self.local_run:
            apk_path = APP_VULKAN_SAMPLES_APK
            self.assets_path = APP_VULKAN_SAMPLES_ASSETS
        else:
            apk_path = PREBUILT_VULKAN_SAMPLES_APK
            self.assets_path = PREBUILT_VULKAN_SAMPLES_ASSETS

        super().__init__(
            avd,
            default_activity=self.app_activity,
            apk_path=apk_path,
            wait_for_start_strategy=Application.start_strategy_wait_for_activity_manager_signal(avd, Application.extract_package_name(self.app_activity))
        )


class VulkanCapsViewerApplication(Application):
    """Represents Vulkan Caps Viewer App."""

    def __init__(self, avd: BaseEmulator, local_run: bool = False):
        app_activity = "de.saschawillems.vulkancapsviewer/org.qtproject.qt5.android.bindings.QtActivity"
        apk_path = APP_VULKANCAPSVIEWER_APK if local_run else PREBUILT_VULKANCAPSVIEWER_APK
        super().__init__(
            avd,
            default_activity=app_activity,
            apk_path=apk_path,
            wait_for_start_strategy=Application.start_strategy_wait_for_activity_manager_signal(avd, Application.extract_package_name(app_activity))
        )


class TriangleApplication(Application):
    """Represents Triangle App."""

    def __init__(self, avd: BaseEmulator, local_run: bool = False):
        app_activity = "de.saschawillems.vulkanTriangle/de.saschawillems.vulkanSample.VulkanActivity"
        apk_path = APP_TRIANGLE_APK if local_run else PREBUILT_TRIANGLE_APK
        super().__init__(
            avd,
            default_activity=app_activity,
            apk_path=apk_path,
            wait_for_start_strategy=Application.start_strategy_wait_for_activity_manager_signal(avd, Application.extract_package_name(app_activity))
        )


class MapsDemoApplication(Application):
    """Represents Maps Demo App."""

    def __init__(self, avd: BaseEmulator, local_run: bool = False):
        app_activity = "com.example.mapdemo/com.example.mapdemo.MainActivity"
        apk_path = APP_MAPS_DEMO_APK if local_run else PREBUILT_MAPS_DEMO_APK
        super().__init__(
            avd,
            default_activity=app_activity,
            apk_path=apk_path,
            wait_for_start_strategy=Application.start_strategy_wait_for_activity_manager_signal(avd, Application.extract_package_name(app_activity))
        )


class GltfViewerApplication(Application):
    """Represents GLTF Viewer App."""

    def __init__(self, avd: BaseEmulator, local_run: bool = False):
        app_activity = "de.saschawillems.vulkanglTFPBR/de.saschawillems.vulkanglTFPBR.VulkanActivity"
        apk_path = APP_GLTF_VIEWER_APK if local_run else PREBUILT_GLTF_VIEWER_APK
        super().__init__(
            avd,
            default_activity=app_activity,
            apk_path=apk_path,
            wait_for_start_strategy=Application.start_strategy_wait_for_activity_manager_signal(avd, Application.extract_package_name(app_activity))
        )


class GearsApplication(Application):
    """Represents Gears App."""

    def __init__(self, avd: BaseEmulator, local_run: bool = False):
        app_activity = "de.saschawillems.vulkanGears/de.saschawillems.vulkanSample.VulkanActivity"
        apk_path = APP_GEARS_APK if local_run else PREBUILT_GEARS_APK
        super().__init__(
            avd,
            default_activity=app_activity,
            apk_path=apk_path,
            wait_for_start_strategy=Application.start_strategy_wait_for_activity_manager_signal(avd, Application.extract_package_name(app_activity))
        )


class GfxbenchApplication(Application):
    """Represents GFXBench App."""

    async def ensure_assets(self, avd : BaseEmulator):
        install_path=Path(f"/storage/emulated/0/Android/data/{self.package_name}/files")
        # First check if the assets are already on the device.
        if "exists" in await avd.adb.shell(f"[ -d {install_path / 'data'} ] && echo 'exists'"):
            logging.info("GFXBench assets already exist on the device, skipping copy.")
            return

        tmp_dir_base = Path("/data/local/tmp")
        # Push assets to a temporary location
        await avd.adb.shell(f"mkdir -p {install_path}")

        assets_to_push = ["data"]
        for asset_dir_name in assets_to_push:
            source_dir = self.assets_path / asset_dir_name
            if source_dir.exists():
                    tmp_asset = tmp_dir_base / asset_dir_name
                    await avd.adb.push(f"{source_dir}", tmp_asset)
                    await avd.adb.shell(f"cp -r {tmp_asset} {install_path}")
                    await avd.adb.shell(f"chmod 777 -R {install_path / asset_dir_name}")
            else:
                if self.local_run:
                    logging.error(f"Asset directory not found at {source_dir}")
                    logging.error("For local runs, you must manually download and extract the gfxbench assets.")
                    logging.error(f"Please download the assets from the gfxbench repository and place them in {self.assets_path}")
                else:
                    logging.warning(f"Asset directory not found, skipping: {source_dir}")

    def __init__(self, avd: BaseEmulator, local_run: bool = False):
        self.app_activity = "net.kishonti.gfxbench.vulkan.v50105.corporate/net.kishonti.app.MainActivity"
        self.local_run = local_run

        if self.local_run:
            apk_path = APP_GFXBENCH_APK
            self.assets_path = APP_GFXBENCH_ASSETS
        else:
            apk_path = PREBUILT_GFXBENCH_APK
            self.assets_path = PREBUILT_GFXBENCH_ASSETS

        super().__init__(
            avd,
            default_activity=self.app_activity,
            apk_path=apk_path,
            wait_for_start_strategy=Application.start_strategy_wait_for_activity_manager_signal(
                avd, Application.extract_package_name(self.app_activity)
            ),
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
