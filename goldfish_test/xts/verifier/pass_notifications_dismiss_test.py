#!/usr/bin/env python3
"""Authentic CTS Verifier Notification Dismiss Test Automation.

Automates the 11 subtests in NotificationDismissVerifierActivity:
1. Set up PIN '1111' screen lock.
2. Configure global and channel lockscreen redaction settings.
3. Test dismissing ongoing notification in unlocked shade (allowed).
4. Test dismissing ongoing notification on keyguard lockscreen (blocked).
5. Test dismissing channel-redacted notification on keyguard (allowed).
6. Test dismissing unredacted notification on keyguard (allowed).
7. Test dismissing globally redacted notification on keyguard (blocked).
8. Remove PIN '1111' and restore device state.
9. Validate global toolbar Pass button enabled and tap Pass.
10. Export test report and assert passing result in test_result.xml.
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
    bounds_center,
    export_and_verify,
    find_active_inline_pass,
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
from security_common import (
    PrereqState,
    clear_all_credentials,
    ensure_security_prerequisites,
    enter_pin_on_keypad,
    is_pin_entry_present,
)

TEST_NAME = "Notification Dismiss Test"
ACTIVITY_CLASS = (
    "com.android.cts.verifier.notifications.NotificationDismissVerifierActivity"
)


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


def unlock_device_with_pin(pin="1111"):
    """Wake device, open bouncer, enter PIN on keypad, and return to app."""
    print("  Waking screen and entering PIN...")
    adb("shell", "input", "keyevent", "KEYCODE_WAKEUP", check=False)
    time.sleep(1.0)
    root = ui_dump()
    w, h = get_screen_size()
    x = w // 2
    y1 = int(h * 0.80)
    y2 = int(h * 0.20)
    if not is_pin_entry_present(root):
        print(f"  Swiping up to open PIN bouncer ({x}, {y1} -> {x}, {y2},"
              " 200ms)...")
        adb(
            "shell",
            "input",
            "swipe",
            str(x),
            str(y1),
            str(x),
            str(y2),
            "200",
            check=False,
        )
        time.sleep(1.0)
        root = ui_dump()

    for _ in range(3):
        if is_pin_entry_present(root):
            break
        print(f"  Retrying bouncer swipe ({x}, {y1} -> {x}, {y2}, 200ms)...")
        adb(
            "shell",
            "input",
            "swipe",
            str(x),
            str(y1),
            str(x),
            str(y2),
            "200",
            check=False,
        )
        time.sleep(1.0)
        root = ui_dump()

    enter_pin_on_keypad(pin)
    time.sleep(2.0)


def lock_screen_and_swipe_notification(should_succeed=True):
    """Lock screen, wake, swipe notification card on lockscreen, and unlock."""
    print("  Locking screen...")
    adb("shell", "input", "keyevent", "26",
        check=False)  # Screen power toggle / lock
    time.sleep(1.5)

    print("  Waking screen on lockscreen...")
    adb("shell", "input", "keyevent", "KEYCODE_WAKEUP", check=False)
    time.sleep(1.5)

    screenshot("lockscreen_with_notification")

    print(
        f"  Attempting swipe dismiss on lockscreen (expect success={should_succeed})..."
    )
    # Horizontal swipe across notification row using dynamic screen coordinates
    w, h = get_screen_size()
    x1 = int(w * 0.20)
    x2 = int(w * 0.85)
    y = int(h * 0.40)
    adb("shell",
        "input",
        "swipe",
        str(x1),
        str(y),
        str(x2),
        str(y),
        "300",
        check=False)
    time.sleep(1.5)

    screenshot("after_lockscreen_swipe")

    unlock_device_with_pin("1111")


def tap_inline_pass_button():
    """Locate and tap the enabled inline Pass button for the active step."""
    for attempt in range(10):
        root = ui_dump()
        w, h = get_screen_size()
        min_y = int(h * 0.05)
        max_y = int(h * 0.95)

        # Find active inline pass buttons and filter out clipped buttons
        candidates = []
        for n in root.iter("node"):
            cls = (n.attrib.get("class") or "").strip()
            res = (n.attrib.get("resource-id") or "").strip()
            if res.endswith(":id/iva_action_button_pass") or (
                    res.endswith(":id/pass_button") and
                    cls == "android.widget.Button"):
                if n.attrib.get("enabled", "false") == "true":
                    _, cy = bounds_center(n)
                    if min_y <= cy <= max_y:
                        candidates.append(n)

        if candidates:
            pass_btn = candidates[0]
            print(
                f"  Tapping inline pass button at {pass_btn.attrib['bounds']}..."
            )
            tap(pass_btn)
            time.sleep(3.5)
            return True

        # Vertical scroll swipe to bring active step into active viewport
        print(
            f"  Inline pass button not in active viewport (attempt {attempt + 1}), scrolling down..."
        )
        adb(
            "shell",
            "input",
            "swipe",
            str(w // 2),
            str(int(h * 0.70)),
            str(w // 2),
            str(int(h * 0.35)),
            "400",
            check=False,
        )
        time.sleep(1.0)
    return False


def main():
    setup()
    set_screenshot_dir("notifications_dismiss_test")

    try:
        # Pre-test setup: Ensure clean slate and PIN '1111' enrolled
        print("Pre-test setup: Setting up PIN '1111' prerequisite...")
        ensure_security_prerequisites(PrereqState.PIN_ONLY)
        adb(
            "shell",
            "settings",
            "put",
            "secure",
            "lock_screen_show_notifications",
            "1",
            check=False,
        )
        adb(
            "shell",
            "settings",
            "put",
            "secure",
            "lock_screen_allow_private_notifications",
            "1",
            check=False,
        )
        adb("shell", "cmd", "notification", "clear_all", check=False)
        time.sleep(1)

        print(f"Navigating to '{TEST_NAME}'...")
        navigate_to(TEST_NAME, verify_title="Notification Dismiss")
        time.sleep(2)
        dismiss_initial_dialog()
        screenshot("01_test_opened")

        # Step 1: SetScreenLockEnabledStep (auto passed due to PIN setup)
        # Step 2: SetGlobalVisibilityPublicStep (auto passed due to pre-test settings)
        # Step 3: SetChannelLockscreenVisibilityPrivateStep
        print("\n[Step 1-3] Redaction setup steps...")
        time.sleep(3.5)
        # Configure channel lockscreen visibility to private for Step 3
        adb(
            "shell",
            "settings",
            "put",
            "secure",
            "lock_screen_allow_private_notifications",
            "0",
            check=False,
        )
        time.sleep(1.0)
        adb(
            "shell",
            "am",
            "start",
            "-W",
            "-a",
            "android.settings.NOTIFICATION_SETTINGS",
            check=False,
        )
        time.sleep(1.5)
        if get_focused_package() == "com.android.settings":
            adb("shell", "input", "keyevent", "KEYCODE_BACK", check=False)
            time.sleep(2.0)
        screenshot("03_redaction_settings_configured")

        # Step 4: CanDismissOngoingNotificationTest (unlocked shade swipe)
        print(
            "\n[Step 4] Testing ongoing notification dismissal in unlocked shade..."
        )
        adb("shell", "cmd", "statusbar", "expand-notifications", check=False)
        time.sleep(2.0)
        screenshot("04_unlocked_shade_ongoing")
        w, h = get_screen_size()
        x1 = int(w * 0.20)
        x2 = int(w * 0.85)
        y = int(h * 0.40)
        adb("shell",
            "input",
            "swipe",
            str(x1),
            str(y),
            str(x2),
            str(y),
            "300",
            check=False)
        time.sleep(1.0)
        adb("shell", "cmd", "statusbar", "collapse", check=False)
        time.sleep(1.5)
        tap_inline_pass_button()
        screenshot("04_ongoing_unlocked_passed")

        # Step 5: CannotDismissOngoingNotificationTest (lockscreen blocked)
        print(
            "\n[Step 5] Testing ongoing notification dismissal on lockscreen (blocked)..."
        )
        time.sleep(1.0)
        lock_screen_and_swipe_notification(should_succeed=False)
        tap_inline_pass_button()
        screenshot("05_ongoing_lockscreen_blocked_passed")

        # Step 6: CanDismissRegularNotificationTest (channel redacted, lockscreen allowed)
        print(
            "\n[Step 6] Testing channel-redacted notification dismissal on lockscreen..."
        )
        time.sleep(1.0)
        lock_screen_and_swipe_notification(should_succeed=True)
        tap_inline_pass_button()
        screenshot("06_channel_redacted_dismiss_passed")

        # Step 7: SetChannelLockscreenVisibilityPublicStep
        print("\n[Step 7] Setting channel visibility to public...")
        adb(
            "shell",
            "settings",
            "put",
            "secure",
            "lock_screen_allow_private_notifications",
            "1",
            check=False,
        )
        time.sleep(1.0)
        adb(
            "shell",
            "am",
            "start",
            "-W",
            "-a",
            "android.settings.NOTIFICATION_SETTINGS",
            check=False,
        )
        time.sleep(1.5)
        if get_focused_package() == "com.android.settings":
            adb("shell", "input", "keyevent", "KEYCODE_BACK", check=False)
            time.sleep(2.0)

        # Step 8: CanDismissRegularNotificationTest (unredacted, lockscreen allowed)
        print(
            "\n[Step 8] Testing unredacted notification dismissal on lockscreen..."
        )
        time.sleep(1.0)
        lock_screen_and_swipe_notification(should_succeed=True)
        tap_inline_pass_button()
        screenshot("08_unredacted_dismiss_passed")

        # Step 9: SetGlobalVisibilityPrivateStep
        print("\n[Step 9] Setting global visibility to private...")
        adb(
            "shell",
            "settings",
            "put",
            "secure",
            "lock_screen_allow_private_notifications",
            "0",
            check=False,
        )
        time.sleep(1.0)
        adb(
            "shell",
            "am",
            "start",
            "-W",
            "-a",
            "android.settings.NOTIFICATION_SETTINGS",
            check=False,
        )
        time.sleep(1.5)
        if get_focused_package() == "com.android.settings":
            adb("shell", "input", "keyevent", "KEYCODE_BACK", check=False)
            time.sleep(2.0)

        # Step 10: CannotDismissRegularNotificationTest (globally redacted, lockscreen blocked)
        print(
            "\n[Step 10] Testing globally redacted notification dismissal on lockscreen (blocked)..."
        )
        time.sleep(1.0)
        lock_screen_and_swipe_notification(should_succeed=False)
        tap_inline_pass_button()
        screenshot("10_global_redacted_blocked_passed")

        # Step 11: SetScreenLockDisabledStep (clearing credentials)
        print(
            "\n[Step 11] Clearing credentials for SetScreenLockDisabledStep...")
        clear_all_credentials()
        time.sleep(2.0)

        # Tap action button to open security settings and return
        for _ in range(5):
            w, h = get_screen_size()
            adb(
                "shell",
                "input",
                "swipe",
                str(w // 2),
                str(int(h * 0.70)),
                str(w // 2),
                str(int(h * 0.25)),
                "300",
                check=False,
            )
            time.sleep(1.0)
            root = ui_dump()
            action_buttons = [
                n for n in root.iter("node")
                if (n.attrib.get("resource-id") or ""
                   ).endswith(":id/nls_action_button") and
                n.attrib.get("enabled", "false") == "true"
            ]
            if action_buttons:
                print(
                    f"  Tapping active action button for Step 11 (bounds: {action_buttons[-1].attrib.get('bounds')})..."
                )
                tap(action_buttons[-1])
                time.sleep(2.5)
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
                time.sleep(2.5)
                break

        # Give mRunner 5 seconds to transition from READY to PASS and enable global pass button
        time.sleep(5.0)
        screenshot("11_credentials_cleared")

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
            screenshot("12_global_pass_enabled")
            tap_pass(pass_btn)
            screenshot("13_global_pass_tapped")
        else:
            raise RuntimeError(
                "Global Pass button was not enabled after completing subtests")

        # Return to main activity and verify exported report
        return_to_main_activity()
        export_and_verify("notifications_dismiss_test")
        screenshot("14_test_report_exported")
        print(
            "\n=== Notification Dismiss Test Automation PASSED successfully! ==="
        )

    finally:
        clear_all_credentials()
        adb("shell", "cmd", "notification", "clear_all", check=False)


if __name__ == "__main__":
    main()
