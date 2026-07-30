#!/usr/bin/env python3
"""
Has Vibrator Test (VIBRATIONS section)
UI flow:
  1. Tap 'Vibrate' button
  2. 'Did the device vibrate?' appears — tap 'Yes'
  3. Pass button becomes enabled — tap it
  4. Export via DPAD overflow-menu navigation
  5. Unzip result and verify test_result.xml shows pass

Screenshots are saved to ./cts_screenshots/vibrations/<step>_<desc>.png
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
    ui_dump, find_node, find_node_containing, tap, wait_for, tap_pass,
    screenshot, set_screenshot_dir,
    export_and_verify
)

TEST_NAME  = "Has Vibrator Test"
OUTPUT_DIR = os.environ.get("CTS_OUTPUT_DIR", "/tmp")

set_screenshot_dir("vibrations")

# ── Export helper (DPAD — popup not captured by uiautomator dump) ──────────────

def ensure_on_main_list():
    for _ in range(6):
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
screenshot("has_vibrator_test_detail")

# Tap Vibrate
print("Tapping 'Vibrate'...")
screenshot("tapping_vibrate")
root = ui_dump()
vibrate_btn = find_node(root, text="Vibrate")
if vibrate_btn is None:
    raise RuntimeError("'Vibrate' button not found")
tap(vibrate_btn)
time.sleep(2)
screenshot("vibrate_tapped_did_it_vibrate_question")

# Tap 'Yes' for "Did the device vibrate?"
print("Answering 'Yes' to 'Did the device vibrate?'...")
screenshot("answering_yes_to_did_the_device_vibrate")
root = ui_dump()
yes_nodes = [n for n in root.iter("node") if n.get("text") == "Yes"]
# The second Yes answers "Did the device vibrate?" (first Yes = API response)
answer_yes = yes_nodes[-1] if len(yes_nodes) >= 2 else yes_nodes[0]
tap(answer_yes)
time.sleep(2)
screenshot("yes_tapped_pass_now_enabled")

# Tap Pass
print("Tapping Pass...")
screenshot("tapping_pass")
pass_btn = wait_for(content_desc="Pass", timeout=10)
tap_pass(pass_btn)
time.sleep(2)
screenshot("pass_tapped")

export_and_verify(TEST_NAME)
screenshot("export_done")
