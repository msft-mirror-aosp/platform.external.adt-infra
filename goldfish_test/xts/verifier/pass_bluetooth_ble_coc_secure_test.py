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

"""Authentic CTS Verifier Bluetooth LE CoC Secure Client/Server Test Automation.

Coordinated dual-device BLE L2CAP Secure Channel-Oriented Connection test:
1. Companion Node (emulator-5556) opens authenticated L2CAP CoC channel & advertises.
2. DUT Node (emulator-5554) connects via encrypted L2CAP CoC socket.
3. Authenticates & pairs both nodes via Secure Simple Pairing (SSP) / PIN prompts.
4. Bidirectional encrypted data stream verified over Netsim RF medium.
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
    get_bluetooth_address,
    get_pass_button_coords,
    handle_node_dialogs_and_notifications,
    handle_pairing_dialogs,
    mesh_diagnostics,
    scale_poll_interval,
    scale_timeout,
    setup_mesh_nodes,
    tap_pass_button_if_enabled,
    pair_mesh_nodes,
    unpair_bonded_devices,
)

TEST_NAME = "Bluetooth LE CoC Secure Client Test"
CLIENT_LIST_ACTIVITY = (
    "com.android.cts.verifier.bluetooth.BleCocSecureClientTestListActivity"
)
SERVER_LIST_ACTIVITY = (
    "com.android.cts.verifier.bluetooth.BleCocSecureServerTestListActivity"
)
CLIENT_START_ACTIVITY = (
    "com.android.cts.verifier.bluetooth.BleCocSecureClientStartActivity"
)
SERVER_START_ACTIVITY = (
    "com.android.cts.verifier.bluetooth.BleCocSecureServerStartActivity"
)


def run_subtest_coc_secure_start(comp_mac: str):
    """Executes subtest 01: BLE CoC Secure Client Data Transfer."""
    print("--- Executing Subtest 01: BLE CoC Secure Client Data Transfer ---")
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
    handle_pairing_dialogs(
        DUT_SERIAL, COMPANION_SERIAL, timeout=int(scale_timeout(30.0))
    )

    # 2. Continuously monitor for Pass button on DUT while secure CoC data transfer completes
    print("Monitoring BLE CoC secure data transfer and waiting for Pass...")
    timeout = scale_timeout(60.0)
    deadline = time.time() + timeout
    start_time = time.time()
    last_restart = start_time

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
            if (CLIENT_START_ACTIVITY in res and "testresult=1" in res) or (
                CLIENT_LIST_ACTIVITY in res and "testresult=1" in res
            ):
                print(f"  ✓ {CLIENT_START_ACTIVITY} confirmed passed (testresult=1)!")
                subtest_passed = True
                break
        # Also handle any late pairing or notification prompts on either node
        handle_node_dialogs_and_notifications(COMPANION_SERIAL)
        handle_node_dialogs_and_notifications(DUT_SERIAL)
        tap_pass_button_if_enabled(COMPANION_SERIAL)

        now = time.time()
        if now - last_restart >= scale_timeout(20.0):
            print("  Re-triggering BLE CoC Secure Client to reconnect...")
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
            time.sleep(scale_timeout(1.5))
            dismiss_initial_dialogs(DUT_SERIAL)
            last_restart = time.time()

        time.sleep(scale_poll_interval(2.0))

    screenshot("01_ble_coc_secure_passed")
    if not subtest_passed:
        raise TimeoutError(
            f"DUT ({DUT_SERIAL}): {CLIENT_START_ACTIVITY} did not complete after {timeout}s — Pass button was not enabled"
        )
    time.sleep(scale_timeout(2.0))


def main():
    setup_mesh_nodes(DUT_SERIAL, COMPANION_SERIAL)
    set_screenshot_dir("bluetooth_ble_coc_secure_test")

    with mesh_diagnostics(TEST_NAME, [DUT_SERIAL, COMPANION_SERIAL]):
        try:
            comp_mac = get_bluetooth_address(COMPANION_SERIAL)
            print(f"Companion BLE address: {comp_mac}")

            print("Pre-pairing mesh nodes for authenticated BLE CoC...")
            pair_mesh_nodes(DUT_SERIAL, COMPANION_SERIAL)

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

            run_subtest_coc_secure_start(comp_mac)

            print(f"Step 3: Launching {CLIENT_LIST_ACTIVITY} on DUT ({DUT_SERIAL})...")
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

            print("Monitoring overall BLE CoC Secure Client Pass condition...")
            list_timeout = scale_timeout(30.0)
            deadline = time.time() + list_timeout
            list_passed = False
            while time.time() < deadline:
                coords = get_pass_button_coords(DUT_SERIAL)
                if coords is not None:
                    print(
                        f"  DUT ({DUT_SERIAL}): Pass button enabled at {coords}, tapping..."
                    )
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
                    if CLIENT_LIST_ACTIVITY in res and "testresult=1" in res:
                        print(
                            f"  ✓ {CLIENT_LIST_ACTIVITY} confirmed passed (testresult=1)!"
                        )
                        list_passed = True
                        break
                time.sleep(scale_poll_interval(2.5))

            screenshot("02_ble_coc_secure_list_passed")
            if not list_passed:
                raise TimeoutError(
                    f"DUT ({DUT_SERIAL}): {CLIENT_LIST_ACTIVITY} Pass button was not enabled after {list_timeout}s"
                )
            time.sleep(scale_timeout(2.0))

            adb_on(
                DUT_SERIAL, "shell", "am", "start", "-W", "-n", ACTIVITY, check=False
            )
            time.sleep(scale_timeout(3.0))
            export_and_verify_mesh(TEST_NAME, CLIENT_LIST_ACTIVITY, DUT_SERIAL)
            print(
                ">>> SUCCESS: Bluetooth LE CoC Secure Client/Server test passed and verified!"
            )

        finally:
            unpair_bonded_devices(DUT_SERIAL)
            unpair_bonded_devices(COMPANION_SERIAL)


if __name__ == "__main__":
    main()
