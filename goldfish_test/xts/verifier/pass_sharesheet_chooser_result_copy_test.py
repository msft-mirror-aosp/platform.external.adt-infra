#!/usr/bin/env python3
"""
Chooser Result: Copy
Taps Share to open the chooser, then taps the "Copy text" action button.
The test auto-passes on selection.

Flow:
  1. setup() + navigate_to "Chooser Result: Copy"
  2. Dismiss OK if present
  3. Tap Share button
  4. Chooser opens; find the "Copy text" node (content-desc or text contains 'Copy')
     and tap it
  5. Test auto-passes and returns to main list
  6. Export ZIP and verify test_result.xml

Screenshots saved to ./cts_screenshots/sharesheet_copy/<step>_<desc>.png
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

TEST_NAME  = "Chooser Result: Copy"
set_screenshot_dir("chooser_result_copy")

OUTPUT_DIR = os.environ.get("CTS_OUTPUT_DIR", "/tmp")





def tap_bounds(b):
    nums = [int(x) for x in b.replace("][", ",").strip("[]").split(",")]
    x, y = (nums[0] + nums[2]) // 2, (nums[1] + nums[3]) // 2
    adb("shell", "input", "tap", str(x), str(y))
    time.sleep(1.5)


def find_copy_button(root):
    """Find the Copy action icon in the chooser.
    Primary: exact content-desc='Copy text'.
    Secondary: small roughly-square icon button with 'copy' in content-desc
    (distinguishes the icon from wide text labels by comparing width vs height).
    """
    for n in root.iter("node"):
        if n.get("content-desc") == "Copy text" and n.get("enabled") == "true":
            return n
    for n in root.iter("node"):
        desc = n.get("content-desc", "")
        if "copy" in desc.lower() and n.get("enabled") == "true":
            b = n.get("bounds", "")
            if b:
                nums = [int(x) for x in b.replace("][", ",").strip("[]").split(",")]
                width = nums[2] - nums[0]
                height = nums[3] - nums[1]
                # Icon button: small and roughly square; wide text labels have width >> height
                if width < 300 and height > 0 and abs(width - height) < height * 0.5:
                    return n
    return None


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

# Find Copy action in the chooser, or fall back to coordinate
root = ui_dump()
copy_btn = find_copy_button(root)
if copy_btn is None:
    raise RuntimeError("Copy action not found in chooser dump")
print(f"Tapping Copy at {copy_btn.get('bounds')}")
tap_bounds(copy_btn.get("bounds"))

time.sleep(2)
screenshot("after_copy")

export_and_verify(TEST_NAME)
screenshot("export_done")
