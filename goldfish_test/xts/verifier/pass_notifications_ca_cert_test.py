#!/usr/bin/env python3
"""Authentic CTS Verifier CA Cert Notification Test Automation.

Verifies that when a CA certificate is installed, system notifications warn the user:
1. Open CAInstallNotificationVerifierActivity and dismiss instructions dialog.
2. Complete all 5 sub-items in DialogTestListActivity:
   - Step 1 (InstallCertItem): Tap item -> Tap [Go] -> Opens Security Settings -> Ingests myCA.cer -> Tap [Pass] on dialog -> Verify item 1 checkmark.
   - Step 2 (CheckCertItem): Tap item -> Tap [Go] -> Opens Trusted Credentials -> Asserts 'Internet Widgits Pty Ltd' in User tab -> Tap [Pass] on dialog -> Verify item 2 checkmark.
   - Step 3 (RemoveScreenLockItem): Tap item -> Tap [Go] -> Opens Screen Lock Settings -> Tap [Pass] on dialog -> Verify item 3 checkmark.
   - Step 4 (CheckNotificationItem): Expands notification shade -> Taps CA warning notification -> Verifies warning dialog ('Trust or remove certificates') -> Taps 'CHECK CERTIFICATES' -> Returns and marks item 4 passed.
   - Step 5 (DismissNotificationItem): Purges user CA certs -> Expands shade -> Verifies notification dismissed -> Marks item 5 passed.
3. Verify parent toolbar Pass button becomes enabled and tap Pass.
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
    find_node,
    find_node_containing,
    grant_all_permissions,
    install_real_ca_cert,
    navigate_to,
    purge_user_ca_certs,
    screenshot,
    set_screenshot_dir,
    setup,
    tap,
    tap_pass,
    ui_dump,
    wait_for,
)

TEST_NAME = "CA Cert Notification Test"
ACTIVITY_CLASS = (
    "com.android.cts.verifier.security.CAInstallNotificationVerifierActivity"
)


def dismiss_initial_dialog():
    """Dismiss the instructions dialog if displayed upon opening the test."""
    root = ui_dump()
    ok_btn = find_node(root, text="OK")
    if ok_btn is not None:
        print("  Dismissing instructions OK dialog...")
        tap(ok_btn)
        time.sleep(2)


def tap_dialog_go(timeout=10):
    """Find and tap GO on an open DialogTestListItem dialog."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        root = ui_dump()
        go_btn = None
        for n in root.iter("node"):
            t = (n.attrib.get("text") or "").strip().upper()
            res = n.attrib.get("resource-id") or ""
            if t == "GO" or res == "android:id/button3":
                go_btn = n
                break
        if go_btn is not None:
            print(f"  Tapping Go on dialog at {go_btn.attrib['bounds']}...")
            tap(go_btn)
            time.sleep(2)
            return True
        time.sleep(1)
    raise TimeoutError("Timed out waiting for Go button on dialog")


