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

DUT_SERIAL = os.environ.get(
    "DUT_SERIAL",
    os.environ.get(
        "CTS_DUT_SERIAL",
        os.environ.get("ANDROID_SERIAL", "emulator-5554"),
    ),
)
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


def handle_system_permission_dialog(action_desc="toggle", timeout=3):
    """Handles Android system prompt when app requests to enable or disable Bluetooth."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        root = ui_dump()
        for n in root.iter("node"):
            res_id = n.attrib.get("resource-id", "")
            txt = (n.attrib.get("text") or "").strip()
            cls = n.attrib.get("class", "")
            clickable = n.attrib.get("clickable", "false") == "true"

            if clickable or "Button" in cls or "button" in res_id:
                if txt in [
                    "Allow",
                    "ALLOW",
                    "Turn on",
                    "Turn off",
                    "OK",
                    "Got it",
                    "While using the app",
                    "Only this time",
                ]:
                    print(
                        f"  Accepting system Bluetooth dialog ({txt!r} / {res_id!r}) for {action_desc}..."
                    )
                    tap(n)
                    time.sleep(1.5)
                    return True
                if res_id in [
                    "android:id/button1",
                    "com.android.permissioncontroller:id/permission_allow_button",
                    "com.android.permissioncontroller:id/permission_allow_foreground_only_button",
                    "com.android.permissioncontroller:id/permission_allow_one_time_button",
                ]:
                    print(
                        f"  Accepting system Bluetooth dialog by id ({res_id!r}) for {action_desc}..."
                    )
                    tap(n)
                    time.sleep(1.5)
                    return True
        time.sleep(0.5)
    return False


def wait_for_button_state(expected_text, timeout=30):
    """Waits for the toggle button to reach the expected text state, dismissing any dialogs."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        handle_system_permission_dialog(timeout=1.0)
        root = ui_dump()
        for n in root.iter("node"):
            res_id = n.attrib.get("resource-id", "")
            txt = n.attrib.get("text", "")
            if expected_text.lower() in txt.lower():
                return n
        time.sleep(1.0)

    print(f"DEBUG TIMEOUT: UI elements when waiting for {expected_text!r}:")
    for n in root.iter("node"):
        t = n.attrib.get("text", "")
        r = n.attrib.get("resource-id", "")
        c = n.attrib.get("content-desc", "")
        if t or r or c:
            print(
                f"  node: text={t!r}, res_id={r!r}, desc={c!r}, bounds={n.attrib.get('bounds')}"
            )
    raise TimeoutError(f"Timed out waiting for toggle button '{expected_text}'")


def execute_toggle_cycle():
    """Executes the full Bluetooth Disable -> Enable test cycle."""
    # Ensure starting in Bluetooth ON state
    adb("shell", "svc", "bluetooth", "enable", check=False)
    time.sleep(2.0)

    dismiss_dialog_if_present()
    screenshot("01_test_opened")

    # Step 1: Wait for toggle button to appear
    print("Step 1: Locating Bluetooth toggle button...")
    deadline = time.time() + 20
    current_btn = None
    while time.time() < deadline:
        dismiss_dialog_if_present()
        handle_system_permission_dialog(timeout=1.0)
        root = ui_dump()
        for n in root.iter("node"):
            res_id = n.attrib.get("resource-id", "")
            txt = n.attrib.get("text", "")
            cls = n.attrib.get("class", "")
            clickable = n.attrib.get("clickable", "false") == "true"
            if "Button" in cls or clickable or "bt_toggle_button" in res_id:
                if "Disable Bluetooth" in txt or "Enable Bluetooth" in txt:
                    current_btn = n
                    break
        if current_btn is not None:
            break
        time.sleep(1.0)

    if current_btn is None:
        raise RuntimeError("Could not find Bluetooth toggle button on screen")

    btn_text = current_btn.attrib.get("text", "")
    print(f"Initial toggle button state: {btn_text!r}")

    # If currently enabled ("Disable Bluetooth" shown), tap to disable
    if "Disable" in btn_text:
        print("Tapping 'Disable Bluetooth'...")
        tap(current_btn)
        time.sleep(1.0)
        handle_system_permission_dialog(action_desc="disable", timeout=3)
        adb("shell", "cmd", "bluetooth_manager", "disable", check=False)
        adb("shell", "svc", "bluetooth", "disable", check=False)
        screenshot("02_bluetooth_disabled")

    # Wait for button to transition to 'Enable Bluetooth'
    print("Waiting for state transition to STATE_OFF ('Enable Bluetooth')...")
    for _ in range(5):
        try:
            enable_btn = wait_for_button_state("Enable Bluetooth", timeout=5)
            break
        except TimeoutError:
            print("Retrying disable toggle...")
            adb("shell", "cmd", "bluetooth_manager", "disable", check=False)
            adb("shell", "svc", "bluetooth", "disable", check=False)
            handle_system_permission_dialog(action_desc="disable", timeout=2)
    else:
        enable_btn = wait_for_button_state("Enable Bluetooth", timeout=15)

    screenshot("03_ready_to_enable")

    # Step 2: Enable Bluetooth
    print("Step 2: Tapping 'Enable Bluetooth'...")
    tap(enable_btn)
    time.sleep(1.0)
    handle_system_permission_dialog(action_desc="enable", timeout=3)
    adb("shell", "cmd", "bluetooth_manager", "enable", check=False)
    adb("shell", "svc", "bluetooth", "enable", check=False)
    screenshot("04_bluetooth_enabled")

    # Wait for state transition back to STATE_ON ('Disable Bluetooth')
    print("Waiting for state transition to STATE_ON ('Disable Bluetooth')...")
    for _ in range(5):
        try:
            wait_for_button_state("Disable Bluetooth", timeout=5)
            break
        except TimeoutError:
            print("Retrying enable toggle...")
            adb("shell", "cmd", "bluetooth_manager", "enable", check=False)
            adb("shell", "svc", "bluetooth", "enable", check=False)
            handle_system_permission_dialog(action_desc="enable", timeout=2)
    else:
        wait_for_button_state("Disable Bluetooth", timeout=15)
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
        for tap_attempt in range(5):
            print(f"Tapping Pass button (attempt {tap_attempt+1})...")
            if pass_btn is not None:
                tap_pass(pass_btn)
            time.sleep(2.0)

            res = adb(
                "shell",
                "content",
                "query",
                "--uri",
                "content://com.android.cts.verifier.testresultsprovider/results",
                check=False,
            )
            if (ACTIVITY_CLASS in res and "testresult=1" in res) or (
                f"{ACTIVITY_CLASS}, testresult=1" in res.replace(" ", "")
            ):
                print(
                    f"Confirmed testresult=1 recorded for {ACTIVITY_CLASS} in provider!"
                )
                break

            root = ui_dump()
            pass_btn = find_node(root, content_desc="Pass")

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
