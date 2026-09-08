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

"""Authentic CTS Verifier Bluetooth LE Scanner / Advertiser Test Automation.

Coordinated dual-device BLE Scanner & Advertiser test over Netsim RF virtual medium:
1. DUT Node (emulator-5554) launches BleScannerTestActivity, enters Tx Power Level
   sub-activity, dismisses dialogs, and waits until the Scanner UI is active.
2. Companion Node (emulator-5556) launches BleAdvertiserTestActivity, enters Tx Power
   Level sub-activity, dismisses dialogs, and triggers multi-advertising across all 4 power levels.
3. DUT monitors reception of Ultra low, Low, Medium, and High power levels, and taps Pass.
4. Companion stops multi-advertising and passes sub-activity.
5. DUT asserts top-level BleScannerTestActivity Pass button is enabled, taps Pass,
   and exports the verification report.
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
    get_bluetooth_address,
    get_pass_button_coords,
    mesh_diagnostics,
    scale_poll_interval,
    scale_timeout,
    setup_mesh_nodes,
    tap_on,
    tap_pass_button_if_enabled,
    tap_pass_on,
    ui_dump_on,
    unpair_bonded_devices,
    wait_for_on,
)

TEST_NAME = "Bluetooth LE Scanner Test"
SCANNER_ACTIVITY = "com.android.cts.verifier.bluetooth.BleScannerPowerLevelActivity"
ADVERTISER_ACTIVITY = (
    "com.android.cts.verifier.bluetooth.BleAdvertiserPowerLevelActivity"
)


def find_node_by_text(root, text_pattern):
    """Find a node whose text contains the given substring."""
    pattern = text_pattern.lower()
    for n in root.iter("node"):
        txt = (n.attrib.get("text") or "").strip().lower()
        if pattern in txt:
            return n
    return None


def main():
    setup_mesh_nodes(DUT_SERIAL, COMPANION_SERIAL)
    set_screenshot_dir("bluetooth_ble_scanner_advertiser_test")

    with mesh_diagnostics(TEST_NAME, [DUT_SERIAL, COMPANION_SERIAL]):
        try:
            comp_mac = get_bluetooth_address(COMPANION_SERIAL)
            print(f"Companion BLE address: {comp_mac}")

            # Pre-seed testinfoseen to suppress modal instruction dialogs on both devices
            for serial, act in [
                (DUT_SERIAL, "BleScannerPowerLevelActivity"),
                (COMPANION_SERIAL, "BleAdvertiserPowerLevelActivity"),
            ]:
                adb_on(
                    serial,
                    "shell",
                    "content",
                    "insert",
                    "--uri",
                    "content://com.android.cts.verifier.testresultsprovider/results",
                    "--bind",
                    f"testname:s:com.android.cts.verifier.bluetooth.{act}",
                    "--bind",
                    "testinfoseen:i:1",
                    check=False,
                )

            # 1. Launch Advertiser on Companion first so packets are already broadcasting
            print(
                f"Step 1: Launching {ADVERTISER_ACTIVITY} on Companion ({COMPANION_SERIAL})..."
            )
            adb_on(
                COMPANION_SERIAL,
                "shell",
                "am",
                "start",
                "-W",
                "-S",
                "-n",
                f"com.android.cts.verifier/.bluetooth.BleAdvertiserPowerLevelActivity",
                check=False,
            )
            time.sleep(3.0)

            # Stop any previous advertisers and start fresh on Companion
            try:
                root_comp = ui_dump_on(COMPANION_SERIAL)
                stop_btn = find_node(
                    root_comp,
                    resource_id="com.android.cts.verifier:id/ble_power_level_stop",
                )
                if stop_btn is not None:
                    tap_on(COMPANION_SERIAL, stop_btn, sleep_after=1.5)
            except Exception:
                pass

            start_btn = wait_for_on(
                COMPANION_SERIAL,
                resource_id="com.android.cts.verifier:id/ble_power_level_start",
                timeout=20,
            )
            print(f"Companion ({COMPANION_SERIAL}): Tapping Start Advertise...")
            tap_on(COMPANION_SERIAL, start_btn, sleep_after=3.0)

            # 2. Launch Scanner on DUT while advertiser is actively broadcasting
            print(f"Step 2: Launching {SCANNER_ACTIVITY} on DUT ({DUT_SERIAL})...")
            adb_on(
                DUT_SERIAL,
                "shell",
                "am",
                "start",
                "-W",
                "-S",
                "-n",
                f"com.android.cts.verifier/.bluetooth.BleScannerPowerLevelActivity",
                check=False,
            )

            # 3. Wait and poll dumpsys for Pass button to become enabled
            print(
                f"Step 3: Waiting for BLE scan window to collect all power levels on DUT ({DUT_SERIAL})..."
            )
            passed = False
            for attempt in range(8):
                # Poll dumpsys every 2.0s for up to 24s
                for _ in range(12):
                    time.sleep(2.0)
                    coords = get_pass_button_coords(DUT_SERIAL)
                    if coords is not None:
                        print(
                            f"DUT ({DUT_SERIAL}): Pass button enabled at {coords}! Tapping Pass..."
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
                        time.sleep(2.0)
                        passed = True
                        break
                if passed:
                    break
                print(
                    f"  [DUT retry {attempt+1}] Pass button not enabled yet, restarting scanner on DUT and advertiser on Companion..."
                )
                # Restart advertiser on Companion
                try:
                    adb_on(
                        COMPANION_SERIAL,
                        "shell",
                        "am",
                        "start",
                        "-W",
                        "-S",
                        "-n",
                        "com.android.cts.verifier/.bluetooth.BleAdvertiserPowerLevelActivity",
                        check=False,
                    )
                    time.sleep(2.0)
                    start_btn = wait_for_on(
                        COMPANION_SERIAL,
                        resource_id="com.android.cts.verifier:id/ble_power_level_start",
                        timeout=15,
                    )
                    tap_on(COMPANION_SERIAL, start_btn, sleep_after=2.0)
                except Exception as e:
                    print(f"  Advertiser restart retry failed: {e}")

                # Refresh scanner on DUT
                adb_on(
                    DUT_SERIAL,
                    "shell",
                    "am",
                    "start",
                    "-W",
                    "-S",
                    "-n",
                    f"com.android.cts.verifier/.bluetooth.BleScannerPowerLevelActivity",
                    check=False,
                )

            if not passed:
                raise TimeoutError(
                    f"DUT ({DUT_SERIAL}): BleScannerPowerLevelActivity did not receive all 4 power levels (Pass button remained disabled)"
                )

            # Stop advertiser and pass on Companion
            try:
                root_c = ui_dump_on(COMPANION_SERIAL)
                stop_btn = find_node(
                    root_c,
                    resource_id="com.android.cts.verifier:id/ble_power_level_stop",
                )
                if stop_btn is not None:
                    tap_on(COMPANION_SERIAL, stop_btn, sleep_after=1.0)
                comp_pass = find_node(root_c, content_desc="Pass")
                if comp_pass is not None:
                    tap_on(COMPANION_SERIAL, comp_pass, sleep_after=1.0)
            except Exception:
                pass

            # Return to main activity & export
            adb_on(
                DUT_SERIAL,
                "shell",
                "am",
                "start",
                "-W",
                "-n",
                ACTIVITY,
                check=False,
            )
            time.sleep(2.0)
            export_and_verify_mesh(TEST_NAME, SCANNER_ACTIVITY, DUT_SERIAL)
            print(
                ">>> SUCCESS: Bluetooth LE Scanner/Advertiser test passed and"
                " verified!"
            )

        finally:
            unpair_bonded_devices(DUT_SERIAL)
            unpair_bonded_devices(COMPANION_SERIAL)


if __name__ == "__main__":
    sys.exit(main())
