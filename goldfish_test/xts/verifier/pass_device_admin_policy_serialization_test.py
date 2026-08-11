#!/usr/bin/env python3
"""
Policy Serialization Test (DEVICE ADMINISTRATION)
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
    reboot_and_wait,
    dismiss_dialogs_and_wait_for_pass,
    wait_for,
)

TEST_NAME = "Policy Serialization Test"
ACTIVITY_CLASS = "com.android.cts.verifier.admin.PolicySerializationTestActivity"

set_screenshot_dir("device_admin_policy_serialization")

setup()
screenshot("app_launched")

# Ensure device is awake and unlocked
adb("shell", "input", "keyevent", "KEYCODE_WAKEUP", check=False)
adb("shell", "input", "keyevent", "82", check=False)
time.sleep(1)

# Flaky Navigation Retry
for attempt in range(3):
    try:
        print(f"Navigating to '{TEST_NAME}' (attempt {attempt + 1})...")
        navigate_to(TEST_NAME)
        break
    except Exception as e:
        print(f"  Navigation failed (attempt {attempt + 1}): {e}")
        adb("shell", "am", "force-stop", "com.android.cts.verifier")
        time.sleep(2)
        adb(
            "shell",
            "am",
            "start",
            "-n",
            "com.android.cts.verifier/.CtsVerifierActivity",
        )
        time.sleep(4)

time.sleep(2)
screenshot("test_opened")

root = ui_dump()
ok = find_node(root, text="OK")
if ok is not None:
    tap(ok)
    time.sleep(1.5)

# Step 1: Tap "Generate Policy"
root = ui_dump()
gen_btn = find_node(root, text="Generate Policy")
if gen_btn is not None:
    print("Tapping 'Generate Policy'...")
    tap(gen_btn)
    time.sleep(1.5)

# Step 2: Tap "Apply Policy"
root = ui_dump()
apply_btn = find_node(root, text="Apply Policy")
if apply_btn is not None and apply_btn.attrib.get("enabled") == "true":
    print("Tapping 'Apply Policy'...")
    tap(apply_btn)
    time.sleep(2)

    # Check if device admin activation screen appeared
    root = ui_dump()
    act_btn = (
        find_node(root, text="Activate this device admin app")
        or find_node(root, text="Activate")
        or find_node(root, text="Activate this device admin")
    )
    if act_btn is None:
        for node in root.iter("node"):
            r_id = node.attrib.get("resource-id", "")
            txt = node.attrib.get("text", "")
            if (
                "admin_action_button" in r_id
                or "action_button" in r_id
                or "activate" in txt.lower()
            ):
                print(
                    f"  Found admin action button: text={txt!r}, resource-id={r_id!r}"
                )
                act_btn = node
                break
    if act_btn is not None:
        print(f"Tapping 'Activate device admin' ({act_btn.attrib.get('text')})...")
        tap(act_btn)
        time.sleep(3)

    # Check for OK button on popup dialog ("Reboot your device and return to this CTS Verifier test.")
    root = ui_dump()
    ok_btn = find_node(root, text="OK")
    if ok_btn is not None:
        print("Tapping 'OK' on reboot prompt dialog...")
        tap(ok_btn)
        time.sleep(2)

    # Execute smart reboot logic via VerifierState
    reboot_and_wait(max_retries=120, poll_interval=1)

    print("Reboot complete! Re-opening CtsVerifier to verify persisted policies...")
    adb("shell", "am", "start", "-n", "com.android.cts.verifier/.CtsVerifierActivity")
    time.sleep(4)

    print(f"Re-navigating to '{TEST_NAME}'...")
    navigate_to(TEST_NAME)
    time.sleep(2)

    # Step 3: Wait for Pass button to be enabled post-reboot and tap it
    print("Waiting for Pass button to become enabled post-reboot...")
    pass_btn = dismiss_dialogs_and_wait_for_pass(timeout=15)
    print("Pass button enabled! Physically tapping green checkmark...")
    tap(pass_btn)
    time.sleep(2)

# Ensure return to main activity for report export
print("Navigating to main activity for report export...")
adb("shell", "am", "start", "-n", "com.android.cts.verifier/.CtsVerifierActivity")
time.sleep(3)
root = ui_dump()
ok = find_node(root, text="OK")
if ok is not None:
    tap(ok)
    time.sleep(1.5)

export_and_verify(TEST_NAME)
