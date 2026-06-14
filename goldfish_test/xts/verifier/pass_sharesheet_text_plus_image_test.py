#!/usr/bin/env python3
"""
Sharesheet Text Plus Image
Taps Share to open the chooser (which shows both text and an image preview),
then presses BACK to dismiss it. The Pass button then enables.

Flow:
  1. setup() + navigate_to "Sharesheet Text Plus Image"
  2. Dismiss OK if present
  3. Tap Share button
  4. Chooser opens showing the shared text + image; BACK to dismiss
  5. ImageButton desc='Pass' appears → tap it
  6. Export ZIP and verify test_result.xml

Screenshots saved to ./cts_screenshots/sharesheet_tpi/<step>_<desc>.png
"""

import os
import sys
import os
import sys
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(SCRIPT_DIR)
from cts_common import screenshot, set_screenshot_dir
import re
import time
import xml.etree.ElementTree as ET

from cts_common import (
    PACKAGE, adb, setup, navigate_to,
    ui_dump, find_node, find_node_containing, tap,
    export_and_verify
)

TEST_NAME  = "Sharesheet Text Plus Image"
set_screenshot_dir("sharesheet_text_plus_image")

OUTPUT_DIR = os.environ.get("CTS_OUTPUT_DIR", "/tmp")





def tap_bounds(b):
    nums = [int(x) for x in b.replace("][", ",").strip("[]").split(",")]
    x, y = (nums[0] + nums[2]) // 2, (nums[1] + nums[3]) // 2
    adb("shell", "input", "tap", str(x), str(y))
    time.sleep(1.5)


def wait_for_parent_pass(timeout=20):
    deadline = time.time() + timeout
    while time.time() < deadline:
        root = ui_dump()
        for n in root.iter("node"):
            if (n.get("content-desc") == "Pass"
                    and n.get("class", "").endswith("ImageButton")
                    and n.get("enabled") == "true"):
                return n
        time.sleep(1)
    raise TimeoutError("Timed out waiting for parent Pass button")


def ensure_on_main_list():
    for _ in range(8):
        root = ui_dump()
        if find_node(root, content_desc="More options") is not None:
            return
        adb("shell", "input", "keyevent", "KEYCODE_BACK")
        time.sleep(2)
    raise RuntimeError("Could not reach main CTS Verifier list")


# ── Main flow ──────────────────────────────────────────────────────────────────

setup()
screenshot("app_launched")

navigate_to(TEST_NAME)
time.sleep(2)
screenshot("test_opened")

# Dismiss intro OK if present
root = ui_dump()
ok = find_node(root, text="OK")
if ok is not None:
    print("Dismissing intro dialog...")
    tap(ok)
    time.sleep(2)
    screenshot("intro_dismissed")
    root = ui_dump()

# Find and tap Share button
share_btn = None
for n in root.iter("node"):
    if (n.get("text") == "Share"
            and "Button" in n.get("class", "")
            and n.get("enabled") == "true"):
        share_btn = n
        break
if share_btn is None:
    raise RuntimeError("Share button not found")
print(f"Tapping Share at {share_btn.get('bounds')}")
tap_bounds(share_btn.get("bounds"))
time.sleep(3)
screenshot("chooser_open")

# BACK to dismiss chooser; Pass button enables after verification
print("BACK to dismiss chooser...")
adb("shell", "input", "keyevent", "KEYCODE_BACK")
time.sleep(2)
screenshot("after_back")

# ImageButton desc='Pass' should now be enabled
print("Waiting for Pass button...")
pass_btn = wait_for_parent_pass(timeout=15)
print(f"Tapping Pass at {pass_btn.get('bounds')}")
tap_bounds(pass_btn.get("bounds"))
time.sleep(2)
screenshot("pass_tapped")

export_and_verify(TEST_NAME)
screenshot("export_done")
