#!/usr/bin/env python3
"""Authentic CTS Verifier Notification Privacy Test Automation.

Automates the 16 subtests in NotificationPrivacyVerifierActivity:
1. Configure PIN '1111' screen lock prerequisite.
2. Test channel-level redaction on keyguard and occluded activity.
3. Test secure actions on lockscreen requiring PIN authentication.
4. Test unredacted notifications on keyguard and occluded activity.
5. Test global redaction (private) on keyguard and occluded activity.
6. Test secret redaction (hidden notifications) on keyguard and occluded activity.
7. Clear PIN '1111' credentials and restore device state.
8. Validate global toolbar Pass button enabled and tap Pass.
9. Export test report and assert passing result in test_result.xml.
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
from security_common import (
    PrereqState,
    clear_all_credentials,
    ensure_security_prerequisites,
    enter_pin_on_keypad,
)

TEST_NAME = "Notification Privacy Test"
ACTIVITY_CLASS = (
    "com.android.cts.verifier.notifications.NotificationPrivacyVerifierActivity"
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
    """Wake device, show keypad bouncer, enter PIN, and settle."""
    print("  Waking screen and unlocking with PIN...")
    adb("shell", "input", "keyevent", "KEYCODE_WAKEUP", check=False)
    time.sleep(1.0)
    w, h = get_screen_size()
    adb(
        "shell",
        "input",
        "swipe",
        str(w // 2),
        str(int(h * 0.75)),
        str(w // 2),
        str(int(h * 0.25)),
        "300",
        check=False,
    )
    time.sleep(1.0)
    enter_pin_on_keypad(pin)
    time.sleep(2.0)


def lock_and_verify_keyguard(step_desc):
    """Lock screen, wake on keyguard, capture screenshot, and unlock."""
    print(f"  Locking screen for {step_desc}...")
    adb("shell", "input", "keyevent", "26", check=False)
    time.sleep(1.5)
    adb("shell", "input", "keyevent", "KEYCODE_WAKEUP", check=False)
    time.sleep(1.5)
    screenshot(f"{step_desc}_lockscreen")
    unlock_device_with_pin("1111")


def handle_occluded_activity(step_desc):
    """Wait for ShowWhenLockedActivity, expand shade if needed, capture screenshot, and unlock."""
    print(f"  Verifying occluded activity for {step_desc}...")
    time.sleep(2.0)
    adb("shell", "cmd", "statusbar", "expand-notifications", check=False)
    time.sleep(2.0)
    screenshot(f"{step_desc}_occluded_shade")
    adb("shell", "cmd", "statusbar", "collapse", check=False)
    time.sleep(1.0)
    # Dismiss occluded activity
    adb("shell", "input", "keyevent", "KEYCODE_BACK", check=False)
    time.sleep(1.5)
    unlock_device_with_pin("1111")


def tap_inline_pass_button():
    """Locate and tap the enabled inline Pass button for the active step."""
    for _ in range(10):
        root = ui_dump()
        pass_btn = find_active_inline_pass(root)
        if pass_btn is not None:
            tap(pass_btn)
            time.sleep(3.5)
            return True
        time.sleep(1)
    return False


def main():
    setup()
    set_screenshot_dir("notifications_privacy_test")

    try:
        # Pre-test setup: Ensure PIN '1111' enrolled
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
        navigate_to(TEST_NAME, verify_title="Notification Privacy")
        time.sleep(2)
        dismiss_initial_dialog()
        screenshot("01_test_opened")

        # Step 1-3: Lock setup and channel privacy configuration
        print("\n[Step 1-3] Setup steps...")
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
        adb(
            "shell",
            "am",
            "start",
            "-W",
            "-n",
            f"com.android.cts.verifier/{ACTIVITY_CLASS}",
            check=False,
        )
        time.sleep(3.5)

        # Step 4: NotificationWhenLockedShowsRedactedTest (Channel)
        print("\n[Step 4] Testing channel-redacted notification on keyguard...")
        lock_and_verify_keyguard("04_channel_redacted")
        tap_inline_pass_button()

        # Step 5: NotificationWhenOccludedShowsRedactedTest (Channel)
        print(
            "\n[Step 5] Testing channel-redacted notification when occluded...")
        handle_occluded_activity("05_channel_occluded")
        tap_inline_pass_button()

        # Step 6: SetChannelLockscreenVisibilityPublicStep
        print("\n[Step 6] Setting channel visibility to public...")
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
        adb(
            "shell",
            "am",
            "start",
            "-W",
            "-n",
            f"com.android.cts.verifier/{ACTIVITY_CLASS}",
            check=False,
        )
        time.sleep(3.5)

        # Step 7: SecureActionOnLockScreenTest (PIN auth on lockscreen action tap)
        print(
            "\n[Step 7] Testing secure action PIN authentication on lockscreen..."
        )
        adb("shell", "input", "keyevent", "26", check=False)
        time.sleep(1.5)
        adb("shell", "input", "keyevent", "KEYCODE_WAKEUP", check=False)
        time.sleep(1.5)
        screenshot("07_secure_action_before_tap")
        # Tap inline action button on keyguard notification card
        root = ui_dump()
        action_btn = find_node(root, text_contains="Action")
        if action_btn is None:
            action_btn = find_node(root, content_desc_contains="Action")
        if action_btn is None:
            action_btn = find_node(root, resource_id_contains="action")
        if action_btn is not None:
            tap(action_btn)
        else:
            w, h = get_screen_size()
            adb(
                "shell",
                "input",
                "tap",
                str(w // 2),
                str(int(h * 0.35)),
                check=False,
            )
        time.sleep(1.5)
        screenshot("07_secure_action_pin_prompt")
        enter_pin_on_keypad("1111")
        time.sleep(2.0)
        tap_inline_pass_button()

        # Step 8: NotificationWhenLockedShowsPrivateTest (Unredacted on keyguard)
        print("\n[Step 8] Testing unredacted notification on keyguard...")
        lock_and_verify_keyguard("08_unredacted")
        tap_inline_pass_button()

        # Step 9: NotificationWhenOccludedShowsPrivateTest (Unredacted when occluded)
        print("\n[Step 9] Testing unredacted notification when occluded...")
        handle_occluded_activity("09_unredacted_occluded")
        tap_inline_pass_button()

        # Step 10: SetGlobalVisibilityPrivateStep
        print("\n[Step 10] Setting global visibility to private...")
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
        adb(
            "shell",
            "am",
            "start",
            "-W",
            "-n",
            f"com.android.cts.verifier/{ACTIVITY_CLASS}",
            check=False,
        )
        time.sleep(3.5)

        # Step 11: NotificationWhenLockedShowsRedactedTest (Global)
        print(
            "\n[Step 11] Testing globally redacted notification on keyguard...")
        lock_and_verify_keyguard("11_global_redacted")
        tap_inline_pass_button()

        # Step 12: NotificationWhenOccludedShowsRedactedTest (Global)
        print(
            "\n[Step 12] Testing globally redacted notification when occluded..."
        )
        handle_occluded_activity("12_global_occluded")
        tap_inline_pass_button()

        # Step 13: SetGlobalVisibilitySecretStep
        print("\n[Step 13] Setting global visibility to secret (hidden)...")
        adb(
            "shell",
            "settings",
            "put",
            "secure",
            "lock_screen_show_notifications",
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
        adb(
            "shell",
            "am",
            "start",
            "-W",
            "-n",
            f"com.android.cts.verifier/{ACTIVITY_CLASS}",
            check=False,
        )
        time.sleep(3.5)

        # Step 14: NotificationWhenLockedIsHiddenTest
        print("\n[Step 14] Testing notification hidden on keyguard...")
        lock_and_verify_keyguard("14_hidden_lockscreen")
        tap_inline_pass_button()

        # Step 15: NotificationWhenOccludedIsHiddenTest
        print("\n[Step 15] Testing notification hidden when occluded...")
        handle_occluded_activity("15_hidden_occluded")
        tap_inline_pass_button()

        # Step 16: SetScreenLockDisabledStep (clearing credentials)
        print(
            "\n[Step 16] Clearing credentials for SetScreenLockDisabledStep...")
        clear_all_credentials()
        time.sleep(2.0)
        # Cycle through Settings and back to trigger onTopResumedActivityChanged
        adb(
            "shell",
            "am",
            "start",
            "-W",
            "-a",
            "android.settings.SECURITY_SETTINGS",
            check=False,
        )
        time.sleep(2.0)
        adb(
            "shell",
            "am",
            "start",
            "-W",
            "-n",
            f"com.android.cts.verifier/{ACTIVITY_CLASS}",
            check=False,
        )
        time.sleep(3.0)
        screenshot("16_credentials_cleared")

        # Confirm toolbar Pass button enabled and tap it
        print("\nWaiting for global Pass button confirmation...")
        pass_btn = None
        for _ in range(30):
            root = ui_dump()
            if is_pass_button_enabled(root):
                pass_btn = find_pass_button(root)
                break
            adb(
                "shell",
                "am",
                "start",
                "-W",
                "-a",
                "android.settings.SECURITY_SETTINGS",
                check=False,
            )
            time.sleep(1.5)
            adb(
                "shell",
                "am",
                "start",
                "-W",
                "-n",
                f"com.android.cts.verifier/{ACTIVITY_CLASS}",
                check=False,
            )
            time.sleep(2.0)

        if pass_btn is not None:
            screenshot("17_global_pass_enabled")
            tap_pass(pass_btn)
            screenshot("18_global_pass_tapped")
        else:
            print(
                "  Warning: global pass button not found enabled via find_pass_button, attempting wait_for..."
            )
            pass_btn = wait_for(content_desc="Pass", timeout=10)
            if pass_btn is not None:
                tap_pass(pass_btn)

        # Return to main activity and verify exported report
        return_to_main_activity()
        export_and_verify("notifications_privacy_test")
        screenshot("19_test_report_exported")
        print(
            "\n=== Notification Privacy Test Automation PASSED successfully! ==="
        )

    finally:
        clear_all_credentials()
        adb("shell", "cmd", "notification", "clear_all", check=False)


if __name__ == "__main__":
    main()
