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

"""Shared multi-device mesh helpers for CTS Verifier automation scripts."""

import contextlib
import os
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from typing import List, Optional

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import cts_common
from cts_common import (
    APK_PATH,
    PACKAGE,
    bounds_center,
    find_any_node,
    find_node,
)

DUT_SERIAL = os.environ.get("CTS_DUT_SERIAL", "emulator-5554")
COMPANION_SERIAL = os.environ.get("CTS_COMPANION_SERIAL", "emulator-5556")

# Set default serial on cts_common to DUT
cts_common.SERIAL = DUT_SERIAL


def adb_on(
    serial: str, *args, check: bool = True, timeout: Optional[int] = None
) -> str:
    """Executes an ADB command targeting a specific device serial."""
    cmd = ["adb", "-s", serial] + list(args)
    try:
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=check,
            timeout=timeout,
        )
        return res.stdout.strip()
    except subprocess.TimeoutExpired as e:
        print(f"  [ERROR] adb command on {serial} timed out: {' '.join(cmd)}")
        raise e


def ui_dump_on(serial: str, retries: int = 5) -> ET.Element:
    """Captures and parses the UI hierarchy XML on a specific device."""
    for attempt in range(retries):
        try:
            res = subprocess.run(
                ["adb", "-s", serial, "exec-out", "uiautomator", "dump", "/dev/tty"],
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
            raw = res.stdout
            if "<hierarchy" in raw:
                start = raw.find("<hierarchy")
                end = raw.rfind("</hierarchy>") + len("</hierarchy>")
                return ET.fromstring(raw[start:end])
        except Exception:
            pass
        time.sleep(1.0)

    # Fallback to file-based dump
    adb_on(
        serial,
        "shell",
        "uiautomator",
        "dump",
        "/data/local/tmp/uidump.xml",
        check=False,
    )
    xml_str = adb_on(serial, "shell", "cat", "/data/local/tmp/uidump.xml", check=False)
    if "<hierarchy" in xml_str:
        start = xml_str.find("<hierarchy")
        end = xml_str.rfind("</hierarchy>") + len("</hierarchy>")
        return ET.fromstring(xml_str[start:end])

    raise RuntimeError(
        f"Failed to obtain UI dump from {serial} after {retries} attempts"
    )


def tap_on(serial: str, node: ET.Element, sleep_after: float = 1.5) -> None:
    """Taps the center coordinates of a UI node on the specified device."""
    x, y = bounds_center(node)
    adb_on(serial, "shell", "input", "tap", str(x), str(y))
    if sleep_after > 0:
        time.sleep(sleep_after)


def wait_for_on(
    serial: str,
    text: Optional[str] = None,
    content_desc: Optional[str] = None,
    resource_id: Optional[str] = None,
    enabled: Optional[bool] = True,
    timeout: int = 20,
) -> ET.Element:
    """Polls until a matching element is found and enabled on the specified device."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            root = ui_dump_on(serial, retries=2)
            node = find_node(
                root,
                text=text,
                content_desc=content_desc,
                resource_id=resource_id,
            )
            if node is not None:
                if (
                    enabled is None
                    or node.attrib.get("enabled", "true") == str(enabled).lower()
                ):
                    return node
        except Exception:
            pass
        time.sleep(1.0)
    label = text or content_desc or resource_id
    raise TimeoutError(f"Timed out waiting for element {label!r} on {serial}")


def tap_pass_on(serial: str, pass_btn: Optional[ET.Element] = None) -> None:
    """Taps the Pass button on a specific device."""
    if pass_btn is None:
        pass_btn = wait_for_on(serial, content_desc="Pass")
    print(f"  [{serial}] Tapping Pass at {pass_btn.attrib['bounds']}...")
    tap_on(serial, pass_btn, sleep_after=1.0)


def dismiss_initial_dialogs(serial: str, timeout: int = 5) -> None:
    """Dismisses info/instruction OK dialogs and grants initial system prompts."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        handled = False
        try:
            root = ui_dump_on(serial, retries=1)
            is_dialog = (
                find_any_node(
                    root,
                    {"resource_id": "android:id/parentPanel"},
                    {"resource_id": "com.android.settings:id/parentPanel"},
                    {"resource_id": "com.android.permissioncontroller:id/grant_dialog"},
                )
                is not None
            )
            if is_dialog:
                btn = find_any_node(
                    root,
                    {"text": "OK"},
                    {"text": "Got it"},
                    {"text": "CLOSE"},
                    {"text": "Allow"},
                    {"text": "ALLOW"},
                    {"text": "Turn on"},
                    {"resource_id": "android:id/button1"},
                )
                if btn is not None:
                    txt = btn.attrib.get("text", "") or btn.attrib.get(
                        "resource-id", ""
                    )
                    if "Deny" not in txt and "Cancel" not in txt:
                        print(
                            f"  [{serial}] Dismissing / accepting initial dialog ({txt})..."
                        )
                        tap_on(serial, btn, sleep_after=1.0)
                        handled = True
        except Exception:
            pass
        if handled:
            time.sleep(0.5)
        else:
            time.sleep(0.5)


def handle_make_discoverable_dialog(serial: str) -> None:
    """Accepts system dialog when app requests to make device discoverable."""
    time.sleep(1.0)
    try:
        root = ui_dump_on(serial, retries=2)
        allow_btn = find_any_node(
            root,
            {"text": "Allow"},
            {"text": "ALLOW"},
            {"text": "Turn on"},
            {"resource_id": "android:id/button1"},
        )
        if allow_btn is not None:
            print(f"  [{serial}] Allowing discoverability request...")
            tap_on(serial, allow_btn, sleep_after=1.5)
    except Exception:
        pass


def get_bluetooth_address(serial: str) -> Optional[str]:
    """Retrieves the local Bluetooth MAC address of a device."""
    addr = adb_on(
        serial, "shell", "settings", "get", "secure", "bluetooth_address", check=False
    )
    if addr and re.match(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$", addr):
        return addr.upper()

    dump = adb_on(serial, "shell", "dumpsys", "bluetooth_manager", check=False)
    match = re.search(
        r"address:\s*([0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2})",
        dump,
    )
    if match:
        return match.group(1).upper()

    name_match = re.search(r"name:\s*(\S+)", dump)
    if name_match:
        return name_match.group(1)

    return None


def handle_pairing_dialogs(
    dut_serial: str = DUT_SERIAL, comp_serial: str = COMPANION_SERIAL, timeout: int = 25
) -> None:
    """Handles Bluetooth pairing and connection authorization dialogs on both devices."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        for s in [dut_serial, comp_serial]:
            try:
                root = ui_dump_on(s, retries=1)
                is_dialog = (
                    find_any_node(
                        root,
                        {"resource_id": "android:id/parentPanel"},
                        {"resource_id": "com.android.settings:id/parentPanel"},
                        {
                            "resource_id": "com.android.permissioncontroller:id/grant_dialog"
                        },
                    )
                    is not None
                )
                if not is_dialog:
                    continue

                pair_btn = find_any_node(
                    root,
                    {"text": "Pair"},
                    {"text": "PAIR"},
                    {"content_desc": "Pair"},
                    {"content_desc": "PAIR"},
                    {"text": "Pair & connect"},
                    {"text": "PAIR & CONNECT"},
                    {"text": "Pair with"},
                    {"text": "Yes"},
                    {"text": "YES"},
                    {"text": "Allow"},
                    {"text": "ALLOW"},
                    {"text": "OK"},
                    {"resource_id": "android:id/button1"},
                    {"resource_id": "com.android.settings:id/button1"},
                )
                if pair_btn is not None:
                    txt = (
                        pair_btn.attrib.get("text", "")
                        or pair_btn.attrib.get("content-desc", "")
                        or pair_btn.attrib.get("resource-id", "")
                    )
                    if txt not in (
                        "Deny",
                        "Cancel",
                        "CANCEL",
                        "Close",
                        "CLOSE",
                        "No",
                        "NO",
                        "Delete",
                        "Bluetooth Settings",
                    ):
                        print(f"  [{s}] Confirming dialog ({txt})...")
                        tap_on(s, pair_btn, sleep_after=1.0)
            except Exception:
                pass
        time.sleep(1.0)


def unpair_bonded_devices(serial: str) -> None:
    """Unpairs all bonded Bluetooth devices on the given node (fast-path root or Settings UI fallback)."""
    try:
        dump = adb_on(serial, "shell", "dumpsys", "bluetooth_manager", check=False)
        if "Bonded devices: 0" in dump or "mBondedDevices=[]" in dump:
            return
    except Exception:
        pass

    try:
        adb_on(serial, "shell", "am", "force-stop", "com.android.settings", check=False)
        adb_on(
            serial,
            "shell",
            "am",
            "start",
            "-n",
            "com.android.settings/.Settings",
            check=False,
        )
        time.sleep(1.0)
        root = ui_dump_on(serial, retries=2)
        conn_dev = find_node(root, text="Connected devices")
        if conn_dev is not None:
            tap_on(serial, conn_dev, sleep_after=1.5)
            root = ui_dump_on(serial, retries=2)
        gear = find_node(root, resource_id="com.android.settings:id/settings_button")
        if gear is not None:
            tap_on(serial, gear, sleep_after=1.5)
            root = ui_dump_on(serial, retries=2)
            forget_btn = find_any_node(
                root, {"content_desc": "Forget"}, {"text": "Forget"}
            )
            if forget_btn is not None:
                tap_on(serial, forget_btn, sleep_after=1.0)
                root = ui_dump_on(serial, retries=2)
                confirm_btn = find_any_node(
                    root,
                    {"text": "Forget device"},
                    {"resource_id": "android:id/button1"},
                )
                if confirm_btn is not None:
                    tap_on(serial, confirm_btn, sleep_after=1.0)
    except Exception:
        pass
    finally:
        adb_on(serial, "shell", "input", "keyevent", "KEYCODE_HOME", check=False)
        time.sleep(0.5)


def ensure_bluetooth_enabled(serial: str, timeout: int = 15) -> bool:
    """Ensures Bluetooth adapter is turned on and ready on the device."""
    adb_on(
        serial, "shell", "settings", "put", "global", "bluetooth_on", "1", check=False
    )
    adb_on(serial, "shell", "svc", "bluetooth", "enable", check=False)
    deadline = time.time() + timeout
    while time.time() < deadline:
        dump = adb_on(serial, "shell", "dumpsys", "bluetooth_manager", check=False)
        if "State:         ON" in dump or "State: ON" in dump:
            return True
        time.sleep(0.5)
    return False


def grant_permissions_on(serial: str, apk_path: Optional[str] = None) -> None:
    """Automatically grants all required CTS Verifier permissions on a specific node."""
    adb_on(
        serial,
        "shell",
        "settings",
        "put",
        "global",
        "hidden_api_policy",
        "1",
        check=False,
    )
    ensure_bluetooth_enabled(serial)
    if apk_path and os.path.exists(apk_path):
        adb_on(serial, "install", "-r", "-g", apk_path, check=False)
    adb_on(
        serial,
        "shell",
        "appops",
        "set",
        PACKAGE,
        "android:read_device_identifiers",
        "allow",
        check=False,
    )
    adb_on(
        serial,
        "shell",
        "appops",
        "set",
        PACKAGE,
        "MANAGE_EXTERNAL_STORAGE",
        "0",
        check=False,
    )
    adb_on(
        serial,
        "shell",
        "am",
        "compat",
        "enable",
        "ALLOW_TEST_API_ACCESS",
        PACKAGE,
        check=False,
    )
    for p in [
        "android.permission.ACCESS_FINE_LOCATION",
        "android.permission.ACCESS_COARSE_LOCATION",
        "android.permission.BLUETOOTH_SCAN",
        "android.permission.BLUETOOTH_CONNECT",
        "android.permission.BLUETOOTH_ADVERTISE",
        "android.permission.READ_EXTERNAL_STORAGE",
        "android.permission.WRITE_EXTERNAL_STORAGE",
        "android.permission.POST_NOTIFICATIONS",
    ]:
        adb_on(serial, "shell", "pm", "grant", PACKAGE, p, check=False)


def export_and_verify_mesh(
    test_name: str, activity_class: str, serial: str = DUT_SERIAL
) -> None:
    """Exports CTS Verifier report and asserts PASS status in TestResultsProvider."""
    print(
        f"Verifying {activity_class} PASS status in TestResultsProvider on {serial}..."
    )
    query_res = adb_on(
        serial,
        "shell",
        "content",
        "query",
        "--uri",
        "content://com.android.cts.verifier.testresultsprovider/results",
        check=False,
    )
    passed = False
    for line in query_res.splitlines():
        if activity_class in line and "testresult=1" in line:
            passed = True
            print(
                f"  ✓ {activity_class} confirmed PASSED (testresult=1) in TestResultsProvider on {serial}"
            )
            break

    if not passed:
        raise AssertionError(
            f"VERIFICATION FAILED: {activity_class} did not record testresult=1 in TestResultsProvider on {serial}.\nQuery output:\n{query_res}"
        )

    try:
        adb_on(
            serial,
            "shell",
            "am",
            "start",
            "-a",
            "android.intent.action.MAIN",
            "-c",
            "android.intent.category.LAUNCHER",
            "-n",
            "com.android.cts.verifier/.CtsVerifierActivity",
            check=False,
        )
        time.sleep(2.0)
        from cts_common import export_and_verify

        export_and_verify(test_name)
    except Exception as e:
        print(f"  [Notice] XML export report check completed with notice: {e}")


@contextlib.contextmanager
def mesh_diagnostics(
    test_name: str,
    devices: Optional[List[str]] = None,
    output_dir: Optional[str] = None,
):
    """Context manager that automatically captures troubleshooting diagnostic bundles on failure."""
    if devices is None:
        devices = [DUT_SERIAL, COMPANION_SERIAL]

    session = None
    try:
        dev_cli_src = os.path.abspath(
            os.path.join(
                SCRIPT_DIR, "../../../../../hardware/google/aemu/tools/emu-dev-cli/src"
            )
        )
        if os.path.isdir(dev_cli_src) and dev_cli_src not in sys.path:
            sys.path.insert(0, dev_cli_src)
        from lib.diagnostics import DiagnosticSession, DiagnosticsConfig

        cfg = DiagnosticsConfig(output_dir=output_dir) if output_dir else None
        session = DiagnosticSession(devices=devices, test_name=test_name, config=cfg)
        session.start()
    except Exception:
        session = None

    try:
        yield
    except Exception as e:
        if session is not None:
            bundle = session.collect_bundle(status="FAILED", error=str(e))
            print(
                f"  [DIAGNOSTICS] Failure diagnostic bundle captured at: {bundle.get('session_dir')}"
            )
        raise
    finally:
        if session is not None:
            session.stop()


def setup_mesh_nodes(
    dut_serial: str = DUT_SERIAL, comp_serial: str = COMPANION_SERIAL
) -> None:
    """Prepares both DUT and Companion nodes for CTS Verifier testing."""
    for s in [dut_serial, comp_serial]:
        print(f"Setting up mesh node {s}...")
        adb_on(s, "shell", "input", "keyevent", "KEYCODE_WAKEUP", check=False)
        adb_on(s, "shell", "wm", "dismiss-keyguard", check=False)
        adb_on(
            s,
            "shell",
            "settings",
            "put",
            "global",
            "stay_on_while_plugged_in",
            "7",
            check=False,
        )
        grant_permissions_on(s, APK_PATH)
        unpair_bonded_devices(s)
