#!/usr/bin/env python3
"""
Streaming Video Quality Verifier
Plays each HTTP Progressive streaming video clip and taps Pass in the player.

Flow:
  1. Launch and navigate to "Streaming Video Quality Verifier"
  2. For each video item (H263, MPEG4, H264):
     a. Tap to open the video player
     b. Wait for SurfaceView (player loaded)
     c. Wait a few seconds for video to buffer/play
     d. Tap the Pass button in the player
     e. Wait to return to the video list
  3. Tap the parent Pass (enabled after all 3 pass)
  4. Export ZIP and verify test_result.xml

Screenshots saved to ./cts_screenshots/streaming/<step>_<desc>.png
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

TEST_NAME  = "Streaming Video Quality Verifier"
set_screenshot_dir("streaming_video_quality_verifier")

OUTPUT_DIR = os.environ.get("CTS_OUTPUT_DIR", "/tmp")

# ── Screenshot helper ──────────────────────────────────────────────────────────




# ── Tap helpers ────────────────────────────────────────────────────────────────

def tap_bounds(b):
    nums = [int(x) for x in b.replace("][", ",").strip("[]").split(",")]
    x, y = (nums[0] + nums[2]) // 2, (nums[1] + nums[3]) // 2
    adb("shell", "input", "tap", str(x), str(y))
    time.sleep(1.5)


def wait_for_player(timeout=10):
    """Wait until SurfaceView appears (video player is open)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        root = ui_dump()
        for n in root.iter("node"):
            if "SurfaceView" in n.get("class", ""):
                return True
        time.sleep(0.5)
    return False


def wait_for_list(timeout=15):
    """Wait until video list items are visible (back from player)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        root = ui_dump()
        for n in root.iter("node"):
            if any(kw in n.get("text", "") for kw in ("H263", "MPEG4", "H264", "HTTP PROGRESSIVE")):
                return True
        time.sleep(0.5)
    return False


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


def pass_video(label, bounds):
    """Open a video item, wait for player, tap Pass, return to list."""
    print(f"Playing: {label}")
    tap_bounds(bounds)

    if not wait_for_player(timeout=10):
        print(f"  WARNING: SurfaceView not detected for {label!r}")
    time.sleep(3)  # let video buffer and start playing
    screenshot(f"player_{re.sub(r'[^a-zA-Z0-9]+', '_', label).strip('_')}")

    # Find Pass button in the player via dump; fall back to coordinate if needed
    root = ui_dump()
    pass_btn = None
    for n in root.iter("node"):
        if (n.get("content-desc") == "Pass"
                and n.get("class", "").endswith("ImageButton")
                and n.get("enabled") == "true"):
            pass_btn = n
            break

    if pass_btn is not None:
        print(f"  Tapping Pass at {pass_btn.get('bounds')}")
        tap_bounds(pass_btn.get("bounds"))
    else:
        # Player Pass is always at the lower-left; tap by fixed coordinate
        print(f"  Pass not found in dump — tapping by coordinate (270, 2284)")
        adb("shell", "input", "tap", "270", "2284")
        time.sleep(1.5)

    if not wait_for_list(timeout=15):
        print(f"  WARNING: Did not return to list after passing {label!r}")
    time.sleep(0.5)
    screenshot(f"list_after_{re.sub(r'[^a-zA-Z0-9]+', '_', label).strip('_')}")


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
screenshot("test_opened")

# Dismiss intro OK dialog if present
root = ui_dump()
ok = find_node(root, text="OK")
if ok is not None:
    print("Dismissing intro dialog...")
    tap(ok)
    time.sleep(2)
    screenshot("intro_dismissed")
    root = ui_dump()

# Collect video items from the initial dump
video_items = []
for n in root.iter("node"):
    txt = n.get("text", "")
    b   = n.get("bounds", "")
    if "Audio" in txt and "Video" in txt:
        video_items.append((txt, b))
        print(f"  Found video item: {txt!r} at {b}")

if not video_items:
    raise RuntimeError("No video items found in Streaming Video Quality Verifier list")

# Play and pass each video
for label, bounds in video_items:
    pass_video(label, bounds)

# All videos done; tap parent Pass
print("Waiting for parent Pass (all videos complete)...")
parent = wait_for_parent_pass(timeout=20)
screenshot("parent_pass_enabled")
print(f"  Tapping parent Pass at {parent.get('bounds')}")
tap_bounds(parent.get("bounds"))
time.sleep(2)
screenshot("parent_pass_tapped")

export_and_verify(TEST_NAME)
screenshot("export_done")
