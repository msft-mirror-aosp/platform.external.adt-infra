#!/usr/bin/env python3
"""
Automated test script for CtsVerifier test: Screen Lock Test
Verifies that DevicePolicyManager's lockNow() method immediately locks the screen.
Follows the Agent Execution & Alignment Guidelines (DEVELOPING_CTS_VERIFIER_AUTOMATION.md).
"""

import os
import sys
import time

sys.stdout.reconfigure(line_buffering=True)

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
    wait_for_screen_off,
    wait_for_keyguard_showing,
)

TEST_NAME = "Screen Lock Test"

set_screenshot_dir("screen_lock_test")

# Step 0: Setup & Device Preparation
# Ensure device has a lockscreen PIN set as required by test instructions
setup()
print("Step 0: Setting lockscreen PIN 1234 on device...")
adb("shell", "locksettings", "set-pin", "1234")
screenshot("app_launched")

# Step 1: Navigate to Screen Lock Test
print("Step 1: Navigating to Screen Lock Test...")
navigate_to(TEST_NAME)
time.sleep(2)
screenshot("test_opened")

# Step 2: Dismiss initial test instruction dialog ("This test checks that DevicePolicyManager's lockNow method...")
print("Step 2: Waiting for instruction dialog 'OK' button...")
ok_node = wait_for(text="OK", timeout=10)
print("Step 2: Tapping instruction dialog 'OK' button...")
tap(ok_node)

# Step 3: Wait for 'Force Lock' button to become available, then tap it to trigger Device Admin activation
print("Step 3: Waiting for 'Force Lock' button to appear...")
force_lock_btn = wait_for(text="Force Lock", timeout=10)
print("Step 3: Tapping 'Force Lock' button...")
tap(force_lock_btn)

# Step 4: Wait for Device Admin activation prompt (DeviceAdminAdd Activity), then tap 'Activate this device admin app'
print(
    "Step 4: Waiting for Device Admin activation screen ('Activate this device admin app')..."
)
admin_action_btn = wait_for(text="Activate this device admin app", timeout=10)
print("Step 4: Tapping 'Activate this device admin app'...")
tap(admin_action_btn)
# Enabling Device Admin immediately executes lockNow(), locking the device screen!
wait_for_screen_off(timeout=10)

# Step 5: Wake screen and wait for Keyguard prompt to become active before entering PIN 1234
print("Step 5: Waking screen (keycode 82)...")
adb("shell", "input", "keyevent", "82")
wait_for_keyguard_showing(timeout=10)
print("Step 5: Entering PIN 1234...")
adb("shell", "input", "text", "1234")
adb("shell", "input", "keyevent", "66")
time.sleep(2.0)

# Step 6: Wait for success alert dialog ("It appears the screen was locked successfully!"), then tap 'OK'
print(
    "Step 6: Waiting for success alert dialog ('It appears the screen was locked successfully!')..."
)
success_ok_node = wait_for(text="OK", timeout=15)
print("Step 6: Tapping 'OK' on success alert dialog...")
tap(success_ok_node)

# Step 7: Wait for green 'Pass' button to become enabled, then tap it
print("Step 7: Waiting for enabled Pass button...")
pass_btn = wait_for(content_desc="Pass", timeout=10)
print("Step 7: Tapping Pass button...")
tap_pass(pass_btn)
time.sleep(2.0)

# Step 8: Return to main CtsVerifier activity and export test result
print("Step 8: Exporting and verifying test result...")
adb("shell", "am", "start", "-n", "com.android.cts.verifier/.CtsVerifierActivity")
time.sleep(3.0)
export_and_verify(TEST_NAME)

print(f"✓ Finished {TEST_NAME} successfully!")
