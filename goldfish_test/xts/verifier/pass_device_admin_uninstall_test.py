#!/usr/bin/env python3
"""
State-synchronized automation script for CtsVerifier 'Device Admin Uninstall Test'.
Generated via TestBuilder & verified for 100% hermetic pass.
"""

import os
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(SCRIPT_DIR)

from cts_common import (
    adb,
    setup,
    navigate_to,
    ui_dump,
    find_node,
    tap,
    tap_pass,
    screenshot,
    set_screenshot_dir,
    export_and_verify,
    wait_for,
    install_empty_device_admin,
)

TEST_NAME = "Device Admin Uninstall Test"

set_screenshot_dir("device_admin_uninstall_test")


def main():
    print(f"Starting automation for: {TEST_NAME}")

    # Step 0: Setup & Launch CtsVerifier
    setup()
    screenshot("app_launched")

    # Step 1: Navigate to Device Admin Uninstall Test
    navigate_to(TEST_NAME)
    time.sleep(2)
    screenshot("test_opened")

    # Step 2: Dismiss instruction dialog if present
    try:
        ok_btn = wait_for(text="OK", timeout=5)
        print("Dismissing instruction dialog...")
        tap(ok_btn)
        time.sleep(1)
    except Exception as e:
        print(f"No instruction dialog present or already dismissed: {e}")

    # Step 3: Install CtsEmptyDeviceAdmin.apk as directed by test instructions
    print("Installing CtsEmptyDeviceAdmin.apk as directed by test instructions...")
    install_empty_device_admin()

    # Step 4: Tap 'Enable admin' button to open DeviceAdminAdd screen
    print("Tapping 'Enable admin' button...")
    enable_admin_btn = wait_for(text="Enable admin", timeout=20)
    tap(enable_admin_btn)
    time.sleep(2)
    screenshot("device_admin_add_opened")

    # Step 5: Activate Device Admin in DeviceAdminAdd activity
    print("Activating device admin in DeviceAdminAdd...")
    activate_btn = wait_for(
        resource_id="com.android.settings:id/restricted_action", timeout=15
    )
    tap(activate_btn)
    time.sleep(2)
    screenshot("device_admin_activated")

    # Step 6: Tap 'Launch settings' to open App Details (SpaActivity)
    print("Tapping 'Launch settings'...")
    launch_settings_btn = wait_for(text="Launch settings", timeout=15)
    tap(launch_settings_btn)
    time.sleep(2)
    screenshot("spa_activity_opened")

    # Step 7: Tap 'Uninstall' button in App Details (SpaActivity)
    print("Tapping 'Uninstall' in App Details...")
    uninstall_btn = wait_for(text="Uninstall", timeout=15)
    tap(uninstall_btn)
    time.sleep(2)
    screenshot("deactivate_prompt_opened")

    # Step 8: Tap 'Deactivate & uninstall' in DeviceAdminAdd activity
    print("Tapping 'Deactivate & uninstall'...")
    deactivate_btn = wait_for(
        resource_id="com.android.settings:id/restricted_action", timeout=15
    )
    tap(deactivate_btn)
    time.sleep(2)
    screenshot("uninstall_confirm_dialog_opened")

    # Step 9: Confirm Uninstall in System PackageInstaller Dialog
    print("Confirming uninstall in system dialog...")
    confirm_uninstall_btn = wait_for(text="Uninstall", timeout=15)
    tap(confirm_uninstall_btn)
    time.sleep(3)
    screenshot("returned_to_test_activity")

    # Step 10: Verify Pass button enabled & complete test
    print("Verifying Pass button and completing test...")
    pass_btn = wait_for(content_desc="Pass", timeout=15)
    tap_pass(pass_btn)
    time.sleep(2)

    # Return to main activity & export results
    adb("shell", "am", "start", "-n", "com.android.cts.verifier/.CtsVerifierActivity")
    time.sleep(3)
    export_and_verify(TEST_NAME)


if __name__ == "__main__":
    main()
