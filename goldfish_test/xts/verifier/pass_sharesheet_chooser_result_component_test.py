#!/usr/bin/env python3
"""
Chooser Result: Component
Taps Share to open the chooser, then taps the CTS Verifier icon inside the
chooser to select it as the share target. The test auto-passes on selection.

Flow:
  1. setup() + navigate_to "Chooser Result: Component"
  2. Dismiss OK if present
  3. Tap Share button
  4. Chooser opens; find clickable CTS Verifier LinearLayout in the chooser
     and tap it
  5. Test auto-passes and returns to main list
  6. Export ZIP and verify test_result.xml

Screenshots saved to ./cts_screenshots/sharesheet_component/<step>_<desc>.png
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

TEST_NAME  = "Chooser Result: Component"
set_screenshot_dir("chooser_result_component")

OUTPUT_DIR = os.environ.get("CTS_OUTPUT_DIR", "/tmp")





def tap_bounds(b):
    nums = [int(x) for x in b.replace("][", ",").strip("[]").split(",")]
    x, y = (nums[0] + nums[2]) // 2, (nums[1] + nums[3]) // 2
    adb("shell", "input", "tap", str(x), str(y))
    time.sleep(1.5)


def find_cts_verifier_container(root):
    """Find the clickable LinearLayout for the CTS Verifier share target.
    Walks up from the 'CTS Verifier' app-name text node to its clickable
    LinearLayout ancestor — no pixel-position assumptions needed.
    """
    parent_map = {}
    for parent in root.iter("node"):
        for child in parent:
            parent_map[id(child)] = parent
    for n in root.iter("node"):
        if n.get("text") == "CTS Verifier":
            current = n
            while id(current) in parent_map:
                current = parent_map[id(current)]
                if (current.get("clickable") == "true"
                        and current.get("enabled") == "true"
                        and "LinearLayout" in current.get("class", "")):
                    return current
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

# Find CTS Verifier LinearLayout target in chooser, or fall back to coordinate
root = ui_dump()
cts_container = find_cts_verifier_container(root)
if cts_container is None:
    raise RuntimeError("CTS Verifier container not found in chooser dump")
print(f"Tapping CTS Verifier container at {cts_container.get('bounds')}")
tap_bounds(cts_container.get("bounds"))

time.sleep(2)
screenshot("after_cts_tap")

export_and_verify(TEST_NAME)
screenshot("export_done")
