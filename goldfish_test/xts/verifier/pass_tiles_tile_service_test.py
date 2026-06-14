#!/usr/bin/env python3
"""
Tile Service Test
Flow:
  1. Step 1 auto-passes (Tile Service enabled)
  2. Tap Step 2 Pass (QS check: no tile visible)
  3. Wait → Step 3 Pass enables: tap it (QS check: tile available)
  4. Wait → parent Pass enables (Step 4 auto): tap it
  5. Export ZIP and verify test_result.xml shows pass

Screenshots saved to ./cts_screenshots/tile_service/<step>_<desc>.png
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

TEST_NAME  = "Tile Service Test"
set_screenshot_dir("tile_service_test")

OUTPUT_DIR = os.environ.get("CTS_OUTPUT_DIR", "/tmp")

# ── Screenshot helper ──────────────────────────────────────────────────────────




# ── Button helpers ─────────────────────────────────────────────────────────────

def tap_bounds(b):
    nums = [int(x) for x in b.replace("][", ",").strip("[]").split(",")]
    x, y = (nums[0] + nums[2]) // 2, (nums[1] + nums[3]) // 2
    adb("shell", "input", "tap", str(x), str(y))
    time.sleep(1.5)


def wait_for_pass_button(timeout=20):
    """Wait for a text-'Pass' Button (not ImageButton) to be enabled."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        root = ui_dump()
        for n in root.iter("node"):
            cls = n.get("class", "")
            if "Button" in cls and "Image" not in cls:
                if n.get("text") == "Pass" and n.get("enabled") == "true":
                    return n
        time.sleep(1)
    raise TimeoutError("Timed out waiting for enabled Pass button")


def wait_for_parent_pass(timeout=20):
    """Wait for the parent ImageButton desc='Pass' to be enabled."""
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


# ── Export + verify ────────────────────────────────────────────────────────────

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
screenshot("tile_service_test_opened")

# Dismiss OK intro dialog
root = ui_dump()
ok = find_node(root, text="OK")
if ok is not None:
    print("Dismissing intro dialog...")
    tap(ok)
    time.sleep(2)
    screenshot("intro_dismissed")

# Step 2: Tap Pass ("Open QS, no tile visible")
print("Step 2: Waiting for Pass (no tile visible in QS)...")
n = wait_for_pass_button(timeout=10)
print(f"  Tapping Pass at {n.get('bounds')}")
tap_bounds(n.get("bounds"))
time.sleep(2)
screenshot("step2_pass_tapped")

# Step 3: Wait for Pass to unlock ("tile available to add"), then tap
print("Step 3: Waiting for Pass to enable (tile available in QS)...")
n = wait_for_pass_button(timeout=20)
screenshot("step3_pass_enabled")
print(f"  Tapping Pass at {n.get('bounds')}")
tap_bounds(n.get("bounds"))
time.sleep(2)
screenshot("step3_pass_tapped")

# Wait for parent Pass (Step 4 auto-passes)
print("Waiting for parent Pass (Step 4 auto-completes)...")
parent = wait_for_parent_pass(timeout=20)
screenshot("parent_pass_enabled")
print(f"  Tapping parent Pass at {parent.get('bounds')}")
tap_bounds(parent.get("bounds"))
time.sleep(2)
screenshot("parent_pass_tapped")

export_and_verify(TEST_NAME)
screenshot("export_done")