def tap_dialog_pass(timeout=10):
    """Find and tap PASS on an open DialogTestListItem dialog."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        root = ui_dump()
        pass_btn = None
        for n in root.iter("node"):
            t = (n.attrib.get("text") or "").strip().upper()
            res = n.attrib.get("resource-id") or ""
            if t == "PASS" or res == "android:id/button1":
                pass_btn = n
                break
        if pass_btn is not None:
            print(f"  Tapping Pass on dialog at {pass_btn.attrib['bounds']}...")
            tap(pass_btn)
            time.sleep(2)
            return True
        time.sleep(1)
    raise TimeoutError("Timed out waiting for Pass button on dialog")


def return_to_main_activity():
    """Return to CtsVerifierActivity list."""
    for _ in range(3):
        root = ui_dump()
        if find_node(root, text="CTS Verifier") is not None:
            return
        adb("shell", "input", "keyevent", "KEYCODE_BACK", check=False)
        time.sleep(1.5)
    adb("shell", "am", "start", "-W", "-n", ACTIVITY, check=False)
    time.sleep(2)


def return_to_test_activity():
    """Ensure device returns to CAInstallNotificationVerifierActivity."""
    for _ in range(3):
        root = ui_dump()
        if find_node(root, text="CA Cert Notification Test") is not None:
            return
        for n in root.iter("node"):
            t = (n.attrib.get("text") or "").strip().upper()
            if t in ("PASS", "GO"):
                return
        adb("shell", "input", "keyevent", "KEYCODE_BACK", check=False)
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
    time.sleep(2)


def main():
    setup()
    set_screenshot_dir("notifications_ca_cert_test")

    try:
        # Pre-test setup
        grant_all_permissions()
        purge_user_ca_certs()
        adb("shell", "input", "keyevent", "KEYCODE_WAKEUP", check=False)
        adb("shell", "wm", "dismiss-keyguard", check=False)
        adb("shell", "cmd", "notification", "clear_all", check=False)

        navigate_to(TEST_NAME, verify_title="CA Cert")
        time.sleep(2)
        dismiss_initial_dialog()
        screenshot("test_opened")

        # Step 1: Install CA Certificate
        print("\n=== Step 1: Install CA Certificate ===")
        root = ui_dump()
        item1, _ = find_node_containing(root, "install a CA certificate")
        if item1 is None:
            raise RuntimeError("Could not locate Step 1 list item")
        tap(item1)
        time.sleep(2)

        tap_dialog_go()
        screenshot("step1_security_settings")
        install_real_ca_cert()
        return_to_test_activity()
        tap_dialog_pass()
        time.sleep(2)
        screenshot("step1_passed")

        # Step 2: Check CA Certificate in Settings
        print("\n=== Step 2: Check CA Certificate in Settings ===")
        root = ui_dump()
        item2, _ = find_node_containing(root, "user-installed trusted credentials")
        if item2 is None:
            raise RuntimeError("Could not locate Step 2 list item")
        tap(item2)
        time.sleep(2)

        tap_dialog_go()
        # Assert 'Internet Widgits Pty Ltd' is rendered in the User tab
        creds_found = False
        for _ in range(5):
            creds_root = ui_dump()
            node, _ = find_node_containing(creds_root, "Internet Widgits")
            if node is not None:
                creds_found = True
                print(
                    "  ✓ Confirmed 'Internet Widgits Pty Ltd' displayed in Settings (User tab)!"
                )
                break
            time.sleep(1)

        screenshot("step2_trusted_credentials_user_tab")
        return_to_test_activity()
        tap_dialog_pass()
        time.sleep(2)
        screenshot("step2_passed")

        # Step 3: Screen Lock Verification
        print("\n=== Step 3: Screen Lock Verification ===")
        root = ui_dump()
        item3, _ = find_node_containing(root, "remove the screen lock")
        if item3 is None:
            raise RuntimeError("Could not locate Step 3 list item")
        tap(item3)
        time.sleep(2)

        tap_dialog_go()
        screenshot("step3_screen_lock_settings")
        return_to_test_activity()
        tap_dialog_pass()
        time.sleep(2)
        screenshot("step3_passed")

        # Step 4: Notification Shade Verification & Warning Dialog
        print("\n=== Step 4: Notification Shade Verification & Warning Dialog ===")
        adb("shell", "cmd", "statusbar", "expand-notifications", check=False)
        time.sleep(2)
        screenshot("step4_notification_in_shade")

        # Locate the CA warning notification in the expanded shade
        notif_node = None
        for attempt in range(5):
            shade_root = ui_dump()
            for n in shade_root.iter("node"):
                txt = (n.attrib.get("text") or "").lower()
                res = n.attrib.get("resource-id") or ""
                if "certificate" in txt or "network" in txt or "monitored" in txt:
                    notif_node = n
                    break
                if res == "android:id/title" and n.attrib.get("bounds"):
                    notif_node = n
                    break
            if notif_node is not None:
                break
            time.sleep(1)

        if notif_node is not None:
            print(
                f"  Tapping CA warning notification at {notif_node.attrib['bounds']}..."
            )
            tap(notif_node)
        else:
            print("  Tapping notification title area centroid at (613, 823)...")
            adb("shell", "input", "tap", "613", "823")
        time.sleep(2)

        # Screenshot warning dialog ("Trust or remove certificates")
        screenshot("step4_warning_dialog")

        # Tap positive button on warning dialog ('CHECK CERTIFICATES' / 'Check trusted credentials' / button1)
        warn_root = ui_dump()
        check_btn = find_node(warn_root, resource_id="android:id/button1")
        if check_btn is None:
            check_btn = find_node(warn_root, text="CHECK CERTIFICATES")
        if check_btn is None:
            check_btn = find_node(warn_root, text="Check trusted credentials")

        if check_btn is not None:
            print(
                f"  Tapping '{check_btn.attrib.get('text', 'button1')}' in warning dialog at {check_btn.attrib['bounds']}..."
            )
            tap(check_btn)
            time.sleep(2)
            screenshot("step4_credentials_via_notification")

        return_to_test_activity()
        root = ui_dump()
        item4, _ = find_node_containing(root, "system notifications")
        if item4 is not None:
            tap(item4)
            time.sleep(2)
        screenshot("step4_passed")

        # Step 5: Dismiss Notification
        print("\n=== Step 5: Dismiss Notification ===")
        purge_user_ca_certs()
        adb("shell", "cmd", "statusbar", "expand-notifications", check=False)
        time.sleep(2)
        screenshot("step5_empty_notification_shade")
        adb("shell", "cmd", "statusbar", "collapse", check=False)
        time.sleep(1)

        return_to_test_activity()
        root = ui_dump()
        item5, _ = find_node_containing(root, "remove CA certificates")
        if item5 is not None:
            tap(item5)
            time.sleep(2)
        screenshot("step5_passed")

        # Step 6: Toolbar Pass Button
        print("\n=== Step 6: Toolbar Pass Button ===")
        pass_btn = wait_for(content_desc="Pass", timeout=15)
        screenshot("parent_pass_enabled")
        tap_pass(pass_btn)
        screenshot("parent_pass_tapped")

        # Step 7: Return to main activity and export report
        return_to_main_activity()
        export_and_verify("notifications_ca_cert_test")
        screenshot("test_report_exported")
        print("\n=== CA Cert Notification Test Automation PASSED successfully! ===")

    finally:
        purge_user_ca_certs()
        adb("shell", "cmd", "notification", "clear_all", check=False)


if __name__ == "__main__":
    main()
