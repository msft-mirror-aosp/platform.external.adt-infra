#!/usr/bin/env python3
"""Projection Offscreen - uses UI navigation."""

import sys
import os
import time
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(SCRIPT_DIR)
from cts_common import setup, navigate_to, dismiss_dialogs_and_wait_for_pass, tap_pass, export_and_verify, screenshot, set_screenshot_dir, adb, ui_dump, tap, find_node

TEST_NAME = "Projection Offscreen Activity"
set_screenshot_dir("projection_offscreen_activity")

setup()
try:
    navigate_to(TEST_NAME)
except RuntimeError:
    print("Flaky navigation, retrying...")
    time.sleep(2)
    adb("shell", "am", "start", "-n", "com.android.cts.verifier/.CtsVerifierActivity")
    time.sleep(5)
    navigate_to(TEST_NAME)

# dismiss OK dialog that might appear initially
root = ui_dump()
ok = find_node(root, text="OK")
if ok is not None:
    tap(ok)
    time.sleep(2)

print("Turning screen off for 8 seconds as required by the test...")
adb("shell", "input", "keyevent", "KEYCODE_SLEEP")
time.sleep(8)
print("Turning screen back on...")
adb("shell", "input", "keyevent", "KEYCODE_WAKEUP")
time.sleep(3)

# Unlock screen with Menu key
adb("shell", "input", "keyevent", "82")
time.sleep(2)

pass_btn = dismiss_dialogs_and_wait_for_pass(timeout=30)
tap_pass(pass_btn)
export_and_verify(TEST_NAME)
