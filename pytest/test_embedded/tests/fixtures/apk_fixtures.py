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
"""Fixtures for launching an animation APK."""

import asyncio
import logging
import time

import pytest

from emu.emulator import BaseEmulator
from emu.emulator_exceptions import (
    EmulatorFailedToBootException,
    FailedToInstallApkException,
)


async def launch_animation_app(avd: BaseEmulator):
    """
    Launches the debug animation app on the emulator.

    This function performs the following steps to ensure the animation app is running:

    1. Stops any existing instances of the animation app.
    2. Clears the logcat (best-effort, not guaranteed to be complete).
    3. Starts the main activity of the animation app.
    4. Waits for the "--STARTED--" message in the logcat, indicating the app has launched.

    Args:
        avd: The emulator instance on which to launch the app.

    Returns:
        bool: True if the app launched successfully, False otherwise.
    """
    logging.info("--> launch_animation_app")
    assert avd.is_alive()
    assert await avd.stop_activity("com.google.AnimateBox")

    await avd.adb.clear_logcat()
    assert await avd.start_activity("com.google.AnimateBox/com.google.emu.MainActivity")

    async def wait_for_started():
        async with await avd.adb.logcat(tag="aemu") as stream:
            logging.info("Waiting for --STARTED-- in logcat stream.")
            async for line in stream:
                if "--STARTED--" in line:
                    return True

    try:
        return await asyncio.wait_for(wait_for_started(), timeout=5)
    except asyncio.TimeoutError:
        logging.warning("No --STARTED-- tag seen.")
        return False


async def wait_for_animation_app_launch(avd: BaseEmulator, timeout: int = 30):
    """Attempts to launch the animation app within a given timeout.

    Args:
      avd: The emulator to launch the app on.
      timeout: The maximum time to wait for the app to launch, in seconds.

    Raises:
      FailedToInstallApkException: If the app fails to launch within the timeout.
    """
    end_time = time.time() + timeout
    launched = False
    while time.time() < end_time and not launched:
        launched = await launch_animation_app(avd)
        if not launched:
            await asyncio.sleep(1)

    if not launched:
        avd.stop()
        # Share log cat for debugging
        logging.info("--> Logcat which might be of use:")
        await avd.adb.exec_out("logcat -d")
        raise FailedToInstallApkException(
            "We failed to install and launch the animation apk."
        )

    logging.info("--> animation apk running")


@pytest.fixture
@pytest.mark.async_timeout(90)
async def animation_app(avd: BaseEmulator):
    """Launch the animation app that displays a rotating triangle.

    This fixture launches an application that displays a rotating
    triangle at 60fps, along with a white box in the corner.
    The application also logs all received key events to logcat.

    The animation app is stopped at the end of the test.

    Args:
        avd: An instance of the `BaseEmulator` class.

    Yields:
        None

    Raises:
        AssertionError: If the animation app fails to launch.
    """
    logging.info("--> animation_app")
    assert avd.is_alive()

    await wait_for_animation_app_launch(avd, timeout=30)
    logging.info("--> yielding animation_app")
    yield
    logging.info("<-- teardown animation_app")

    await avd.stop_activity("com.google.AnimateBox")
    logging.info("=== finalized animation_app")


@pytest.fixture
@pytest.mark.async_timeout(200)
async def coldboot_animation_app(emulator: BaseEmulator):
    """Launch the animation app after a cold boot.

    Similar to `animation_app`, but performs a cold boot before
    launching the application. This ensures that the application
    is launched in a clean state.

    Args:
        emulator: An instance of the `BaseEmulator` class.

    Yields:
        None

    Raises:
        EmulatorFailedToBootException: If the emulator fails to boot.
        AssertionError: If the animation app fails to launch.
    """
    logging.info("--> coldboot_animation_app")
    await emulator.stop()
    assert await emulator.launch(flags=["-no-snapshot-load"])
    booted = await emulator.wait_for_boot()
    if not booted:
        emulator.stop()
        raise EmulatorFailedToBootException(
            "The emulator did not boot in time and was stopped."
        )

    assert emulator.is_alive()

    # Sleep for a few seconds after cold boot to allow
    # system UI to update (time, LTE signal, etc.).
    await asyncio.sleep(10)

    wait_for_animation_app_launch(emulator, timeout=30)
    logging.info("--> yielding coldboot_animation_app")
    yield
    logging.info("<-- teardown coldboot_animation_app")
    await emulator.stop_activity("com.google.AnimateBox")
    await emulator.reset_state()
    logging.info("== finalized coldboot_animation_app")
