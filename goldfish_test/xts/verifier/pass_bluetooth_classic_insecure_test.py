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

"""Authentic CTS Verifier Bluetooth Classic Insecure Client/Server Test Automation.

Coordinated dual-device test over Netsim RF virtual medium:
1. Companion Node (emulator-5556) launches InsecureServerActivity & makes itself discoverable.
2. DUT Node (emulator-5554) launches InsecureClientActivity & scans for nearby devices.
3. DUT connects to Companion over unauthenticated RFCOMM socket.
4. Bidirectional exchange of 10 messages verified.
5. Asserts Pass button enabled, taps Pass, and exports verification report.
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
    tap_pass,
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
    make_device_discoverable,
    mesh_diagnostics,
    setup_mesh_nodes,
    tap_on,
    ui_dump_on,
    unpair_bonded_devices,
    wait_for_mesh_pass,
    wait_for_on,
)

TEST_NAME = "Insecure Client"
CLIENT_ACTIVITY = "com.android.cts.verifier.bluetooth.InsecureClientActivity"
SERVER_ACTIVITY = "com.android.cts.verifier.bluetooth.InsecureServerActivity"


def main():
    setup_mesh_nodes(DUT_SERIAL, COMPANION_SERIAL)
    set_screenshot_dir("bluetooth_classic_insecure_test")

    with mesh_diagnostics(TEST_NAME, [DUT_SERIAL, COMPANION_SERIAL]):
        try:
            # 1. Start Server on Companion
            print(
                f"Step 1: Launching {SERVER_ACTIVITY} on Companion ({COMPANION_SERIAL})..."
            )
            adb_on(
                COMPANION_SERIAL,
                "shell",
                "am",
                "start",
                "-W",
                "-n",
                f"com.android.cts.verifier/{SERVER_ACTIVITY}",
                check=False,
            )
            time.sleep(2.0)
            dismiss_initial_dialogs(COMPANION_SERIAL)

            comp_mac = get_bluetooth_address(COMPANION_SERIAL)
            print(f"Companion address resolved: {comp_mac}")

            print(f"Companion ({COMPANION_SERIAL}): Making device discoverable...")
            make_device_discoverable(COMPANION_SERIAL, timeout=35)

            # 2. Start Client on DUT
            print(f"Step 2: Launching {CLIENT_ACTIVITY} on DUT ({DUT_SERIAL})...")
            adb_on(
                DUT_SERIAL,
                "shell",
                "am",
                "start",
                "-W",
                "-n",
                f"com.android.cts.verifier/{CLIENT_ACTIVITY}",
                check=False,
            )
            time.sleep(2.0)
            dismiss_initial_dialogs(DUT_SERIAL)

            # DUT opens DevicePickerActivity automatically; tap scan if present
            try:
                scan_btn = wait_for_on(
                    DUT_SERIAL,
                    resource_id="com.android.cts.verifier:id/bt_scan_button",
                    timeout=5,
                )
                print(f"DUT ({DUT_SERIAL}): Tapping 'Scan'...")
                tap_on(DUT_SERIAL, scan_btn, sleep_after=1.5)
            except Exception:
                pass

            # 3. Select Companion device on DUT
            print(f"DUT ({DUT_SERIAL}): Waiting for Companion in scan results...")
            target_node = None
            deadline = time.time() + 45
            last_scan_tap = time.time()
            while time.time() < deadline:
                root = ui_dump_on(DUT_SERIAL, retries=2)
                target_node = find_device_item(root, comp_mac)
                if target_node is not None:
                    break

                now = time.time()
                if now - last_scan_tap >= 5.0:
                    scan_btn = find_any_node(
                        root,
                        {"resource_id": "com.android.cts.verifier:id/bt_scan_button"},
                        {"resource_id": "com.android.cts.verifier:id/button_scan"},
                        {"text": "Scan for devices"},
                        {"text": "SCAN FOR DEVICES"},
                        {"text": "Scan"},
                        {"text": "SCAN"},
                    )
                    if scan_btn is not None:
                        tap_on(DUT_SERIAL, scan_btn, sleep_after=1.5)
                        last_scan_tap = time.time()
                    else:
                        time.sleep(1.0)
                else:
                    time.sleep(1.0)

            if target_node is not None:
                target_txt = target_node.attrib.get("text", "").replace("\n", " ")
                print(f"DUT ({DUT_SERIAL}): Connecting to target {target_txt}...")
                tap_on(DUT_SERIAL, target_node, sleep_after=0.2)
            else:
                raise TimeoutError(
                    f"DUT ({DUT_SERIAL}): Companion {comp_mac} not discovered within 45s"
                )

            # 4. Wait for 10 messages exchange & Pass button enabled on DUT
            print(
                f"Step 4: Monitoring RFCOMM data stream and Pass condition on DUT ({DUT_SERIAL})..."
            )
            pass_btn = wait_for_mesh_pass(
                DUT_SERIAL,
                COMPANION_SERIAL,
                comp_mac=comp_mac,
                client_activity=CLIENT_ACTIVITY,
                timeout=120,
            )
            screenshot("01_insecure_rfcomm_passed")

            # Also tap Pass on Companion if enabled
            try:
                comp_pass = wait_for_on(
                    COMPANION_SERIAL, content_desc="Pass", enabled=True, timeout=5
                )
                if comp_pass is not None:
                    print(f"Companion ({COMPANION_SERIAL}): Tapping Pass button...")
                    tap_on(COMPANION_SERIAL, comp_pass, sleep_after=1.0)
            except Exception:
                pass

            if pass_btn is None or pass_btn.attrib.get("enabled") != "true":
                raise TimeoutError(
                    f"DUT ({DUT_SERIAL}): Insecure RFCOMM test did not complete — Pass button was not enabled"
                )

            print(f"DUT ({DUT_SERIAL}): Tapping enabled Pass button...")
            tap_on(DUT_SERIAL, pass_btn, sleep_after=2.0)

            # Return to main activity & export
            adb_on(
                DUT_SERIAL, "shell", "am", "start", "-W", "-n", ACTIVITY, check=False
            )
            time.sleep(3.0)
            export_and_verify_mesh(TEST_NAME, CLIENT_ACTIVITY, DUT_SERIAL)
            print(
                ">>> SUCCESS: Bluetooth Classic Insecure Client/Server test passed and verified!"
            )

        finally:
            unpair_bonded_devices(DUT_SERIAL)
            unpair_bonded_devices(COMPANION_SERIAL)


if __name__ == "__main__":
    main()
