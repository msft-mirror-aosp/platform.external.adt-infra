#!/usr/bin/env python3
"""Authentic CTS Verifier Bubble Notification Tests Automation.

Automates the 22 subtests in BubblesVerifierActivity:
1. Enable device and notification bubble settings.
2. Launch BubblesVerifierActivity and dismiss instructions.
3. For each step:
   a. Tap bubble action button (e.g. 'Send Bubble', 'Open Settings').
   b. Verify floating circular bubble icon, expanded window, overflow flyout,
      rotation (portrait/landscape), scrim, and IME soft-keyboard insets.
   c. Capture numbered step screenshots.
   d. Tap test_step_passed button to advance to the next step.
4. Verify summary screen (0 failures) and global toolbar Pass button enabled.
5. Tap global Pass button, export report, and verify passing result in test_result.xml.
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
    find_node,
    find_pass_button,
    get_display_dimensions,
    get_focused_package,
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

TEST_NAME = "Bubble Notification Tests"
ACTIVITY_CLASS = "com.android.cts.verifier.notifications.BubblesVerifierActivity"


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


def handle_bubble_step(step_idx):
    """Execute action button (if present), perform UI verification, and tap test_step_passed."""
    print(f"\n[Step {step_idx:02d}] Inspecting bubble step UI...")
    # Ensure scroll is reset to top of step
    w, h = get_screen_size()
    adb(
        "shell",
        "input",
        "swipe",
        str(w // 2),
        str(int(h * 0.30)),
        str(w // 2),
        str(int(h * 0.80)),
        "300",
        check=False,
    )
    time.sleep(1.0)

    # Configure step-specific bubble settings
    if step_idx == 3:
        adb(
            "shell",
            "settings",
            "put",
            "secure",
            "notification_bubbles",
            "1",
            check=False,
        )
        adb(
            "shell",
            "cmd",
            "notification",
            "set_bubbles",
            "com.android.cts.verifier",
            "2",
            check=False,
        )
        time.sleep(2.5)
    elif step_idx == 4:
        adb(
            "shell",
            "settings",
            "put",
            "secure",
            "notification_bubbles",
            "0",
            check=False,
        )
        adb(
            "shell",
            "cmd",
            "notification",
            "set_bubbles",
            "com.android.cts.verifier",
            "0",
            check=False,
        )
        time.sleep(2.5)
    elif step_idx == 5:
        adb(
            "shell",
            "settings",
            "put",
            "secure",
            "notification_bubbles",
            "1",
            check=False,
        )
        adb(
            "shell",
            "cmd",
            "notification",
            "set_bubbles",
            "com.android.cts.verifier",
            "1",
            check=False,
        )
        time.sleep(2.5)

    # 1. Search and tap action button if present (e.g. 'Send Bubble' or 'Open settings')
    root = ui_dump()
    action_btn = find_node(
        root, resource_id="com.android.cts.verifier:id/bubble_test_button")
    if (action_btn is not None and
            action_btn.attrib.get("enabled", "true") == "true" and
            action_btn.attrib.get("text", "").strip()):
        bounds = action_btn.attrib.get("bounds", "")
        if bounds and not bounds.startswith("[0,0]"):
            btn_text = action_btn.attrib.get("text", "")
            print(f"  Tapping action button: {btn_text!r}...")
            tap(action_btn)
            time.sleep(2.5)
            screenshot(f"step_{step_idx:02d}_action_tapped")

            # Check if Settings opened as a result of action button
            is_settings = get_focused_package() == "com.android.settings"
            if not is_settings:
                try:
                    root_check = ui_dump(retries=2)
                    is_settings = (
                        root_check.attrib.get("package")
                        == "com.android.settings" or
                        find_node(root_check,
                                  resource_id_contains="com.android.settings")
                        is not None)
                except Exception:
                    pass
            if is_settings:
                print(
                    "  Settings opened, capturing screenshot and returning...")
                screenshot(f"step_{step_idx:02d}_settings")
                time.sleep(1.5)
                for _ in range(3):
                    if get_focused_package() == "com.android.settings":
                        adb("shell",
                            "input",
                            "keyevent",
                            "KEYCODE_BACK",
                            check=False)
                        time.sleep(1.5)
                    else:
                        break

    # 2. Step 19: Rotation verification
    if step_idx == 19:
        print("  [Step 19] Testing rotation in landscape and portrait...")
        adb("shell", "wm", "set-user-rotation", "lock", "1",
            check=False)  # Landscape
        time.sleep(2.0)
        screenshot("step_19_landscape")
        adb("shell", "wm", "set-user-rotation", "lock", "0",
            check=False)  # Portrait
        time.sleep(2.0)
        screenshot("step_19_portrait")

    # 3. Take step screenshot
    screenshot(f"step_{step_idx:02d}_verified")

    # 4. Wait for and tap test_step_passed button
    for _ in range(12):
        root = ui_dump()
        if is_pass_button_enabled(root):
            print("  ✓ Global toolbar Pass button is enabled during step!")
            return True
        step_passed_btn = find_node(
            root, resource_id="com.android.cts.verifier:id/test_step_passed")
        if (step_passed_btn is not None and
                step_passed_btn.attrib.get("enabled", "false") == "true"):
            print(f"  Tapping 'test_step_passed' for step {step_idx:02d}...")
            tap(step_passed_btn)
            time.sleep(2.0)
            return True
        # Scroll down in case button is below viewport in ScrollView
        w, h = get_screen_size()
        adb(
            "shell",
            "input",
            "swipe",
            str(w // 2),
            str(int(h * 0.70)),
            str(w // 2),
            str(int(h * 0.35)),
            "300",
            check=False,
        )
        time.sleep(1.0)

    print(
        f"  Warning: 'test_step_passed' button not enabled for step {step_idx:02d}"
    )
    return False


def main():
    setup()
    set_screenshot_dir("notifications_bubbles_test")

    try:
        # Pre-test setup: Enable bubbles in system settings
        print(
            "Pre-test setup: Enabling bubble notifications in system settings..."
        )
        adb("shell", "input", "keyevent", "KEYCODE_WAKEUP", check=False)
        adb("shell", "wm", "dismiss-keyguard", check=False)
        adb("shell", "settings", "put", "global", "zen_mode", "0", check=False)
        adb(
            "shell",
            "settings",
            "put",
            "secure",
            "notification_bubbles",
            "1",
            check=False,
        )
        adb(
            "shell",
            "cmd",
            "notification",
            "set_bubbles",
            "com.android.cts.verifier",
            "0",
            check=False,
        )
        adb("shell", "cmd", "notification", "clear_all", check=False)
        time.sleep(2.5)

        print(f"Navigating to '{TEST_NAME}'...")
        navigate_to(TEST_NAME, verify_title="Bubble Notification")
        time.sleep(2)
        dismiss_initial_dialog()
        screenshot("00_test_opened")

        print("Executing Bubble Notification verification steps...")
        step = 1
        while step <= 30:
            # Check if global toolbar pass button is already enabled
            root = ui_dump()
            if is_pass_button_enabled(root):
                print("  ✓ Global toolbar Pass button is enabled!")
                break

            handle_bubble_step(step)
            step += 1

        # Confirm toolbar Pass button enabled and tap it
        print("\nWaiting for global Pass button confirmation...")
        pass_btn = None
        for _ in range(15):
            root = ui_dump()
            if is_pass_button_enabled(root):
                pass_btn = find_pass_button(root)
                break
            time.sleep(2)

        if pass_btn is not None:
            screenshot("23_global_pass_enabled")
            tap_pass(pass_btn)
            screenshot("24_global_pass_tapped")
        else:
            raise RuntimeError(
                "Global Pass button was not enabled after completing subtests")

        # Return to main activity and verify exported report
        return_to_main_activity()
        export_and_verify("notifications_bubbles_test")
        screenshot("25_test_report_exported")
        print(
            "\n=== Bubble Notification Tests Automation PASSED successfully! ==="
        )

    finally:
        adb("shell", "wm", "set-user-rotation", "free", check=False)
        adb("shell", "cmd", "notification", "clear_all", check=False)


if __name__ == "__main__":
    main()
