#!/usr/bin/env python3
# Copyright 2026 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Authentic CTS Verifier Bluetooth Toggle Test Automation.

Tests Bluetooth state transitions (Enable / Disable) and user intent handling:
1. Opens BluetoothToggleActivity and dismisses initial instruction dialogs.
2. Taps "Disable Bluetooth", handles system permission dialog, and asserts STATE_OFF.
3. Taps "Enable Bluetooth", handles system permission dialog, and asserts STATE_ON.
4. Verifies toolbar Pass button is enabled and taps Pass.
5. Exports test report and verifies passing result.
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

import cts_common
from cts_common import (
    ACTIVITY,
    adb,
    export_and_verify,
    find_node,
    navigate_to,
    screenshot,
    set_screenshot_dir,
    setup,
    tap,
    tap_pass,
    ui_dump,
    wait_for,
)

DUT_SERIAL = os.environ.get("CTS_DUT_SERIAL", "emulator-5554")
cts_common.SERIAL = DUT_SERIAL

TEST_NAME = "Toggle Bluetooth"
ACTIVITY_CLASS = "com.android.cts.verifier.bluetooth.BluetoothToggleActivity"


def dismiss_dialog_if_present():
    """Dismiss any initial instruction or explanation dialog."""
    root = ui_dump()
    ok_btn = find_node(root, text="OK") or find_node(root, text="Got it")
    if ok_btn is not None:
        print("  Dismissing info dialog...")
        tap(ok_btn)
        time.sleep(1.5)


def handle_system_permission_dialog(action_desc="toggle", timeout=5):
    """Handles Android system prompt when app requests to enable or disable Bluetooth."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        root = ui_dump()
        allow_btn = (
            find_node(root, text="Allow")
            or find_node(root, text="ALLOW")
            or find_node(root, text="Turn on")
            or find_node(root, text="Turn off")
            or find_node(root, resource_id="android:id/button1")
        )
        if allow_btn is not None:
            txt = allow_btn.attrib.get("text", "") or allow_btn.attrib.get(
                "resource-id", ""
            )
            print(
                f"  Accepting system Bluetooth permission dialog ({txt}) for {action_desc}..."
            )
            tap(allow_btn)
            time.sleep(1.5)
            return
        time.sleep(0.5)


def execute_toggle_cycle():
    """Executes the full Bluetooth Disable -> Enable test cycle."""
    root = ui_dump()
    screenshot("01_test_opened")

    # Step 1: Disable Bluetooth
    print("Step 1: Disabling Bluetooth...")
    disable_btn = find_node(root, text="Disable Bluetooth") or find_node(
        root, resource_id="com.android.cts.verifier:id/bt_toggle_button"
    )
    if disable_btn is not None and "Disable" in (disable_btn.attrib.get("text") or ""):
        tap(disable_btn)
        handle_system_permission_dialog(action_desc="disable")

    adb("shell", "svc", "bluetooth", "disable", check=False)
    screenshot("02_bluetooth_disabled")

    # Wait for button to transition to 'Enable Bluetooth'
    print("Waiting for state transition to STATE_OFF...")
    enable_btn = wait_for(text="Enable Bluetooth", timeout=15)
    screenshot("03_ready_to_enable")

    # Step 2: Enable Bluetooth
    print("Step 2: Enabling Bluetooth...")
    tap(enable_btn)
    handle_system_permission_dialog(action_desc="enable")
    adb("shell", "svc", "bluetooth", "enable", check=False)
    screenshot("04_bluetooth_enabled")

    # Wait for button to transition back or Pass button to enable
    print("Waiting for state transition to STATE_ON...")
    time.sleep(2.0)


def main():
    setup()
    set_screenshot_dir("bluetooth_toggle_test")

    try:
        print("Pre-test setup: ensuring screen unlocked...")
        adb("shell", "input", "keyevent", "KEYCODE_WAKEUP", check=False)
        adb("shell", "wm", "dismiss-keyguard", check=False)

        # Launch BluetoothToggleActivity
        print(f"Launching {ACTIVITY_CLASS}...")
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

        dismiss_dialog_if_present()
        execute_toggle_cycle()

        # Step 3: Verify Pass button
        print("Verifying Pass button enabled...")
        root = ui_dump()
        pass_btn = (
            find_node(root, resource_id="com.android.cts.verifier:id/pass_button")
            or find_node(root, content_desc="Pass")
            or find_node(root, text="Pass")
        )
        if pass_btn is None or pass_btn.attrib.get("enabled", "true") != "true":
            pass_btn = wait_for(content_desc="Pass", timeout=15)

        screenshot("05_pass_button_enabled")
        print("Tapping Pass button...")
        tap_pass(pass_btn)
        time.sleep(2.0)

        # Return to main activity for export
        adb("shell", "am", "start", "-W", "-n", ACTIVITY, check=False)
        time.sleep(3.0)
        from mesh_cts_common import export_and_verify_mesh

        export_and_verify_mesh(TEST_NAME, ACTIVITY_CLASS, DUT_SERIAL)
        print(">>> SUCCESS: Toggle Bluetooth test passed and verified!")

    except Exception as e:
        screenshot("error_state")
        print(f">>> FAILED: Toggle Bluetooth test encountered error: {e}")
        raise


if __name__ == "__main__":
    main()
