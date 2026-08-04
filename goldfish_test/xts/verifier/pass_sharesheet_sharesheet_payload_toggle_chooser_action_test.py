#!/usr/bin/env python3
"""
Sharesheet Payload Toggle Chooser Action Test
Taps Share to open the chooser, selects all 3 images (by tapping each
"Selectable image" item), then taps the "Test Action" chooser action.
The test auto-passes on completion.

Flow:
  1. setup() + navigate_to "Sharesheet Payload Toggle Chooser Action Test"
  2. Dismiss OK if present
  3. Tap Share button
  4. Chooser opens with 3 selectable images in a horizontal carousel + "Test Action"
  5. Tap all 3 "Selectable image" items (the center item may already be selected,
     but tap all to ensure correct state)
  6. Tap "Test Action" button (find by text; touch propagates to clickable parent)
  7. Test auto-passes and returns to main list
  8. Export ZIP and verify test_result.xml

Screenshots saved to ./cts_screenshots/sharesheet_ptca/<step>_<desc>.png
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

TEST_NAME  = "Sharesheet Payload Toggle Chooser Action Test"
set_screenshot_dir("sharesheet_payload_toggle_chooser_action_test")

OUTPUT_DIR = os.environ.get("CTS_OUTPUT_DIR", "/tmp")





def tap_bounds(b):
    nums = [int(x) for x in b.replace("][", ",").strip("[]").split(",")]
    x, y = (nums[0] + nums[2]) // 2, (nums[1] + nums[3]) // 2
    adb("shell", "input", "tap", str(x), str(y))
    time.sleep(1.5)


def find_selectable_item(root, name):
    """Find a specific 'Selectable image' node by name (e.g. 'Item 3')."""
    for n in root.iter("node"):
        if n.get("content-desc", "").startswith(name):
            return n
    return None


def long_press(x, y, duration_ms=800):
    """Simulate a long press via a stationary swipe."""
    adb("shell", "input", "swipe", str(x), str(y), str(x), str(y), str(duration_ms))
    time.sleep(1.5)


def get_screen_size():
    """Return (width, height) in pixels from `adb shell wm size`."""
    out = adb("shell", "wm", "size")
    m = re.search(r"(\d+)x(\d+)", out)
    return (int(m.group(1)), int(m.group(2))) if m else (1080, 2400)


def find_test_action(root):
    """Find the Test Action button in the chooser."""
    for n in root.iter("node"):
        if n.get("text") == "Test Action" and n.get("enabled") == "true":
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

# Select all 3 images using long press.
# Item 2 starts pre-selected (checked=true). Long pressing Item 1 selects it while
# keeping Item 2 selected. Then swipe left to reveal Item 3, long press Item 3.
screen_w, _ = get_screen_size()

root = ui_dump()
item1 = find_selectable_item(root, "Item 1")
if item1 is None:
    time.sleep(1)
    root = ui_dump()
    item1 = find_selectable_item(root, "Item 1")
if item1 is None:
    raise RuntimeError("Item 1 not found in chooser dump")
b = item1.get("bounds")
nums = [int(x) for x in b.replace("][", ",").strip("[]").split(",")]
cx, cy = (nums[0]+nums[2])//2, (nums[1]+nums[3])//2
item1_cy = cy
print(f"Long pressing Item 1 at ({cx}, {cy})...")
long_press(cx, cy)

screenshot("item1_selected")

# Swipe left to bring Item 3 into view; keep y at Item 1 center, scale x to screen width
print("Swiping left to reveal Item 3...")
adb("shell", "input", "swipe",
    str(int(screen_w * 0.74)), str(item1_cy),
    str(int(screen_w * 0.19)), str(item1_cy), "300")
time.sleep(2)

root = ui_dump()
item3 = find_selectable_item(root, "Item 3")
if item3 is None:
    time.sleep(1)
    root = ui_dump()
    item3 = find_selectable_item(root, "Item 3")
if item3 is None:
    raise RuntimeError("Item 3 not found in chooser dump after swipe")
b = item3.get("bounds")
nums = [int(x) for x in b.replace("][", ",").strip("[]").split(",")]
cx, cy = (nums[0]+nums[2])//2, (nums[1]+nums[3])//2
print(f"Long pressing Item 3 at ({cx}, {cy})...")
long_press(cx, cy)

screenshot("items_selected")

# Tap Test Action
root = ui_dump()
action_btn = find_test_action(root)
if action_btn is None:
    raise RuntimeError("Test Action not found in chooser dump")
print(f"Tapping Test Action at {action_btn.get('bounds')}")
tap_bounds(action_btn.get("bounds"))

time.sleep(2)
screenshot("after_action")

export_and_verify(TEST_NAME)
screenshot("export_done")
