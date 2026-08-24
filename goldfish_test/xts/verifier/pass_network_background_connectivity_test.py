#!/usr/bin/env python3
"""Authentic CTS Verifier Network Background Connectivity Test Automation.

Tests background IPv6 connectivity:
1. Open ConnectivityBackgroundTestActivity and dismiss instructions dialog.
2. Tap "Start Test" to initiate background connectivity probing.
3. Simulate battery unplug and turn the screen off to trigger idle state.
4. Wait for background HTTP/IPv6 checks to complete.
5. Turn screen back on, dismiss keyguard, and reset battery simulation.
6. Verify toolbar Pass button enabled and tap Pass.
7. Export test report and assert passing result in test_result.xml.
"""

import os
import sys
import time

try:
    sys.stdout.reconfigure(line_buffering=True)
except (AttributeError, TypeError):
    pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from cts_common import (
    ACTIVITY,
    adb,
    export_and_verify,
    find_any_node,
    find_node,
    navigate_to,
    set_screenshot_dir,
    setup,
    tap,
    tap_pass,
    ui_dump,
    wait_for,
)

TEST_NAME = "Network Background Connectivity Test"
ACTIVITY_CLASS = "com.android.cts.verifier.net.ConnectivityBackgroundTestActivity"


def dismiss_initial_dialog():
    """Dismiss instructions dialog if displayed."""
    root = ui_dump()
    ok_btn = find_any_node(root, [("text", "OK"), ("text", "Ok"), ("text", "ok")])
    if ok_btn is not None:
        print("  Dismissing instructions OK dialog...")
        tap(ok_btn)
        time.sleep(1.5)


def locate_start_button(root):
    """Locate Start Test button."""
    btn = find_any_node(
        root,
        [
            ("resource_id", "com.android.cts.verifier:id/start_test"),
            ("text", "Start Test"),
            ("text", "Start test"),
            ("text", "START TEST"),
            ("text", "Start"),
        ],
    )
    if btn is not None:
        return btn
    for n in root.iter("node"):
        txt = (n.attrib.get("text") or "").upper()
        if "START" in txt:
            return n
    return None


def main():
    setup()
    set_screenshot_dir("network_background_connectivity_test")

    try:
        print("Pre-test setup: ensuring screen unlocked and Wi-Fi active...")
        adb("shell", "input", "keyevent", "KEYCODE_WAKEUP", check=False)
        adb("shell", "wm", "dismiss-keyguard", check=False)
        adb("shell", "svc", "wifi", "enable", check=False)
        time.sleep(2)

        navigate_to(TEST_NAME, verify_title="Network Background")
        time.sleep(2)
        dismiss_initial_dialog()

        root = ui_dump()
        start_btn = locate_start_button(root)
        if start_btn is not None:
            print("  Tapping Start Test...")
            tap(start_btn)
            time.sleep(2)

        # Trigger screen off & battery unplug simulation
        print("  Simulating battery unplug and turning screen off...")
        adb("shell", "dumpsys", "battery", "unplug", check=False)
        adb("shell", "input", "keyevent", "KEYCODE_POWER", check=False)
        # Step device idle to run background tasks
        adb("shell", "dumpsys", "deviceidle", "step", "deep", check=False)

        print("  Waiting 20 seconds for background connectivity checks...")
        time.sleep(20)

        print("  Waking screen and resetting battery status...")
        adb("shell", "input", "keyevent", "KEYCODE_WAKEUP", check=False)
        adb("shell", "wm", "dismiss-keyguard", check=False)
        adb("shell", "dumpsys", "battery", "reset", check=False)
        time.sleep(3)

        print("Waiting for Pass button to become enabled...")
        pass_btn = wait_for(content_desc="Pass", timeout=60)
        if pass_btn.attrib.get("enabled") != "true":
            raise AssertionError(
                "CTS Verifier did not pass: Pass button remains disabled after background execution"
            )
        tap_pass(pass_btn)
        time.sleep(2)

        print("Exporting and validating test report...")
        export_and_verify(ACTIVITY_CLASS)
        print(">>> Network Background Connectivity Test PASSED authentically!")
        return 0

    finally:
        adb("shell", "dumpsys", "battery", "reset", check=False)
        adb("shell", "input", "keyevent", "KEYCODE_WAKEUP", check=False)
        adb("shell", "wm", "dismiss-keyguard", check=False)


if __name__ == "__main__":
    sys.exit(main())
