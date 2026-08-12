#!/usr/bin/env python3
"""
Capture Content For Notes Tests
The test description says to mark this test as passed since ROLE_NOTES is not
enabled on the device.  After dismissing the OK dialog the Pass button is
already enabled, so we just tap it.
"""

import time
from cts_common import screenshot, set_screenshot_dir

from cts_common import (
    ACTIVITY, adb, setup, navigate_to, export_and_verify,
    dismiss_dialogs_and_wait_for_pass, tap_pass,
)

TEST_NAME = "Capture Content For Notes Tests"
set_screenshot_dir("capture_content_for_notes_tests")


setup()
print("Navigating to test...")
screenshot("navigating_to_test")
navigate_to(TEST_NAME)
time.sleep(2)
print("Dismissing OK dialog and tapping Pass...")
pass_btn = dismiss_dialogs_and_wait_for_pass()
tap_pass(pass_btn)
export_and_verify(TEST_NAME)
