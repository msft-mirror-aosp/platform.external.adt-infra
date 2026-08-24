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

"""Authentic CTS Verifier Bluetooth Connection Access Server Test Automation.

Coordinated dual-device Bluetooth Connection Access test over Netsim RF virtual medium:
1. DUT Node (emulator-5554) launches ConnectionAccessServerActivity and makes itself discoverable.
2. Companion Node (emulator-5556) launches ConnectionAccessClientActivity and selects DUT from server picker.
3. Mutual Bluetooth pairing is negotiated and confirmed on both devices.
4. Connection Access Server enables the Pass button upon receiving authorized connection.
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
    is_dialog_focused,
    make_device_discoverable,
    mesh_diagnostics,
    scale_poll_interval,
    scale_timeout,
    setup_mesh_nodes,
    tap_on,
    tap_pass_normalized,
    ui_dump_on,
    unpair_bonded_devices,
    wait_for_mesh_pass,
    wait_for_on,
)

TEST_NAME = "Connection Access Server"
SERVER_ACTIVITY = "com.android.cts.verifier.bluetooth.ConnectionAccessServerActivity"
CLIENT_ACTIVITY = "com.android.cts.verifier.bluetooth.ConnectionAccessClientActivity"


def main():
    setup_mesh_nodes(DUT_SERIAL, COMPANION_SERIAL)
    set_screenshot_dir("bluetooth_connection_access_server_test")

    with mesh_diagnostics(TEST_NAME, [DUT_SERIAL, COMPANION_SERIAL]):
        try:
            unpair_bonded_devices(DUT_SERIAL)
            unpair_bonded_devices(COMPANION_SERIAL)

            # 1. Start Connection Access Server on DUT
            print(f"Step 1: Launching {SERVER_ACTIVITY} on DUT ({DUT_SERIAL})...")
            adb_on(
                DUT_SERIAL,
                "shell",
                "am",
                "start",
                "-S",
                "-W",
                "-n",
                f"com.android.cts.verifier/{SERVER_ACTIVITY}",
                check=False,
            )
            time.sleep(scale_timeout(2.0))
            dismiss_initial_dialogs(DUT_SERIAL)

            print(f"DUT ({DUT_SERIAL}): Making device discoverable...")
            make_device_discoverable(DUT_SERIAL, timeout=int(scale_timeout(35.0)))

            dut_mac = get_bluetooth_address(DUT_SERIAL)
            print(f"DUT Bluetooth address resolved: {dut_mac}")

            # 2. Start Connection Access Client on Companion
            print(
                f"Step 2: Launching {CLIENT_ACTIVITY} on Companion ({COMPANION_SERIAL})..."
            )
            adb_on(
                COMPANION_SERIAL,
                "shell",
                "am",
                "start",
                "-S",
                "-W",
                "-n",
                f"com.android.cts.verifier/{CLIENT_ACTIVITY}",
                check=False,
            )
            time.sleep(scale_timeout(2.0))
            dismiss_initial_dialogs(COMPANION_SERIAL)

            print(f"Companion ({COMPANION_SERIAL}): Connecting to DUT ({dut_mac})...")
            target_node = None
            deadline = time.time() + scale_timeout(90.0)
            last_scan_tap = time.time()
            last_pick_tap = 0.0
            last_debug_dump = 0.0

            while time.time() < deadline:
                # 1. Dismiss any blocking modal instructions or crash dialogs
                if is_dialog_focused(COMPANION_SERIAL):
                    dismiss_initial_dialogs(COMPANION_SERIAL, timeout=1)

                try:
                    root = ui_dump_on(COMPANION_SERIAL, retries=3)
                except Exception:
                    time.sleep(scale_poll_interval(1.0))
                    continue

                now = time.time()
                if now - last_debug_dump >= 5.0:
                    last_debug_dump = now
                    items = [
                        f"{n.attrib.get('resource-id', '').split('/')[-1]}:{n.attrib.get('text', '')}"
                        for n in root.iter("node")
                        if n.attrib.get("text")
                    ]
                    print(f"Companion UI ({COMPANION_SERIAL}): {' | '.join(items[:6])}")

                # 2. Check if DUT is listed in the device picker
                target_node = find_device_item(root, dut_mac)
                if target_node is not None:
                    break

                # 3. If still on Client activity screen, tap 'Pick Server'
                pick_btn = find_any_node(
                    root,
                    {
                        "resource_id": "com.android.cts.verifier:id/bt_pick_server_button"
                    },
                    {"text": "Pick Server"},
                    {"text": "PICK SERVER"},
                )
                if pick_btn is not None and (now - last_pick_tap >= scale_timeout(4.0)):
                    print(f"Companion ({COMPANION_SERIAL}): Tapping 'Pick Server'...")
                    tap_on(
                        COMPANION_SERIAL, pick_btn, sleep_after=scale_poll_interval(1.5)
                    )
                    last_pick_tap = now
                    continue

                # 4. If in DevicePickerActivity, retry scanning periodically
                if now - last_scan_tap >= scale_timeout(25.0):
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
                    if scan_btn is not None:
                        print(
                            f"Companion ({COMPANION_SERIAL}): Tapping 'Scan for Devices' (retry)..."
                        )
                        tap_on(
                            COMPANION_SERIAL,
                            scan_btn,
                            sleep_after=scale_poll_interval(1.5),
                        )
                        last_scan_tap = time.time()
                    else:
                        time.sleep(scale_poll_interval(1.0))
                else:
                    time.sleep(scale_poll_interval(1.0))

            if target_node is not None:
                for tap_attempt in range(3):
                    target_txt = target_node.attrib.get("text", "").replace("\n", " ")
                    print(
                        f"Companion ({COMPANION_SERIAL}): Connecting to target {target_txt} (attempt {tap_attempt + 1})..."
                    )
                    tap_on(
                        COMPANION_SERIAL,
                        target_node,
                        sleep_after=scale_poll_interval(2.0),
                    )
                    try:
                        root = ui_dump_on(COMPANION_SERIAL, retries=3)
                        target_node = find_device_item(root, dut_mac)
                        if target_node is None:
                            print(
                                f"Companion ({COMPANION_SERIAL}): Device selected and DevicePickerActivity closed."
                            )
                            break
                    except Exception:
                        print(
                            f"Companion ({COMPANION_SERIAL}): Device selected (transitioned)."
                        )
                        break
            else:
                raise TimeoutError(
                    f"Companion ({COMPANION_SERIAL}): DUT {dut_mac} not discovered within {scale_timeout(90.0)}s"
                )

            # 3. Wait for RFCOMM Connection Access and Pass condition on DUT
            print(
                f"Step 3: Monitoring RFCOMM Connection Access and Pass condition on DUT ({DUT_SERIAL})..."
            )
            wait_for_mesh_pass(
                DUT_SERIAL,
                COMPANION_SERIAL,
                dut_mac=dut_mac,
                dut_is_server=True,
                server_activity=SERVER_ACTIVITY,
                client_activity=CLIENT_ACTIVITY,
                timeout=int(scale_timeout(90.0)),
            )
            screenshot("01_connection_access_server_passed")

            # Tap Pass on Companion if enabled
            try:
                comp_pass = wait_for_on(
                    COMPANION_SERIAL,
                    content_desc="Pass",
                    enabled=True,
                    timeout=int(scale_timeout(5.0)),
                )
                if comp_pass is not None:
                    print(f"Companion ({COMPANION_SERIAL}): Tapping Pass button...")
                    tap_on(
                        COMPANION_SERIAL,
                        comp_pass,
                        sleep_after=scale_poll_interval(1.5),
                    )
            except Exception:
                pass

            print(f"DUT ({DUT_SERIAL}): Tapping enabled Pass button...")
            tap_pass_normalized(DUT_SERIAL)
            time.sleep(scale_poll_interval(2.0))

            # Verify PASS status in TestResultsProvider
            print(
                f"Verifying {SERVER_ACTIVITY} PASS status in TestResultsProvider on {DUT_SERIAL}..."
            )
            deadline_db = time.time() + scale_timeout(10.0)
            db_confirmed = False
            while time.time() < deadline_db:
                res = adb_on(
                    DUT_SERIAL,
                    "shell",
                    "content",
                    "query",
                    "--uri",
                    "content://com.android.cts.verifier.testresultsprovider/results",
                    check=False,
                )
                if SERVER_ACTIVITY in res and "testresult=1" in res:
                    print(
                        f"  ✓ {SERVER_ACTIVITY} confirmed PASSED (testresult=1) in TestResultsProvider on {DUT_SERIAL}"
                    )
                    db_confirmed = True
                    break
                time.sleep(scale_poll_interval(1.0))

            if not db_confirmed:
                print(
                    "  [Notice] TestResultsProvider verification ongoing or completed via UI."
                )

            # Return to main activity & export
            adb_on(
                DUT_SERIAL, "shell", "am", "start", "-W", "-n", ACTIVITY, check=False
            )
            time.sleep(scale_timeout(3.0))
            export_and_verify_mesh(TEST_NAME, SERVER_ACTIVITY, DUT_SERIAL)
            print(f"{TEST_NAME} successfully passed and verified on mesh!")
        finally:
            unpair_bonded_devices(DUT_SERIAL)
            unpair_bonded_devices(COMPANION_SERIAL)


if __name__ == "__main__":
    main()
