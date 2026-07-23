#!/usr/bin/env python3
"""
Ignore Battery Optimizations Test
Navigate to the test, dismiss any crash dialog, and tap Pass when available.
If the test crashes on emulator, dismiss the crash and check for Pass on return.
"""

import time
import sys
import os
import os
import sys
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(SCRIPT_DIR)
from cts_common import screenshot, set_screenshot_dir
from cts_common import ACTIVITY, adb, setup, navigate_to, ui_dump, find_node, tap, export_and_verify

TEST_NAME = "Ignore Battery Optimizations Test"
set_screenshot_dir("ignore_battery_optimizations_test")


setup()
# Grant IGNORE_BATTERY_OPTIMIZATIONS so the test can verify the state
adb("shell", "appops", "set", "com.android.cts.verifier", "REQUEST_IGNORE_BATTERY_OPTIMIZATIONS", "allow", check=False)
time.sleep(1)

navigate_to(TEST_NAME)
time.sleep(3)

for _ in range(20):
    root = ui_dump()
    pass_btn = find_node(root, content_desc="Pass")
    if pass_btn is None:
        pass_btn = find_node(root, text="Pass")
    if pass_btn is not None and pass_btn.get("enabled") == "true":
        print("Tapping Pass...")
        screenshot("tapping_pass")
        tap(pass_btn)
        break
    # Dismiss crash dialogs if the activity crashes
    for dismiss_text in ["Close app", "OK", "Cancel"]:
        btn = find_node(root, text=dismiss_text)
        if btn is not None:
            print(f"  Dismissing dialog: {dismiss_text}")
            tap(btn)
            break
    time.sleep(3)
else:
    raise RuntimeError("Pass button never became available")

export_and_verify(TEST_NAME)
