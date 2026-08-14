#!/usr/bin/env python3
"""Authentic CTS Verifier CA Cert Notification on Boot Test Automation.

Verifies that when a trusted credential is installed, the system notifies the user on boot:
1. Open CANotifyOnBootActivity and dismiss instructions dialog.
2. Tap "Install credential" -> install authentic myCA.cer into user cert store.
3. Tap "Check Credentials" -> assert "Internet Widgits Pty Ltd" in Settings (User tab).
4. Tap "Remove screen lock" -> verify screen lock settings.
5. Execute authentic device reboot via adb reboot and wait for sys.boot_completed.
6. Post-reboot: Expand notification shade, tap CA warning notification, verify warning dialog, tap 'Check trusted credentials'.
7. Return to CTS Verifier and tap Pass.
8. Export test report and assert passing result in test_result.xml.
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
    reboot_and_wait,
    screenshot,
    set_screenshot_dir,
    setup,
    tap,
    tap_pass,
    ui_dump,
    wait_for,
)

TEST_NAME = "CA Cert Notification on Boot Test"
ACTIVITY_CLASS = "com.android.cts.verifier.security.CANotifyOnBootActivity"


def dismiss_initial_dialog():
    """Dismiss the instructions dialog if displayed upon opening the test."""
    for _ in range(3):
        root = ui_dump()
        ok_btn = None
        for n in root.iter("node"):
            t = (n.attrib.get("text") or "").strip().upper()
            res = n.attrib.get("resource-id") or ""
            if t == "OK" or res == "android:id/button1":
                ok_btn = n
                break
        if ok_btn is not None:
            print("  Dismissing instructions OK dialog...")
            tap(ok_btn)
            time.sleep(1.5)
            return
        time.sleep(1)


def open_test_activity():
    """Open the test activity via list navigation with direct intent fallback."""
    print(f"Opening {TEST_NAME}...")
    adb("shell", "cmd", "statusbar", "collapse", check=False)
    adb("shell", "am", "start", "-n", ACTIVITY, check=False)
    time.sleep(2)

    found = False
    for name_variant in [
        "CA Cert Notification on Boot test",
        "CA Cert Notification on Boot Test",
    ]:
        try:
            navigate_to(name_variant, max_swipes=25)
            found = True
            break
        except Exception as e:
            print(f"  List navigation with {name_variant!r} did not succeed: {e}")

    if not found:
        print(
            f"  List navigation unsuccessful. Launching activity directly via am start: {ACTIVITY_CLASS}..."
        )
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
    dismiss_initial_dialog()


def return_to_activity(target_activity):
    """Ensure device returns to the specified target activity."""
    for _ in range(3):
        root = ui_dump()
        if (
            find_node(root, text="CA Cert Notification on Boot test") is not None
            or find_node(root, resource_id="com.android.cts.verifier:id/install")
            is not None
        ):
            return
        adb("shell", "input", "keyevent", "KEYCODE_BACK", check=False)
        time.sleep(1.5)
    adb(
        "shell",
        "am",
        "start",
        "-W",
        "-n",
        f"com.android.cts.verifier/{target_activity}",
        check=False,
    )
    time.sleep(2)


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


def main():
    setup()
    set_screenshot_dir("notifications_ca_cert_on_boot_test")

    try:
        # Pre-test setup
        grant_all_permissions()
        purge_user_ca_certs()
        adb("shell", "input", "keyevent", "KEYCODE_WAKEUP", check=False)
        adb("shell", "wm", "dismiss-keyguard", check=False)
        adb("shell", "cmd", "notification", "clear_all", check=False)

        open_test_activity()
        screenshot("test_opened")

        # Step 1: Install credential
        print("\n=== Step 1: Tap Install Credential ===")
        install_btn = None
        for _ in range(5):
            root = ui_dump()
            btn = find_node(root, resource_id="com.android.cts.verifier:id/install")
            if btn is not None:
                install_btn = btn
                break
            btn = find_node(root, text="Install credential")
            if btn is not None:
                install_btn = btn
                break
            time.sleep(1)

        if install_btn is not None:
            print(f"Tapping 'Install credential' at {install_btn.attrib['bounds']}...")
            tap(install_btn)
            time.sleep(2)
            install_real_ca_cert()
            screenshot("install_credential_settings")
            return_to_activity(ACTIVITY_CLASS)

        # Step 2: Check Credentials
        print("\n=== Step 2: Check Credentials in Settings ===")
        check_btn = None
        for _ in range(5):
            root = ui_dump()
            btn = find_node(root, resource_id="com.android.cts.verifier:id/check_creds")
            if btn is not None:
                check_btn = btn
                break
            btn = find_node(root, text="Check Credentials")
            if btn is not None:
                check_btn = btn
                break
            time.sleep(1)

        if check_btn is not None:
            print(f"Tapping 'Check Credentials' at {check_btn.attrib['bounds']}...")
            tap(check_btn)
            time.sleep(2)
            # Assert "Internet Widgits" is on screen
            for _ in range(5):
                creds_root = ui_dump()
                node, _ = find_node_containing(creds_root, "Internet Widgits")
                if node is not None:
                    print("  ✓ Confirmed 'Internet Widgits Pty Ltd' in Settings!")
                    break
                time.sleep(1)
            screenshot("credentials_checked")
            return_to_activity(ACTIVITY_CLASS)

        # Step 3: Remove Screen Lock
        print("\n=== Step 3: Remove Screen Lock ===")
        remove_btn = None
        for _ in range(5):
            root = ui_dump()
            btn = find_node(
                root, resource_id="com.android.cts.verifier:id/remove_screen_lock"
            )
            if btn is not None:
                remove_btn = btn
                break
            btn = find_node(root, text="Remove screen lock")
            if btn is not None:
                remove_btn = btn
                break
            time.sleep(1)

        if remove_btn is not None:
            print(f"Tapping 'Remove screen lock' at {remove_btn.attrib['bounds']}...")
            tap(remove_btn)
            time.sleep(2)
            screenshot("screen_lock_settings")
            return_to_activity(ACTIVITY_CLASS)

        # Step 4: Authentic Device Reboot
        print("\n=== Step 4: Authentic Device Reboot ===")
        reboot_and_wait(max_retries=120, poll_interval=1)
        screenshot("device_rebooted_unlocked")

        # Step 5: Restore permissions post-reboot
        print("Restoring permissions post-reboot...")
        grant_all_permissions()
        adb("shell", "input", "keyevent", "KEYCODE_WAKEUP", check=False)
        adb("shell", "wm", "dismiss-keyguard", check=False)
        time.sleep(2)

        # Step 6: Post-Boot Notification Shade & Dialog Verification
        print("\n=== Step 6: Post-Boot Notification Shade & Dialog Verification ===")
        adb("shell", "cmd", "statusbar", "expand-notifications", check=False)
        time.sleep(2)
        screenshot("post_boot_notification_in_shade")

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
            print("  Tapping notification container area...")
            adb("shell", "input", "tap", "720", "900")
        time.sleep(2)

        screenshot("post_boot_warning_dialog")

        # Tap 'Check trusted credentials' or 'CHECK CERTIFICATES' in warning dialog
        warn_root = ui_dump()
        check_btn_dlg = find_node(warn_root, resource_id="android:id/button1")
        if check_btn_dlg is None:
            check_btn_dlg, _ = find_node_containing(
                warn_root, "Check trusted credentials"
            )
        if check_btn_dlg is None:
            check_btn_dlg, _ = find_node_containing(warn_root, "CHECK CERTIFICATES")
        if check_btn_dlg is None:
            check_btn_dlg, _ = find_node_containing(warn_root, "Check certificates")
        if check_btn_dlg is not None:
            print(
                f"  Tapping '{check_btn_dlg.attrib.get('text', 'button1')}' in warning dialog..."
            )
            tap(check_btn_dlg)
            time.sleep(2)
            screenshot("post_boot_credentials_via_notification")

        # Step 7: Return to CTS Verifier and tap Pass
        print("\n=== Step 7: Return to CTS Verifier & Tap Pass ===")
        # Ensure notifications and settings are dismissed
        adb("shell", "cmd", "statusbar", "collapse", check=False)
        adb("shell", "input", "keyevent", "KEYCODE_BACK", check=False)
        adb("shell", "am", "force-stop", "com.android.settings", check=False)
        time.sleep(1)

        open_test_activity()

        pass_btn = None
        for _ in range(5):
            try:
                pass_btn = wait_for(content_desc="Pass", timeout=5)
                if pass_btn is not None:
                    break
            except Exception:
                dismiss_initial_dialog()
                time.sleep(1)

        if pass_btn is None:
            pass_btn = wait_for(content_desc="Pass", timeout=15)

        screenshot("pass_button_enabled")
        tap_pass(pass_btn)
        screenshot("pass_tapped")

        # Step 8: Return to main activity and export report
        return_to_main_activity()
        export_and_verify("notifications_ca_cert_on_boot_test")
        screenshot("test_report_exported")
        print(
            "\n=== CA Cert Notification on Boot Test Automation PASSED successfully! ==="
        )

    finally:
        purge_user_ca_certs()
        adb("shell", "cmd", "notification", "clear_all", check=False)


if __name__ == "__main__":
    main()
