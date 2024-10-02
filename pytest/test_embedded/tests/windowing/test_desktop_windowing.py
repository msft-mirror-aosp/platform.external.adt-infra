# Copyright 2024 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,_ software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pytest
from mobly import asserts

_MINIMIZE_BUTTON_CONTENT_DESC = "Minimize"
_MAXIMIZE_BUTTON_CONTENT_DESC = "Maximize"
_CLOSE_BUTTON_CONTENT_DESC = "Close"
_TEST_APP_ICON_CONTENT_DESC = "Predicted app: AnimateBox"
_TEST_APP_CONTENT_DESC = "Caption bar of AnimateBox."
_TIMEOUT_MS = 8000

"""
End-to-end tests that change windowing mode with caption bar buttons (minimize, maximize, close).
"""


@pytest.fixture
async def show_status_bar(avd):
    """
    This fixture starts the StatusBarActivity which keeps its status bar visible.
    """
    await avd.stop_activity("com.google.AnimateBox")
    await avd.start_activity("com.google.AnimateBox/com.google.emu.StatusBarActivity")
    yield
    await avd.stop_activity("com.google.AnimateBox")


@pytest.mark.uiautomator
async def test_launch_app(ad_ui, show_status_bar):
    asserts.assert_true(
        ad_ui(desc=_TEST_APP_CONTENT_DESC).wait.exists(_TIMEOUT_MS),
        "Failed to see animation app",
    )


@pytest.mark.uiautomator
async def test_close_window(ad_ui, show_status_bar):
    # Click the close button and verify that the app disappears
    asserts.assert_true(
        ad_ui(desc=_CLOSE_BUTTON_CONTENT_DESC).wait.exists(_TIMEOUT_MS),
        "Close button did not appear",
    )
    ad_ui(desc=_CLOSE_BUTTON_CONTENT_DESC).click()
    asserts.assert_true(
        ad_ui(desc=_TEST_APP_CONTENT_DESC).wait.gone(_TIMEOUT_MS),
        "App did not disappear",
    )


@pytest.mark.uiautomator
async def test_minimize_and_restore_window(ad_ui, show_status_bar):
    # Click the minimize button and verify that the app is hidden
    asserts.assert_true(
        ad_ui(desc="Minimize").wait.exists(_TIMEOUT_MS),
        "Minimize button did not appear",
    )
    ad_ui(desc="Minimize").click()
    asserts.assert_true(
        ad_ui(desc=_TEST_APP_CONTENT_DESC).wait.gone(_TIMEOUT_MS),
        "App did not disappear",
    )

    # Click on the app icon and verify that the app appears
    ad_ui.dump(file=True)
    asserts.assert_true(
        ad_ui(desc=_TEST_APP_ICON_CONTENT_DESC).wait.exists(_TIMEOUT_MS),
        "App icon did not appear",
    )
    ad_ui(desc=_TEST_APP_ICON_CONTENT_DESC).click()
    asserts.assert_true(
        ad_ui(desc=_TEST_APP_CONTENT_DESC).wait.exists(_TIMEOUT_MS),
        "App did not appear",
    )


@pytest.mark.uiautomator
async def test_maximize_and_restore_window(ad_ui, show_status_bar):
    content = ad_ui(desc=_TEST_APP_CONTENT_DESC).parent
    original_bounds = content.visible_bounds

    # Click the maximize button and verify that test app content is changed to the maximum width
    ad_ui(desc=_MAXIMIZE_BUTTON_CONTENT_DESC).click()
    ad_ui.wait.idle(timeout=_TIMEOUT_MS)
    asserts.assert_equal(content.visible_bounds.top, 0)
    asserts.assert_equal(content.visible_bounds.left, 0)
    asserts.assert_equal(content.visible_bounds.right, ad_ui.width)
    asserts.assert_equal(content.visible_bounds.bottom, ad_ui.height)

    # Click the restore button and verify that test app content is changed to its previous width
    ad_ui(desc=_MAXIMIZE_BUTTON_CONTENT_DESC).click()
    asserts.assert_equal(content.visible_bounds, original_bounds)
