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
from emu.application import AnimationApplication


@pytest.fixture
@pytest.mark.async_timeout(120)
async def install_animation_apk(avd: BaseEmulator):
    """Installs the animation APK on the emulator.

    Retries installation up to 3 times in case of transient failures.
    """
    apk = AnimationApplication(avd)
    await apk.install()
    yield apk


@pytest.fixture
@pytest.mark.async_timeout(120)
async def animation_app(install_animation_apk, avd: BaseEmulator):
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
    animation = install_animation_apk
    await animation.start()
    logging.info("--> yielding animation_app")
    yield animation
    logging.info("<-- teardown animation_app")

    await animation.stop()
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
        await emulator.stop()
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
