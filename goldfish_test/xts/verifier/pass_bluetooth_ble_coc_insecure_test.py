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

"""Authentic CTS Verifier Bluetooth LE CoC Insecure Client/Server Test Automation.

Coordinated dual-device BLE L2CAP Channel-Oriented Connection test:
1. Companion Node (emulator-5556) opens unauthenticated L2CAP CoC channel & advertises.
2. DUT Node (emulator-5554) connects via L2CAP CoC socket.
3. Bidirectional data stream verified over Netsim RF medium.
4. Asserts Pass button enabled, taps Pass, and exports verification report.
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
    NORM_PASS_BUTTON,
    adb_on,
    dismiss_initial_dialogs,
    export_and_verify_mesh,
    get_bluetooth_address,
    get_pass_button_coords,
    mesh_diagnostics,
    scale_poll_interval,
    scale_timeout,
    setup_mesh_nodes,
    tap_normalized,
    tap_on,
    tap_pass_button_if_enabled,
    tap_pass_normalized,
    tap_pass_on,
    ui_dump_on,
    unpair_bonded_devices,
    wait_for_on,
)

TEST_NAME = "Bluetooth LE CoC Insecure Client Test"
CLIENT_LIST_ACTIVITY = (
    "com.android.cts.verifier.bluetooth.BleCocInsecureClientTestListActivity"
)
SERVER_LIST_ACTIVITY = (
    "com.android.cts.verifier.bluetooth.BleCocInsecureServerTestListActivity"
)
CLIENT_START_ACTIVITY = (
    "com.android.cts.verifier.bluetooth.BleCocInsecureClientStartActivity"
)
SERVER_START_ACTIVITY = (
    "com.android.cts.verifier.bluetooth.BleCocInsecureServerStartActivity"
)


def run_subtest_coc_insecure_start(comp_mac: str):
    """Executes subtest 01: BLE CoC Insecure Client Data Transfer."""
    print("--- Executing Subtest 01: BLE CoC Insecure Client Data Transfer ---")
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

    # 1. Continuously monitor for Pass button on DUT using view hierarchy coordinates
    print("Monitoring BLE CoC data transfer and waiting for Pass...")
    timeout = scale_timeout(75.0)
    deadline = time.time() + timeout
    subtest_passed = False
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
        tap_pass_button_if_enabled(COMPANION_SERIAL)

        # Periodically restart activities to restart advertising / scanning if stuck
        now = time.time()
        if now - last_restart >= scale_timeout(20.0):
            print("  Re-triggering BLE CoC Insecure advertise and scan...")
            adb_on(
                COMPANION_SERIAL,
                "shell",
                "am",
                "start",
                "-S",
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
                "-S",
                "-W",
                "-n",
                f"com.android.cts.verifier/{CLIENT_START_ACTIVITY}",
                check=False,
            )
            time.sleep(scale_timeout(2.0))
            dismiss_initial_dialogs(DUT_SERIAL)
            last_restart = time.time()

        time.sleep(scale_poll_interval(1.5))

    screenshot("01_ble_coc_insecure_client_passed")
    if not subtest_passed:
        raise TimeoutError(
            f"DUT ({DUT_SERIAL}): {CLIENT_START_ACTIVITY} did not complete after {timeout}s — Pass button was not enabled"
        )
    time.sleep(scale_timeout(2.0))


def main():
    setup_mesh_nodes(DUT_SERIAL, COMPANION_SERIAL)
    set_screenshot_dir("bluetooth_ble_coc_insecure_test")

    with mesh_diagnostics(TEST_NAME, [DUT_SERIAL, COMPANION_SERIAL]):
        try:
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

            run_subtest_coc_insecure_start(comp_mac)

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

            print("Monitoring overall BLE CoC Insecure Client Pass condition...")
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

            screenshot("02_ble_coc_insecure_list_passed")
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
                ">>> SUCCESS: Bluetooth LE CoC Insecure Client/Server test passed and verified!"
            )

        finally:
            unpair_bonded_devices(DUT_SERIAL)
            unpair_bonded_devices(COMPANION_SERIAL)


if __name__ == "__main__":
    main()
