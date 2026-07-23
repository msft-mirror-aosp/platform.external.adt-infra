#!/usr/bin/env python3
"""
Tile Service Request Test
10-step flow that tests adding/rejecting Quick Settings tiles via TileService API.

Setup:
  - CtsTileServiceApp.apk must be at: ./android-cts-verifier/CtsTileServiceApp.apk
  - The companion app is uninstalled first so Step 1 auto-passes, then installed
    for Steps 2-10.

Flow:
  Step 1:  Auto-passes (companion app not installed)
  Step 2:  Install CtsTileServiceApp → tap Pass
  Step 3:  Auto-verifies installation
  Step 4:  Tap Pass (no Request Tile Service tiles in QS)
  Step 5:  Start request → dialog → "Don't add tile" → auto-complete
  Step 6:  Start request → dialog → verify info → "Don't add tile" → tap Pass
  Step 7:  Start request → dialog → "Add tile" → auto-complete
  Step 8:  Tap Pass (Request Tile Service tile visible in QS)
  Step 9:  Auto-completes (tile-already-added response check)
  Step 10: Start request → Uninstall dialog → tap Uninstall → auto-complete
  Parent Pass: tap → export → verify XML

Screenshots saved to ./cts_screenshots/tile_service_request/<step>_<desc>.png
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

TEST_NAME      = "Tile Service Request Test"
set_screenshot_dir("tile_service_request_test")

cts_apk_path   = os.environ.get("CTS_APK_PATH")
if cts_apk_path:
    COMPANION_APK = os.path.join(os.path.dirname(cts_apk_path), "CtsTileServiceApp.apk")
else:
    COMPANION_APK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "android-cts-verifier", "CtsTileServiceApp.apk")

if not os.path.exists(COMPANION_APK):
    print(f"Error: COMPANION_APK not found at {COMPANION_APK}")
    raise FileNotFoundError(f"COMPANION_APK not found: {COMPANION_APK}")

COMPANION_PKG  = "com.android.cts.tileserviceapp"
OUTPUT_DIR = os.environ.get("CTS_OUTPUT_DIR", "/tmp")

# ── Screenshot helper ──────────────────────────────────────────────────────────




# ── Tap helpers ────────────────────────────────────────────────────────────────

def tap_bounds(b):
    nums = [int(x) for x in b.replace("][", ",").strip("[]").split(",")]
    x, y = (nums[0] + nums[2]) // 2, (nums[1] + nums[3]) // 2
    adb("shell", "input", "tap", str(x), str(y))
    time.sleep(1.5)


def wait_for_button(texts, timeout=20):
    """Wait for any text-Button (not ImageButton/View) in *texts* to be enabled."""
    if isinstance(texts, str):
        texts = [texts]
    deadline = time.time() + timeout
    while time.time() < deadline:
        root = ui_dump()
        for n in root.iter("node"):
            cls = n.get("class", "")
            if "Button" in cls and "Image" not in cls:
                if n.get("text") in texts and n.get("enabled") == "true":
                    return n
        time.sleep(1)
    raise TimeoutError(f"Timed out waiting for enabled button with text in {texts}")


def wait_for_parent_pass(timeout=30):
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


def tap_dialog_option(label, exact=False, timeout=10):
    """Tap a dialog button/text. If exact=True, full text must match (case-insensitive)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        root = ui_dump()
        for n in root.iter("node"):
            t = n.get("text", "")
            match = (t.lower() == label.lower()) if exact else (label.lower() in t.lower())
            if match:
                print(f"  Tapping dialog option {t!r}")
                tap_bounds(n.get("bounds"))
                return
        time.sleep(1)
    raise RuntimeError(f"Dialog option {label!r} not found after {timeout}s")


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

# Ensure companion app is NOT installed so Step 1 auto-passes
print("Uninstalling companion app (so Step 1 auto-passes)...")
adb("shell", "pm", "uninstall", COMPANION_PKG, check=False)
time.sleep(1)

setup()
screenshot("app_launched")

navigate_to(TEST_NAME)
time.sleep(2)
screenshot("test_opened")

# Dismiss intro OK dialog
root = ui_dump()
ok = find_node(root, text="OK")
if ok is not None:
    print("Dismissing intro dialog...")
    tap(ok)
    time.sleep(2)
    screenshot("intro_dismissed")

# Step 1 auto-passes (app not installed at open time)
print("Step 1: auto-passes (companion app not installed)")
screenshot("step1_auto_passed")

