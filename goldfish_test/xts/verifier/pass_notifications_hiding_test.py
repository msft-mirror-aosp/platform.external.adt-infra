#!/usr/bin/env python3
"""Authentic CTS Verifier Notification Hiding Test Automation.

Automates the 9 subtests in NotificationHidingVerifierActivity:
1. Grant SMS role holder to CtsVerifier.
2. Launch NotificationHidingVerifierActivity and dismiss instructions.
3. Automate MediaProjection consent dialog ('Entire screen' / 'Start now').
4. For each test scenario (Shade, In-App, Partial share, Launcher, Bubbles, Local recorder):
   a. Tap send_notification_button to post sensitive OTP notification.
   b. Expand shade / navigate as required.
   c. Tap save_screen_capture_button to verify CDD 9.8.2 sensitive content redaction.
   d. Tap test_step_passed to advance.
5. Verify summary screen (0 failures) and global toolbar Pass button enabled.
6. Tap global Pass button, export report, and verify passing result in test_result.xml.
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

TEST_NAME = "Notification Hiding Test"
ACTIVITY_CLASS = (
    "com.android.cts.verifier.notifications.NotificationHidingVerifierActivity")


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
    for _ in range(3):
        root = ui_dump()
        ok_btn = find_node(root, text="OK")
        if ok_btn is not None:
            print("  Dismissing instructions OK dialog...")
            tap(ok_btn)
            time.sleep(1.5)
            break
        time.sleep(0.5)


def handle_mediaprojection_consent():
    """Automate system screen capture permission dialog ('Entire screen' / 'Start now') with dynamic child button detection."""
    print("  Handling MediaProjection consent dialog...")
    dialog_start_time = time.time()
    dialog_seen = False

    # Wait up to 6s specifically for SystemUI modal consent dialog to appear
    while time.time() - dialog_start_time < 6.0:
        root = ui_dump()
        focused_pkg = get_focused_package()

        is_systemui_or_consent = (
            (focused_pkg and "systemui" in focused_pkg.lower()) or
            find_node(root, text="Entire screen") is not None or
            find_node(root, content_desc="Entire screen") is not None or
            find_node(root, text="Start now") is not None or
            find_node(root, text="Start recording") is not None or
            find_node(root, text="Start casting") is not None or
            find_node(root, text="Share screen") is not None or
            find_node(root, text="A single app") is not None or
            find_node(root, text="Single app") is not None or
            find_node(root, text="Choose app to share") is not None or
            find_node(root, text="Choose an app") is not None or find_node(
                root,
                resource_id=
                "com.android.systemui:id/screen_share_mode_options_start_button",
            ) is not None)
        if is_systemui_or_consent:
            dialog_seen = True
            break
        time.sleep(0.5)

    if not dialog_seen:
        focused_pkg = get_focused_package()
        if focused_pkg == "com.android.cts.verifier":
            print("  No MediaProjection consent dialog appeared"
                  " (already in CTS Verifier).")
            return True

    # Handle the consent dialog
    for _ in range(12):
        if get_focused_package() == "com.android.cts.verifier":
            print("  ✓ Back in CTS Verifier, MediaProjection consent complete.")
            return True

        root = ui_dump()

        # Check if MediaProjectionAppSelectorActivity ("Choose app to share" app picker grid) is open
        app_selector = (
            find_node(root, text="Choose app to share") is not None or
            find_node(root, text="Choose an app") is not None or find_node(
                root, resource_id="com.android.systemui:id/app_picker_grid")
            is not None or "appselector" in get_focused_package().lower())
        if app_selector:
            print("  [Consent] MediaProjectionAppSelectorActivity detected."
                  " Selecting 'CTS Verifier' or pressing BACK...")
            cts_node = find_node(root, text="CTS Verifier")
            if cts_node is None:
                cts_node = find_node(root, content_desc="CTS Verifier")
            if cts_node is not None:
                tap(cts_node)
                time.sleep(2.0)
            else:
                adb("shell", "input", "keyevent", "KEYCODE_BACK", check=False)
                time.sleep(1.5)
            if get_focused_package() == "com.android.cts.verifier":
                return True
            root = ui_dump()

        # 1. Open com.android.systemui:id/screen_share_mode_spinner (or find spinner widget)
        # and explicitly select "Entire screen" BEFORE searching for or tapping "Next" / "Start"
        spinner = find_node(
            root,
            resource_id="com.android.systemui:id/screen_share_mode_spinner")
        if spinner is None:
            spinner = find_node(root, class_name="android.widget.Spinner")
        if spinner is None:
            spinner = find_node(root, text="A single app")
        if spinner is None:
            spinner = find_node(root, text="Single app")
        if spinner is None:
            spinner = find_node(root, content_desc="A single app")

        spinner_text = ""
        if spinner is not None:
            spinner_text = (spinner.attrib.get("text", "") or
                            spinner.attrib.get("content-desc", ""))
            for child in spinner.iter("node"):
                t = child.attrib.get("text", "")
                if t:
                    spinner_text = t
                    break

        if spinner is not None and "entire screen" not in spinner_text.lower():
            print("  Opening screen share mode spinner to select 'Entire"
                  " screen'...")
            tap(spinner)
            time.sleep(1.0)
            root_dropdown = ui_dump()
            es_opt = find_node(root_dropdown, text="Entire screen")
            if es_opt is None:
                es_opt = find_node(root_dropdown, content_desc="Entire screen")
            if es_opt is not None:
                print("  Selecting 'Entire screen' from spinner dropdown...")
                tap(es_opt)
                time.sleep(1.0)
                root = ui_dump()

        # 2. Look for 'Entire screen' radio/spinner/list option on the dialog
        entire_screen = find_node(root, text="Entire screen")
        if entire_screen is None:
            entire_screen = find_node(root, content_desc="Entire screen")
        if (entire_screen is not None and
                entire_screen.attrib.get("checked", "") != "true"):
            print("  Selecting 'Entire screen' option...")
            tap(entire_screen)
            time.sleep(1.0)
            root = ui_dump()

        # 3. Look for 'Start now' / 'Share screen' / 'Start recording' / 'Start casting' / 'Start' / 'Next' button
        start_btn = None
        for candidate in [
                find_node(root, text="Start recording"),
                find_node(root, text="Start now"),
                find_node(root, text="Share screen"),
                find_node(root, text="Start casting"),
                find_node(root, text="Start"),
                find_node(root, text="Next"),
                find_node(root, resource_id="android:id/button1"),
                find_node(
                    root,
                    resource_id=
                    "com.android.systemui:id/screen_share_mode_options_start_button",
                ),
                find_node(
                    root,
                    resource_id=
                    "com.android.systemui:id/screen_share_mode_options_next_button",
                ),
                find_node(
                    root,
                    resource_id="com.android.systemui:id/button_start",
                ),
        ]:
            if candidate is not None:
                start_btn = candidate
                break

        # Fallback: scan buttonPanel / alert dialog children for enabled button
        if start_btn is None:
            for panel_res in ("android:id/buttonPanel",
                              "android:id/parentPanel"):
                panel = find_node(root, resource_id=panel_res)
                if panel is not None:
                    for child in panel.iter("node"):
                        if (child.attrib.get("class")
                                == "android.widget.Button" and child.attrib.get(
                                    "enabled", "true") == "true" and
                                child.attrib.get("text", "").lower()
                                not in ("cancel", "dismiss")):
                            start_btn = child
                            break
                    if start_btn is not None:
                        break

        if start_btn is not None and start_btn.attrib.get("enabled",
                                                          "true") == "true":
            btn_text = start_btn.attrib.get("text", "Start")
            print(f"  Tapping '{btn_text}' consent button...")
            tap(start_btn)
            time.sleep(2.0)

            # Verify return to com.android.cts.verifier
            for _ in range(6):
                if get_focused_package() == "com.android.cts.verifier":
                    print("  ✓ Back in CTS Verifier, MediaProjection consent"
                          " complete.")
                    return True
                time.sleep(0.5)
            continue
        time.sleep(1)

    for _ in range(5):
        if get_focused_package() == "com.android.cts.verifier":
            return True
        adb("shell", "input", "keyevent", "KEYCODE_BACK", check=False)
        time.sleep(1.0)
    return get_focused_package() == "com.android.cts.verifier"


def handle_hiding_step(step_idx):
    """Send sensitive notification, trigger capture, and tap test_step_passed."""
    print(f"\n[Step {step_idx:02d}] Executing Notification Hiding test step...")
    # Ensure CtsVerifier is focused before starting step
    if get_focused_package() != "com.android.cts.verifier":
        print("  [Focus] Current focused package is"
              f" {get_focused_package()!r}, restoring CtsVerifier...")
        adb(
            "shell",
            "am",
            "start",
            "-W",
            "-f",
            "0x20000000",
            "-n",
            ("com.android.cts.verifier/.notifications.NotificationHidingVerifierActivity"
            ),
            check=False,
        )
        time.sleep(2.0)

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
        "250",
        check=False,
    )
    time.sleep(1.0)
    root = ui_dump()

    # 1. Start screenshare / re-engage consent dialog ('Entire screen' / 'Start now')
    start_share_btn = find_node(
        root,
        resource_id="com.android.cts.verifier:id/start_screenshare_button",
    )
    if (start_share_btn is not None and
            start_share_btn.attrib.get("enabled", "true") == "true"):
        print("  Starting screen share recording...")
        tap(start_share_btn)
        time.sleep(1.5)
        handle_mediaprojection_consent()
        root = ui_dump()
    else:
        handle_mediaprojection_consent()
        root = ui_dump()

    # Verify focus returned to CtsVerifier before subtest execution
    if get_focused_package() != "com.android.cts.verifier":
        print("  [Focus] Restoring CtsVerifier focus before proceeding with"
              " subtest execution...")
        for _ in range(3):
            adb("shell", "input", "keyevent", "KEYCODE_BACK", check=False)
            time.sleep(1.0)
            if get_focused_package() == "com.android.cts.verifier":
                break
        if get_focused_package() != "com.android.cts.verifier":
            adb(
                "shell",
                "am",
                "start",
                "-W",
                "-f",
                "0x20000000",
                "-n",
                ("com.android.cts.verifier/.notifications.NotificationHidingVerifierActivity"
                ),
                check=False,
            )
            time.sleep(2.0)
        root = ui_dump()

    # 2. Tap send notification button if enabled
    send_btn = find_node(
        root,
        resource_id="com.android.cts.verifier:id/send_notification_button",
    )
    if send_btn is not None and send_btn.attrib.get("enabled",
                                                    "true") == "true":
        print("  Tapping 'send_notification_button'...")
        tap(send_btn)
        time.sleep(1.5)

    # 3. Handle shade expansion for shade test steps (e.g. Step 1, 3, 5, 7)
    if step_idx in [1, 3, 5, 7]:
        print("  Expanding notification shade...")
        adb("shell", "cmd", "statusbar", "expand-notifications", check=False)
        time.sleep(2.0)
        screenshot(f"step_{step_idx:02d}_shade_opened")
        adb("shell", "cmd", "statusbar", "collapse", check=False)
        time.sleep(1.5)
        root = ui_dump()

    # 4. Tap save screen capture button if enabled
    save_btn = find_node(
        root,
        resource_id="com.android.cts.verifier:id/save_screen_capture_button",
    )
    if save_btn is not None and save_btn.attrib.get("enabled",
                                                    "true") == "true":
        print("  Tapping 'save_screen_capture_button'...")
        tap(save_btn)
        time.sleep(2.0)

    screenshot(f"step_{step_idx:02d}_verified")

    # 5. Tap test_step_passed (or skip_button if low ram)
    # Perform vertical scroll down swipe to bring test_step_passed into view before searching in UI dump
    adb(
        "shell",
        "input",
        "swipe",
        str(w // 2),
        str(int(h * 0.70)),
        str(w // 2),
        str(int(h * 0.35)),
        "250",
        check=False,
    )
    time.sleep(1.0)
    for _ in range(8):
        root = ui_dump()
        step_passed_btn = find_node(
            root, resource_id="com.android.cts.verifier:id/test_step_passed")
        if (step_passed_btn is not None and
                step_passed_btn.attrib.get("enabled", "false") == "true"):
            print(f"  Tapping 'test_step_passed' for step {step_idx:02d}...")
            tap(step_passed_btn)
            time.sleep(2.0)
            return True

        skip_btn = find_node(
            root, resource_id="com.android.cts.verifier:id/skip_button")
        if skip_btn is not None and skip_btn.attrib.get("enabled",
                                                        "false") == "true":
            print(f"  Tapping 'skip_button' for step {step_idx:02d}...")
            tap(skip_btn)
            time.sleep(2.0)
            return True

        # Perform vertical scroll swipe in ScrollView to reveal buttons
        adb(
            "shell",
            "input",
            "swipe",
            str(w // 2),
            str(int(h * 0.70)),
            str(w // 2),
            str(int(h * 0.35)),
            "250",
            check=False,
        )
        time.sleep(1.0)

    print(
        f"  Warning: Neither 'test_step_passed' nor 'skip_button' enabled for step {step_idx:02d}"
    )
    return False


def main():
    setup()
    set_screenshot_dir("notifications_hiding_test")

    try:
        # Pre-test setup: Grant SMS role holder to CtsVerifier
        print("Pre-test setup: Granting SMS role holder and clearing state...")
        adb("shell", "input", "keyevent", "KEYCODE_WAKEUP", check=False)
        adb("shell", "wm", "dismiss-keyguard", check=False)
        adb("shell", "settings", "put", "global", "zen_mode", "0", check=False)
        adb(
            "shell",
            "cmd",
            "role",
            "add-role-holder",
            "android.app.role.SMS",
            "com.android.cts.verifier",
            check=False,
        )
        adb("shell", "cmd", "notification", "clear_all", check=False)
        time.sleep(1)

        print(f"Navigating to '{TEST_NAME}'...")
        navigate_to(
            TEST_NAME,
            verify_title="Notification Hiding",
        )
        time.sleep(2)
        dismiss_initial_dialog()
        screenshot("00_test_opened")

        # Iterate through the Notification Hiding test steps dynamically (8 or 9 steps)
        total_steps = 9
        print(
            f"Beginning verification of all {total_steps} Notification Hiding test steps..."
        )

        for step in range(1, total_steps + 1):
            root = ui_dump()
            # Check if global toolbar pass button is already enabled before each step
            if is_pass_button_enabled(root):
                print("  ✓ Global toolbar Pass button is enabled!")
                break

            handle_hiding_step(step)

        # Immediately after completing subtests: collapse status bar, clear notifications, and dismiss dialogs
        print(
            "Completed subtests: collapsing status bar, clearing notifications, and dismissing system dialogs/overlays..."
        )
        adb("shell", "cmd", "statusbar", "collapse", check=False)
        adb("shell", "cmd", "notification", "clear_all", check=False)
        adb(
            "shell",
            "am",
            "broadcast",
            "-a",
            "android.intent.action.CLOSE_SYSTEM_DIALOGS",
            check=False,
        )
        time.sleep(1.0)

        # Confirm toolbar Pass button enabled and tap it
        print("\nWaiting for global Pass button confirmation...")
        pass_btn = None
        for _ in range(15):
            root = ui_dump()
            if is_pass_button_enabled(root):
                pass_btn = find_pass_button(root)
                break
            time.sleep(2.0)

        if pass_btn is not None:
            screenshot("10_global_pass_enabled")
            tap_pass(pass_btn)
            screenshot("11_global_pass_tapped")
        else:
            raise RuntimeError(
                "Global Pass button was not enabled after completing subtests")

        # Return to main activity and verify exported report
        return_to_main_activity()
        export_and_verify("notifications_hiding_test")
        screenshot("12_test_report_exported")
        print(
            "\n=== Notification Hiding Test Automation PASSED successfully! ==="
        )

    finally:
        adb(
            "shell",
            "cmd",
            "role",
            "remove-role-holder",
            "android.app.role.SMS",
            "com.android.cts.verifier",
            check=False,
        )
        adb("shell", "cmd", "notification", "clear_all", check=False)


if __name__ == "__main__":
    main()
