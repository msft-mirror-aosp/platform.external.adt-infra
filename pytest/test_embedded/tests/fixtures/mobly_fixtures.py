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
"""Fixtures for interacting with the emulator through mobly."""
import pytest
from mobly import asserts
from snippet_uiautomator import uiautomator

from emu.emulator import BaseEmulator
from emu.apk import APP_MOBLY_APK
from emu.application import Application


@pytest.fixture
@pytest.mark.async_timeout(90)
async def install_mobly_apk(avd: BaseEmulator):
    """Installs the Mobly Snippets APK on the emulator.

    Retries installation up to 3 times in case of transient failures.
    """
    mobly_snippets = Application(
        avd,
        apk_path=APP_MOBLY_APK.absolute(),
        package_name="com.google.android.mobly.snippet.bundled",
    )
    await mobly_snippets.install()
    yield mobly_snippets


@pytest.fixture
def mobly(install_mobly_apk, avd: BaseEmulator):
    """
    Provides a function to access Mobly snippet controllers for the emulator.

    This fixture simplifies interacting with Mobly snippets on the emulator.
    It returns a function that takes a package name as an argument and returns
    the corresponding Mobly snippet controller.

    Args:
        avd: The `avd` fixture providing the emulator instance.

    Returns:
        callable: A function to get Mobly snippet controllers.

    Example usage:
        def test_example(mobly):
            mbs_controller = mobly("mbs")
            # Use mbs_controller to interact with the MBS snippet
    """

    def mobly_package(package: str):
        return avd.mobly(package)

    return mobly_package


@pytest.fixture
def mbs(mobly):
    """
    Provides the Mobly MBS (Mobly Bundled Snippets) controller for the emulator.

    This fixture provides direct access to the MBS snippet controller, which offers
    various utility functions for interacting with the Android device.

    Args:
        mobly: The `mobly` fixture providing access to Mobly snippet controllers.

    Returns:
        MoblySnippetController: The MBS snippet controller.
    """
    return mobly("mbs")


@pytest.fixture(scope="function")
async def ad_ui(mobly, avd: BaseEmulator):
    """
    Provides access to the Android device's UI through UiAutomator.

    This fixture registers the UiAutomator service, allowing interaction with
    the Android device's UI elements. It yields the `ad.ui` object, which
    provides methods for finding and interacting with UI elements.

    The fixture ensures proper cleanup by unregistering the service after the test.

    Args:
        avd: The `avd` fixture providing the emulator instance.

    Yields:
        UiAutomator: The UiAutomator object for UI interaction.
    """
    ad = avd.mobly_device.get_device()
    ad.services.register(
        uiautomator.ANDROID_SERVICE_NAME, uiautomator.UiAutomatorService
    )
    yield ad.ui

    ad.services.unregister(uiautomator.ANDROID_SERVICE_NAME)
    asserts.assert_false(
        hasattr(ad, uiautomator.PUBLIC_SERVICE_NAME),
        "Failed to remove Python wrapper",
    )
    asserts.assert_false(
        hasattr(ad, uiautomator.HIDDEN_SERVICE_NAME),
        "Failed to remove snippet client",
    )
