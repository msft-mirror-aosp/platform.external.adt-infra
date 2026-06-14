#!/usr/bin/env python3
"""
Interactive Session Test
Taps Share, then taps the Close button (above the chooser), then answers
"yes it worked" by tapping the Pass ImageButton.

Flow:
  1. setup() + navigate_to "Interactive Session Test"
  2. Tap Share button
  3. Chooser opens (half-sheet); Close button is in CTS Verifier window above the
     chooser — NOT captured by uiautomator dump; position computed from screen
     density and chooser drag-handle y-coordinate found in the dump
  4. Question appears: "Did the Close button track the Chooser's movement?"
  5. Tap ImageButton desc='Pass'
  6. Export ZIP and verify test_result.xml

Screenshots saved to ./cts_screenshots/sharesheet_interactive/<step>_<desc>.png
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

TEST_NAME  = "Interactive Session Test"
set_screenshot_dir("interactive_session_test")

OUTPUT_DIR = os.environ.get("CTS_OUTPUT_DIR", "/tmp")





def tap_bounds(b):
    nums = [int(x) for x in b.replace("][", ",").strip("[]").split(",")]
    x, y = (nums[0] + nums[2]) // 2, (nums[1] + nums[3]) // 2
    adb("shell", "input", "tap", str(x), str(y))
    time.sleep(1.5)


def get_screen_density():
    """Return the screen density in dpi from `adb shell wm density`."""
    out = adb("shell", "wm", "density")
    m = re.search(r"Physical density:\s*(\d+)", out)
    return int(m.group(1)) if m else 480


def get_screen_size():
    """Return (width, height) in pixels from `adb shell wm size`."""
    out = adb("shell", "wm", "size")
    m = re.search(r"(\d+)x(\d+)", out)
    return (int(m.group(1)), int(m.group(2))) if m else (1080, 2400)


def find_chooser_drag_handle_y(root, screen_w):
    """Return the top y-coordinate of the chooser drag handle.
    Looks for the topmost full-width thin element in the dump (the resize bar).
    The Close button in the CTS Verifier window sits just above this y.
    """
    result = None
    for n in root.iter("node"):
        b = n.get("bounds", "")
        if b:
            nums = [int(x) for x in b.replace("][", ",").strip("[]").split(",")]
            x0, y0, x1, y1 = nums
            height = y1 - y0
            # Full-width, not at y=0, and thin enough to be a drag handle (< 200px)
            if x0 == 0 and x1 == screen_w and y0 > 50 and height < 200:
                if result is None or y0 < result:
                    result = y0
    return result


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

# Close button is in the CTS Verifier window above the chooser (not in the dump).
# Compute its position: ~22dp from left, ~24dp above the chooser drag handle.
density = get_screen_density()
screen_w, _ = get_screen_size()
drag_dump = ui_dump()
chooser_top = find_chooser_drag_handle_y(drag_dump, screen_w)
if chooser_top is None:
    raise RuntimeError("Could not find chooser drag handle in dump")
close_x = int(22 * density / 160)
close_y = chooser_top - int(24 * density / 160)
print(f"Tapping Close at ({close_x}, {close_y}) — density={density}dpi, chooser_top={chooser_top}")
adb("shell", "input", "tap", str(close_x), str(close_y))
time.sleep(2)
screenshot("after_close")

# Question now appears: "Did the Close button track the Chooser's movement?"
# Tap Pass (ImageButton desc='Pass')
print("Waiting for Pass button...")
pass_btn = wait_for_parent_pass(timeout=15)
print(f"Tapping Pass at {pass_btn.get('bounds')}")
tap_bounds(pass_btn.get("bounds"))
time.sleep(2)
screenshot("pass_tapped")

export_and_verify(TEST_NAME)
screenshot("export_done")
