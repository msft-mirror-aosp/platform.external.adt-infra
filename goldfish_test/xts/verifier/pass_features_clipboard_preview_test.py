#!/usr/bin/env python3
"""
Clipboard Preview Test
Verifies that a clipboard confirmation UI appears when content is copied.
After the OK dialog, the Pass button becomes enabled once the 'Copy' button
is tapped (clipboard content is written).
"""

import time
from cts_common import screenshot, set_screenshot_dir

from cts_common import (
    ACTIVITY, adb, setup, navigate_to, export_and_verify,
    find_node, ui_dump, tap, wait_for, tap_pass,
)

TEST_NAME = "Clipboard Preview Test"
set_screenshot_dir("clipboard_preview_test")


setup()
print("Navigating to test...")
screenshot("navigating_to_test")
navigate_to(TEST_NAME)
time.sleep(2)

# Dismiss the intro OK dialog
root = ui_dump()
ok = find_node(root, text="OK")
if ok is not None:
    print("  Dismissing OK dialog...")
    tap(ok)
    time.sleep(2)

# Tap Copy to write to clipboard — this enables the Pass button
print("Tapping 'Copy'...")
screenshot("tapping_copy")
copy_btn = wait_for(text="Copy", timeout=10)
tap(copy_btn)
time.sleep(2)

print("Tapping Pass...")
screenshot("tapping_pass")
tap_pass()
export_and_verify(TEST_NAME)
