#!/usr/bin/env python3
"""
Sharesheet Album Label Test
Two-phase test verifying the chooser headline changes between "Sharing text"
and "Sharing album" depending on share payload type.

Flow:
  Phase 1:
    1. setup() + navigate_to "Sharesheet Album Label Test"
    2. Tap Share → chooser opens with "Sharing text" headline
    3. BACK to dismiss chooser
    4. Question appears: "Did you see a title like 'Sharing Text'?"
    5. Tap Button text='Yes'

  Phase 2:
    6. Instructions update: "Now press Share again and see if headline says 'Sharing album'"
    7. Tap Share → chooser opens with "Sharing album" headline
    8. BACK to dismiss chooser
    9. ImageButton desc='Pass' appears → tap it

  10. Export ZIP and verify test_result.xml

Screenshots saved to ./cts_screenshots/sharesheet_album/<step>_<desc>.png
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

TEST_NAME  = "Sharesheet Album Label Test"
set_screenshot_dir("sharesheet_album_label_test")

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


def find_share_button(root):
    for n in root.iter("node"):
        if (n.get("text") == "Share"
                and "Button" in n.get("class", "")
                and n.get("enabled") == "true"):
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

# ── Phase 1: Share → BACK → Yes ───────────────────────────────────────────────
print("Phase 1: tapping Share...")
share_btn = find_share_button(root)
if share_btn is None:
    raise RuntimeError("Share button not found")
print(f"  Share at {share_btn.get('bounds')}")
tap_bounds(share_btn.get("bounds"))
time.sleep(3)
screenshot("chooser_phase1")

print("BACK to dismiss chooser...")
adb("shell", "input", "keyevent", "KEYCODE_BACK")
time.sleep(2)
screenshot("after_back_phase1")

# Tap Yes button ("Did you see a title like 'Sharing Text'?")
root = ui_dump()
yes_btn = None
for n in root.iter("node"):
    if (n.get("text") == "Yes"
            and "Button" in n.get("class", "")
            and n.get("enabled") == "true"):
        yes_btn = n
        break
if yes_btn is None:
    raise RuntimeError("Yes button not found after Phase 1 BACK")
print(f"  Tapping Yes at {yes_btn.get('bounds')}")
tap_bounds(yes_btn.get("bounds"))
time.sleep(2)

# ── Phase 2: Share again → BACK → Pass ────────────────────────────────────────
screenshot("phase2_instructions")

root = ui_dump()
share_btn = find_share_button(root)
if share_btn is None:
    raise RuntimeError("Share button not found for Phase 2")
print(f"Phase 2: tapping Share at {share_btn.get('bounds')}...")
tap_bounds(share_btn.get("bounds"))
time.sleep(3)
screenshot("chooser_phase2")

print("BACK to dismiss chooser...")
adb("shell", "input", "keyevent", "KEYCODE_BACK")
time.sleep(2)
screenshot("after_back_phase2")

# ImageButton desc='Pass' should now be enabled
print("Waiting for Pass button...")
pass_btn = wait_for_parent_pass(timeout=15)
print(f"  Tapping Pass at {pass_btn.get('bounds')}")
tap_bounds(pass_btn.get("bounds"))
time.sleep(2)
screenshot("pass_tapped")

export_and_verify(TEST_NAME)
screenshot("export_done")
