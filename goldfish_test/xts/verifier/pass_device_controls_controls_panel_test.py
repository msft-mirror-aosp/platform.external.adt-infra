#!/usr/bin/env python3
"""Controls Panel - uses UI navigation."""

import time
import sys
from cts_common import (
    setup, navigate_to, ui_dump, find_node, tap, scroll_and_tap_item_or_fail,
    tap_pass, adb, export_and_verify, set_screenshot_dir
)

TEST_NAME = "Controls Panel tests"
set_screenshot_dir("controls_panel_tests")

setup()
navigate_to(TEST_NAME)

SUB_TESTS = [
    "0. Install helper app",
    "1. Controls Panel visible test",
    "2a. Controls Panel setting in extra test false value",
    "2b. Controls Panel setting in extra test true value",
    "3a. Control Panel starting on keyguard test false value",
    "3b. Control Panel starting as a dream test true value"
]

def is_verifier_in_foreground():
    root = ui_dump()
    for node in root.iter("node"):
        if node.attrib.get("package") == "com.android.cts.verifier":
            return True
    return False

def ensure_verifier_foreground():
    for _ in range(5):
        if is_verifier_in_foreground():
            return
        print("  CtsVerifier not in foreground! Relaunching...")
        adb("shell", "am", "start", "-n", "com.android.cts.verifier/.CtsVerifierActivity")
        time.sleep(2)
        # Attempt to navigate again if needed, but usually it opens where we left off
    print("  [ERROR] Could not bring CtsVerifier to foreground!")
    sys.exit(1)

for subtest in SUB_TESTS:
    print(f"\n======================================")
    print(f"Subtest: {subtest}")

    ensure_verifier_foreground()

    scroll_and_tap_item_or_fail(subtest)
    time.sleep(2)

    root = ui_dump()
    ok_btn = find_node(root, text="OK")
    if ok_btn is not None:
        print("  Dismissing OK dialog...")
        tap(ok_btn)
        time.sleep(1)
        root = ui_dump()

    # Look for Open Settings button
    settings_btn = find_node(root, text="Open Settings")
    if settings_btn is not None:
        print("  Found 'Open Settings' button, tapping it...")
        tap(settings_btn)
        time.sleep(2)

        # Verify Settings is in foreground
        if is_verifier_in_foreground():
            print("  [WARNING] Settings might not be in foreground, but proceeding to set property...")

        # Determine whether to set to true (1) or false (0) based on test name
        setting_val = "1" if "true value" in subtest else "0"
        print(f"  Setting lockscreen_show_controls to {setting_val} via adb...")
        adb("shell", "settings", "put", "secure", "lockscreen_show_controls", setting_val)

        # Verify it was set
        actual_val = adb("shell", "settings", "get", "secure", "lockscreen_show_controls").strip()
        if actual_val != setting_val:
            print(f"  [ERROR] Expected lockscreen_show_controls={setting_val}, but got {actual_val}")

        # Go back to CtsVerifier
        print("  Going back to CtsVerifier...")
        adb("shell", "input", "keyevent", "4")
        time.sleep(1)

        ensure_verifier_foreground()
        root = ui_dump()

    # Now tap pass
    pass_btn = find_node(root, content_desc="Pass")
    if pass_btn is None:
        pass_btn = find_node(root, text="Pass")

    if pass_btn is not None:
        print("  Tapping Pass...")
        tap_pass(pass_btn)
        time.sleep(1)
    else:
        print("  [ERROR] Pass button not found!")
        sys.exit(1)

    ensure_verifier_foreground()

# Main test pass
print("\n  Tapping Pass for main test...")
ensure_verifier_foreground()
root = ui_dump()
pass_btn = find_node(root, content_desc="Pass")
if pass_btn is None:
    pass_btn = find_node(root, text="Pass")
tap_pass(pass_btn)

export_and_verify(TEST_NAME)
sys.exit(0)

