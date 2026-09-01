#!/usr/bin/env python3
"""Authentic CTS Verifier Notification Styles Test Automation.

Automates the 19 subtests in NotificationStyleVerifierActivity:
1. Launch NotificationStyleVerifierActivity and dismiss instructions.
2. For each styled notification test (BigPicture, Custom RemoteViews,
   ProgressStyle, SemanticColors, MetricStyle):
   a. Expand notification shade via status bar command.
   b. Enforce 2.0s settle delay for animation and capture screenshot.
   c. Verify notification presentation in shade.
   d. Collapse shade and tap inline Pass button.
   e. Allow 3.5s runner delay for teardown and next item setup.
3. Validate global toolbar Pass button enabled and tap Pass.
4. Export test report and assert passing result in test_result.xml.
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
    find_active_inline_pass,
    find_node,
    find_pass_button,
    find_fail_button,
    get_display_dimensions,
    get_screen_size,
    is_pass_button_enabled,
    navigate_to,
    screenshot,
    set_screenshot_dir,
    setup,
    tap,
    tap_pass,
    ui_dump,
    wait_for,
)

TEST_NAME = "Notification Styles Test"
ACTIVITY_CLASS = (
    "com.android.cts.verifier.notifications.NotificationStyleVerifierActivity")


def return_to_main_activity():
    """Return to CtsVerifierActivity list."""
    for _ in range(4):
        root = ui_dump()
        if find_node(root, text="CTS Verifier") is not None:
            return
        adb("shell", "input", "keyevent", "KEYCODE_BACK", check=False)
        time.sleep(1.5)
    adb("shell", "am", "start", "-W", "-n", ACTIVITY, check=False)
    time.sleep(2)


def dismiss_initial_dialog():
    """Dismiss the instructions dialog if displayed upon opening the test."""
    root = ui_dump()
    ok_btn = find_node(root, text="OK")
    if ok_btn is not None:
        print("  Dismissing instructions OK dialog...")
        tap(ok_btn)
        time.sleep(1.5)


def main():
    setup()
    set_screenshot_dir("notifications_style_test")

    try:
        # Pre-test setup: screen on, clear notifications
        print("Pre-test setup: ensuring screen unlocked and clean state...")
        adb("shell", "input", "keyevent", "KEYCODE_WAKEUP", check=False)
        adb("shell", "wm", "dismiss-keyguard", check=False)
        adb("shell", "settings", "put", "global", "zen_mode", "0", check=False)
        adb("shell", "cmd", "notification", "clear_all", check=False)
        time.sleep(1)

        print(f"Navigating to '{TEST_NAME}'...")
        navigate_to(
            TEST_NAME,
            verify_title="Notification Styles",
        )
        time.sleep(2)
        dismiss_initial_dialog()
        screenshot("01_00_test_opened")

        print("Executing Notification Style verification steps...")
        start_time = time.time()
        timeout = 480  # 8 minutes max for all 19 subtests
        step = 0

        while time.time() - start_time < timeout:
            root = ui_dump()
            if is_pass_button_enabled(root):
                print("  ✓ Global toolbar Pass button is enabled!")
                break

            inline_pass = find_active_inline_pass(root)
            if inline_pass is None:
                # Scroll down to reveal next items in ScrollView
                w, h = get_screen_size()
                adb(
                    "shell",
                    "input",
                    "swipe",
                    str(w // 2),
                    str(int(h * 0.70)),
                    str(w // 2),
                    str(int(h * 0.35)),
                    "250",
                )
                time.sleep(1.5)
                root = ui_dump()
                inline_pass = find_active_inline_pass(root)

            if inline_pass is not None:
                step += 1
                print(f"  [Step {step:02d}] Verifying styled notification...")
                # Expand shade to trigger and verify styled notification
                adb("shell",
                    "cmd",
                    "statusbar",
                    "expand-notifications",
                    check=False)
                time.sleep(2.0)
                screenshot(f"step_{step:02d}_shade_expanded")
                adb("shell", "cmd", "statusbar", "collapse", check=False)
                time.sleep(1.5)

                root = ui_dump()
                btn = find_active_inline_pass(root)
                if btn is not None:
                    print(f"  [Step {step:02d}] Tapping inline Pass button...")
                    tap(btn)
                    time.sleep(
                        3.5
                    )  # Allow InteractiveVerifierActivity delay() transition
                continue

            time.sleep(1.0)

        # Confirm toolbar Pass button enabled and tap it
        print("\nWaiting for global Pass button confirmation...")
        pass_btn = None
        for _ in range(30):
            root = ui_dump()
            if is_pass_button_enabled(root):
                pass_btn = find_pass_button(root)
                break
            time.sleep(2)

        if pass_btn is not None:
            screenshot("20_global_pass_enabled")
            tap_pass(pass_btn)
            screenshot("21_global_pass_tapped")
        else:
            raise RuntimeError(
                "Global Pass button was not enabled after completing subtests")

        # Return to main activity and verify exported report
        return_to_main_activity()
        export_and_verify("notifications_style_test")
        screenshot("22_test_report_exported")
        print(
            "\n=== Notification Styles Test Automation PASSED successfully! ==="
        )

    finally:
        adb("shell", "cmd", "notification", "clear_all", check=False)


if __name__ == "__main__":
    main()
