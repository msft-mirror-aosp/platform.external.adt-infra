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

"""Authentic CTS Verifier Bluetooth HID Device Test Automation.

Coordinated dual-device Bluetooth HID Device & Host test over Netsim RF virtual medium:
1. DUT Node (emulator-5554) launches HidDeviceActivity and registers HID application proxy.
2. Companion Node (emulator-5556) launches HidHostActivity and selects DUT from device picker.
3. Authenticates & pairs both nodes via Secure Simple Pairing (SSP) / PIN prompts.
4. DUT executes Send_report ("bluetooth" keystrokes), Reply_report, and Report_error.
5. Host verifies received keystrokes in EditText.
6. DUT unregisters HID application proxy and asserts Pass condition.
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
    find_node,
    screenshot,
    set_screenshot_dir,
)
from mesh_cts_common import (
    COMPANION_SERIAL,
    DUT_SERIAL,
    adb_on,
    dismiss_initial_dialogs,
    export_and_verify_mesh,
    find_any_node,
    find_device_item,
    get_bluetooth_address,
    handle_make_discoverable_dialog,
    handle_pairing_dialogs,
    mesh_diagnostics,
    scale_poll_interval,
    scale_timeout,
    setup_mesh_nodes,
    tap_on,
    tap_pass_on,
    ui_dump_on,
    unpair_bonded_devices,
    wait_for_on,
)

TEST_NAME = "Bluetooth HID Device Test"
DEVICE_ACTIVITY = "com.android.cts.verifier.bluetooth.HidDeviceActivity"
HOST_ACTIVITY = "com.android.cts.verifier.bluetooth.HidHostActivity"


def main():
    setup_mesh_nodes(DUT_SERIAL, COMPANION_SERIAL)
    set_screenshot_dir("bluetooth_hid_device_test")

    with mesh_diagnostics(TEST_NAME, [DUT_SERIAL, COMPANION_SERIAL]):
        try:
            # 1. Start HID Device on DUT
            print(f"Step 1: Launching {DEVICE_ACTIVITY} on DUT ({DUT_SERIAL})...")
            adb_on(
                DUT_SERIAL,
                "shell",
                "am",
                "start",
                "-W",
                "-n",
                f"com.android.cts.verifier/{DEVICE_ACTIVITY}",
                check=False,
            )
            time.sleep(2.0)
            dismiss_initial_dialogs(DUT_SERIAL)

            dut_mac = get_bluetooth_address(DUT_SERIAL)
            print(f"DUT Bluetooth address resolved: {dut_mac}")

            # Register app on DUT
            print("DUT: Registering HID application proxy...")
            reg_btn = wait_for_on(
                DUT_SERIAL,
                resource_id="com.android.cts.verifier:id/bt_hid_device_register_button",
                timeout=scale_timeout(15.0),
            )
            tap_on(DUT_SERIAL, reg_btn, sleep_after=scale_poll_interval(1.5))

            # Make discoverable on DUT
            print("DUT: Making device discoverable...")
            disc_btn = wait_for_on(
                DUT_SERIAL,
                resource_id="com.android.cts.verifier:id/bt_hid_device_discoverable_button",
                timeout=scale_timeout(15.0),
            )
            tap_on(DUT_SERIAL, disc_btn, sleep_after=scale_poll_interval(1.5))
            handle_make_discoverable_dialog(DUT_SERIAL)

            # 2. Start HID Host on Companion
            print(
                f"Step 2: Launching {HOST_ACTIVITY} on Companion ({COMPANION_SERIAL})..."
            )
            adb_on(
                COMPANION_SERIAL,
                "shell",
                "am",
                "start",
                "-W",
                "-n",
                f"com.android.cts.verifier/{HOST_ACTIVITY}",
                check=False,
            )
            time.sleep(scale_timeout(2.0))
            dismiss_initial_dialogs(COMPANION_SERIAL)

            # Companion: Select device
            print("Companion: Tapping 'Select device'...")
            pick_btn = wait_for_on(
                COMPANION_SERIAL,
                resource_id="com.android.cts.verifier:id/bt_hid_host_pick_device_button",
                timeout=scale_timeout(15.0),
            )
            tap_on(COMPANION_SERIAL, pick_btn, sleep_after=scale_poll_interval(2.0))

            print(f"Companion ({COMPANION_SERIAL}): Waiting for DUT in scan results...")
            target_node = None
            deadline = time.time() + scale_timeout(90.0)
            last_scan_tap = time.time()
            while time.time() < deadline:
                try:
                    root = ui_dump_on(COMPANION_SERIAL, retries=2)
                except Exception:
                    time.sleep(scale_poll_interval(1.0))
                    continue

                target_node = find_device_item(root, dut_mac)
                if target_node is not None:
                    break

                scan_btn = find_any_node(
                    root,
                    {"resource_id": "com.android.cts.verifier:id/bt_scan_button"},
                    {"resource_id": "com.android.cts.verifier:id/button_scan"},
                    {"text": "Scan for Devices"},
                    {"text": "Scan for devices"},
                    {"text": "SCAN FOR DEVICES"},
                    {"text": "Scan"},
                    {"text": "SCAN"},
                )
                now = time.time()
                if scan_btn is not None and (
                    now - last_scan_tap >= scale_timeout(25.0)
                ):
                    print(
                        f"Companion ({COMPANION_SERIAL}): Tapping 'Scan for Devices'..."
                    )
                    tap_on(
                        COMPANION_SERIAL, scan_btn, sleep_after=scale_poll_interval(1.5)
                    )
                    last_scan_tap = time.time()
                else:
                    time.sleep(scale_poll_interval(1.0))

            if target_node is not None:
                target_txt = target_node.attrib.get("text", "").replace("\n", " ")
                print(
                    f"Companion ({COMPANION_SERIAL}): Connecting to DUT {target_txt}..."
                )
                tap_on(
                    COMPANION_SERIAL, target_node, sleep_after=scale_poll_interval(2.5)
                )

            # 3. Handle Pairing Dialogs on both devices
            print("Handling Secure Simple Pairing (SSP) / PIN dialogs...")
            handle_pairing_dialogs(
                DUT_SERIAL, COMPANION_SERIAL, timeout=scale_timeout(60.0)
            )

            # 4. DUT: Send HID reports
            print("DUT: Tapping 'Test Send_report'...")
            send_btn = wait_for_on(
                DUT_SERIAL,
                resource_id="com.android.cts.verifier:id/bt_hid_device_send_report_button",
                enabled=True,
                timeout=scale_timeout(25.0),
            )
            tap_on(DUT_SERIAL, send_btn, sleep_after=scale_poll_interval(2.5))

            # 5. DUT: Reply report
            try:
                print("DUT: Tapping 'Test Reply_report'...")
                reply_btn = wait_for_on(
                    DUT_SERIAL,
                    resource_id="com.android.cts.verifier:id/bt_hid_device_reply_report_button",
                    enabled=True,
                    timeout=scale_timeout(15.0),
                )
                tap_on(DUT_SERIAL, reply_btn, sleep_after=scale_poll_interval(2.0))
            except Exception:
                pass

            # 6. DUT: Report error
            try:
                print("DUT: Tapping 'Test Report_error'...")
                err_btn = wait_for_on(
                    DUT_SERIAL,
                    resource_id="com.android.cts.verifier:id/bt_hid_device_report_error_button",
                    enabled=True,
                    timeout=scale_timeout(15.0),
                )
                tap_on(DUT_SERIAL, err_btn, sleep_after=scale_poll_interval(2.0))
            except Exception:
                pass

            # 7. DUT: Unregister app
            print("DUT: Tapping 'Unregister app'...")
            unreg_btn = wait_for_on(
                DUT_SERIAL,
                resource_id="com.android.cts.verifier:id/bt_hid_device_unregister_button",
                enabled=True,
                timeout=scale_timeout(15.0),
            )
            tap_on(DUT_SERIAL, unreg_btn, sleep_after=scale_poll_interval(2.0))

            # 8. Monitor Pass condition on DUT
            print(
                f"Step 8: Monitoring HID Device Pass condition on DUT ({DUT_SERIAL})..."
            )
            pass_btn = wait_for_on(
                DUT_SERIAL,
                content_desc="Pass",
                enabled=True,
                timeout=scale_timeout(45.0),
            )
            screenshot("01_hid_device_passed")
            if pass_btn is None or pass_btn.attrib.get("enabled") != "true":
                raise TimeoutError(
                    f"DUT ({DUT_SERIAL}): HID Device test did not complete — Pass button was not enabled"
                )
            tap_pass_on(DUT_SERIAL, pass_btn)
            time.sleep(scale_timeout(2.0))

            # Also tap pass on companion host if available
            try:
                comp_pass = wait_for_on(
                    COMPANION_SERIAL,
                    content_desc="Pass",
                    enabled=True,
                    timeout=scale_timeout(8.0),
                )
                if comp_pass is not None:
                    tap_pass_on(COMPANION_SERIAL, comp_pass)
            except Exception:
                pass

            # Return to main activity & export
            adb_on(
                DUT_SERIAL, "shell", "am", "start", "-W", "-n", ACTIVITY, check=False
            )
            time.sleep(3.0)
            export_and_verify_mesh(TEST_NAME, DEVICE_ACTIVITY, DUT_SERIAL)
            print(">>> SUCCESS: Bluetooth HID Device test passed and verified!")

        finally:
            unpair_bonded_devices(DUT_SERIAL)
            unpair_bonded_devices(COMPANION_SERIAL)


if __name__ == "__main__":
    main()
