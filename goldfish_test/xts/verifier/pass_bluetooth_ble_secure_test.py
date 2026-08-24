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

"""Authentic CTS Verifier Bluetooth LE Secure Client/Server Test Automation.

Coordinated dual-device BLE GATT test over Netsim RF virtual medium with encryption:
1. Companion Node (emulator-5556) starts Secure GATT Server and advertises.
2. DUT Node (emulator-5554) runs BLE Secure Client subtests against Companion.
3. Authenticates and pairs both nodes via Secure Simple Pairing (SSP) / PIN prompts.
4. Verifies encrypted GATT operations and notifications.
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
    screenshot,
    set_screenshot_dir,
)
from mesh_cts_common import (
    COMPANION_SERIAL,
    DUT_SERIAL,
    adb_on,
    dismiss_initial_dialogs,
    export_and_verify_mesh,
    get_bluetooth_address,
    get_pass_button_coords,
    handle_node_dialogs_and_notifications,
    handle_pairing_dialogs,
    has_active_bluetooth_notification,
    is_dialog_focused,
    mesh_diagnostics,
    pair_mesh_nodes,
    scale_poll_interval,
    scale_timeout,
    setup_mesh_nodes,
    unpair_bonded_devices,
)

TEST_NAME = "Bluetooth LE Secure Client Test"
CLIENT_LIST_ACTIVITY = (
    "com.android.cts.verifier.bluetooth.BleSecureClientTestListActivity"
)
SERVER_LIST_ACTIVITY = (
    "com.android.cts.verifier.bluetooth.BleSecureServerTestListActivity"
)
CLIENT_START_ACTIVITY = (
    "com.android.cts.verifier.bluetooth.BleSecureClientStartActivity"
)
SERVER_START_ACTIVITY = (
    "com.android.cts.verifier.bluetooth.BleSecureServerStartActivity"
)


def run_subtest_secure_client_start(comp_mac: str):
    """Executes subtest 01: BLE Secure GATT Client Operations."""
    print("--- Executing Subtest 01: BLE Secure GATT Client Operations ---")
    adb_on(
        COMPANION_SERIAL,
        "shell",
        "am",
        "start",
        "-W",
        "-n",
        f"com.android.cts.verifier/{SERVER_START_ACTIVITY}",
        check=False,
    )
    time.sleep(scale_timeout(2.0))
    dismiss_initial_dialogs(COMPANION_SERIAL)

    adb_on(
        DUT_SERIAL,
        "shell",
        "am",
        "start",
        "-W",
        "-n",
        f"com.android.cts.verifier/{CLIENT_START_ACTIVITY}",
        check=False,
    )
    time.sleep(scale_timeout(2.0))
    dismiss_initial_dialogs(DUT_SERIAL)

    # 1. Handle pairing negotiation concurrently across both nodes
    print("Handling Secure Simple Pairing (SSP) / PIN dialogs...")
    handle_pairing_dialogs(DUT_SERIAL, COMPANION_SERIAL, timeout=scale_timeout(30.0))

    # 2. Continuously monitor for Pass button while GATT operations complete
    print("Monitoring BLE secure GATT operations and waiting for Pass...")
    timeout = scale_timeout(180.0)
    deadline = time.time() + timeout
    subtest_passed = False

    while time.time() < deadline:
        coords = get_pass_button_coords(DUT_SERIAL)
        if coords is not None:
            print(f"  DUT ({DUT_SERIAL}): Pass button enabled at {coords}, tapping...")
            adb_on(
                DUT_SERIAL,
                "shell",
                "input",
                "tap",
                str(coords[0]),
                str(coords[1]),
                check=False,
            )
            time.sleep(scale_poll_interval(1.5))
            res = adb_on(
                DUT_SERIAL,
                "shell",
                "content",
                "query",
                "--uri",
                "content://com.android.cts.verifier.testresultsprovider/results",
                check=False,
            )
            if CLIENT_START_ACTIVITY in res and "testresult=1" in res:
                print(f"  ✓ {CLIENT_START_ACTIVITY} confirmed passed (testresult=1)!")
                subtest_passed = True
                break

        res = adb_on(
            DUT_SERIAL,
            "shell",
            "content",
            "query",
            "--uri",
            "content://com.android.cts.verifier.testresultsprovider/results",
            check=False,
        )
        if (CLIENT_START_ACTIVITY in res and "testresult=1" in res) or (
            CLIENT_LIST_ACTIVITY in res and "testresult=1" in res
        ):
            print(
                f"  ✓ {CLIENT_START_ACTIVITY} confirmed passed in database (testresult=1)!"
            )
            subtest_passed = True
            break

        # Ensure Companion (server) dialogs are continuously handled without blocking DUT
        if is_dialog_focused(COMPANION_SERIAL) or has_active_bluetooth_notification(
            COMPANION_SERIAL
        ):
            handle_node_dialogs_and_notifications(COMPANION_SERIAL)

        time.sleep(scale_poll_interval(2.5))

    screenshot("01_ble_gatt_secure_passed")
    if not subtest_passed:
        raise TimeoutError(
            f"DUT ({DUT_SERIAL}): {CLIENT_START_ACTIVITY} did not complete after {timeout}s — Pass button was not enabled"
        )
    time.sleep(scale_timeout(2.0))


def main():
    setup_mesh_nodes(DUT_SERIAL, COMPANION_SERIAL)
    set_screenshot_dir("bluetooth_ble_secure_test")

    with mesh_diagnostics(TEST_NAME, [DUT_SERIAL, COMPANION_SERIAL]):
        try:
            print("Step 0: Establishing authenticated BLE bond between nodes...")
            pair_mesh_nodes(DUT_SERIAL, COMPANION_SERIAL)

            comp_mac = get_bluetooth_address(COMPANION_SERIAL)
            print(f"Companion BLE address: {comp_mac}")

            print(
                f"Step 1: Launching {SERVER_LIST_ACTIVITY} on Companion ({COMPANION_SERIAL})..."
            )
            adb_on(
                COMPANION_SERIAL,
                "shell",
                "am",
                "start",
                "-W",
                "-n",
                f"com.android.cts.verifier/{SERVER_LIST_ACTIVITY}",
                check=False,
            )
            time.sleep(scale_timeout(2.0))
            dismiss_initial_dialogs(COMPANION_SERIAL)

            print(f"Step 2: Launching {CLIENT_LIST_ACTIVITY} on DUT ({DUT_SERIAL})...")
            adb_on(
                DUT_SERIAL,
                "shell",
                "am",
                "start",
                "-W",
                "-n",
                f"com.android.cts.verifier/{CLIENT_LIST_ACTIVITY}",
                check=False,
            )
            time.sleep(scale_timeout(2.0))
            dismiss_initial_dialogs(DUT_SERIAL)

            run_subtest_secure_client_start(comp_mac)

            print(f"Verifying {CLIENT_START_ACTIVITY} on DUT ({DUT_SERIAL})...")
            export_and_verify_mesh(TEST_NAME, CLIENT_START_ACTIVITY, DUT_SERIAL)
            print(
                ">>> SUCCESS: Bluetooth LE Secure Client/Server test passed and verified!"
            )

        finally:
            unpair_bonded_devices(DUT_SERIAL)
            unpair_bonded_devices(COMPANION_SERIAL)


if __name__ == "__main__":
    main()