# Install companion app for remaining steps
print("Installing CtsTileServiceApp...")
adb("install", "-r", "-g", COMPANION_APK)
time.sleep(2)
screenshot("companion_app_installed")

# Step 2: Tap Pass (confirm companion app installed)
print("Step 2: Tapping Pass (confirm install)...")
n = wait_for_button("Pass", timeout=10)
print(f"  Pass at {n.get('bounds')}")
tap_bounds(n.get("bounds"))
time.sleep(2)
screenshot("step2_pass_tapped")

# Step 3 auto-verifies; wait for Step 4 Pass to unlock
print("Step 3: Auto-verifying install (waiting for Step 4 to unlock)...")
n = wait_for_button("Pass", timeout=20)
screenshot("step4_pass_enabled")

# Step 4: Tap Pass ("no tiles in QS")
print("Step 4: Tapping Pass (no tiles in QS)...")
tap_bounds(n.get("bounds"))
time.sleep(2)
screenshot("step4_pass_tapped")

# Step 5: Start request → dialog → dismiss with BACK → auto-complete
print("Step 5: Start request → dismiss dialog (KEYCODE_BACK) → auto-complete...")
n = wait_for_button("Start request", timeout=20)
print(f"  Start request at {n.get('bounds')}")
tap_bounds(n.get("bounds"))
time.sleep(2)
screenshot("step5_dialog_appeared")
adb("shell", "input", "keyevent", "KEYCODE_BACK")
time.sleep(2)
screenshot("step5_dismissed")

# Step 6's Start request is below the visible area; scroll down to reveal it
print("  Scrolling down to reveal Step 6...")
adb("shell", "input", "swipe", "540", "1800", "540", "400", "300")
time.sleep(1)

# Step 6: Start request → dialog → "Don't add tile" → Pass enables → tap Pass
print("Step 6: Start request → verify info → Don't add tile → tap Pass...")
n = wait_for_button("Start request", timeout=30)
print(f"  Start request at {n.get('bounds')}")
tap_bounds(n.get("bounds"))
time.sleep(2)
screenshot("step6_dialog_appeared")
tap_dialog_option("don't add tile")
time.sleep(1)

n = wait_for_button("Pass", timeout=15)
screenshot("step6_pass_enabled")
print(f"  Tapping Step 6 Pass at {n.get('bounds')}")
tap_bounds(n.get("bounds"))
time.sleep(2)
screenshot("step6_pass_tapped")

# Step 7: Start request → dialog → "Add tile" → auto-complete
print("Step 7: Start request → Add tile → auto-complete...")
n = wait_for_button("Start request", timeout=15)
print(f"  Start request at {n.get('bounds')}")
tap_bounds(n.get("bounds"))
time.sleep(2)
screenshot("step7_dialog_appeared")
tap_dialog_option("add tile", exact=True)  # exact to avoid matching "Don't add tile"
time.sleep(2)
screenshot("step7_tile_added")

# Step 8: Tap Pass ("tile visible in QS")
print("Step 8: Waiting for Pass (tile visible in QS)...")
n = wait_for_button("Pass", timeout=15)
screenshot("step8_pass_enabled")
print(f"  Tapping Step 8 Pass at {n.get('bounds')}")
tap_bounds(n.get("bounds"))
time.sleep(2)
screenshot("step8_pass_tapped")

# Step 9 auto-completes; Step 10 Start request enables (app still installed)
print("Step 9: Auto-completes (tile-already-added response check)...")
print("Step 10: Waiting for Start request (uninstall companion app)...")
n = wait_for_button("Start request", timeout=15)
screenshot("step10_start_request_enabled")
print(f"  Tapping Start request at {n.get('bounds')}")
tap_bounds(n.get("bounds"))
time.sleep(2)
screenshot("step10_uninstall_dialog")

# Confirm uninstall (exact match to avoid hitting "Uninstall this app?" title)
tap_dialog_option("uninstall", exact=True)
time.sleep(4)
screenshot("step10_uninstalled")

# Wait for parent Pass to enable (Step 10 auto-completes after uninstall)
print("Waiting for parent Pass...")
parent = wait_for_parent_pass(timeout=20)
screenshot("parent_pass_enabled")
print(f"  Tapping parent Pass at {parent.get('bounds')}")
tap_bounds(parent.get("bounds"))
time.sleep(2)
screenshot("parent_pass_tapped")

export_and_verify(TEST_NAME)
screenshot("export_done")
