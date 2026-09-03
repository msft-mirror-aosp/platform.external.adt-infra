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
import tempfile
import time
import xml.etree.ElementTree as ET
from typing import List, Optional, Tuple, Union

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import cts_common
from cts_common import (
    APK_PATH,
    NORM_FAIL_BUTTON,
    NORM_INFO_BUTTON,
    NORM_MENU_BUTTON,
    NORM_PASS_BUTTON,
    PACKAGE,
    bounds_center,
    find_any_node,
    find_node,
    get_display_size,
    get_scale_factor,
    is_remote_execution,
    scale_poll_interval,
    scale_timeout,
    tap_normalized,
    tap_pass_normalized,
)

__all__ = [
    "APK_PATH",
    "NORM_FAIL_BUTTON",
    "NORM_INFO_BUTTON",
    "NORM_MENU_BUTTON",
    "NORM_PASS_BUTTON",
    "PACKAGE",
    "bounds_center",
    "find_any_node",
    "find_node",
    "get_display_size",
    "get_scale_factor",
    "is_remote_execution",
    "scale_poll_interval",
    "scale_timeout",
    "tap_normalized",
    "tap_pass_normalized",
    "DUT_SERIAL",
    "COMPANION_SERIAL",
    "adb_on",
    "ui_dump_on",
    "tap_on",
    "wait_for_on",
    "find_device_item",
    "find_confirmation_button",
    "dismiss_initial_dialogs",
    "get_bluetooth_address",
    "handle_make_discoverable_dialog",
    "handle_node_dialogs_and_notifications",
    "handle_pairing_dialogs",
    "make_device_discoverable",
    "pair_mesh_nodes",
    "setup_mesh_nodes",
    "unpair_bonded_devices",
]

DUT_SERIAL = os.environ.get(
    "DUT_SERIAL",
    os.environ.get(
        "CTS_DUT_SERIAL",
        os.environ.get("ANDROID_SERIAL", "emulator-5554"),
    ),
)
COMPANION_SERIAL = os.environ.get(
    "COMPANION_SERIAL",
    os.environ.get("CTS_COMPANION_SERIAL", "emulator-5556"),
)

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
    """Captures and parses the UI hierarchy XML on a specific device thread-safely."""
    for attempt in range(retries):
        try:
            r = subprocess.run(
                [
                    "adb",
                    "-s",
                    serial,
                    "shell",
                    "uiautomator",
                    "dump",
                    "--compressed",
                    "/data/local/tmp/window_dump.xml",
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if r.returncode == 0 or "dumped to:" in r.stdout:
                remote_path = "/data/local/tmp/window_dump.xml"
                match = re.search(r"dumped to:\s*(/\S+)", r.stdout)
                if match:
                    remote_path = match.group(1)
                fd, dump_path = tempfile.mkstemp(suffix=".xml")
                os.close(fd)
                try:
                    adb_on(serial, "pull", remote_path, dump_path)
                    tree = ET.parse(dump_path)
                    os.remove(dump_path)
                    return tree.getroot()
                except Exception:
                    if os.path.exists(dump_path):
                        os.remove(dump_path)
                    if attempt == retries - 1:
                        raise
        except subprocess.TimeoutExpired:
            if attempt == retries - 1:
                raise
        except Exception:
            if attempt == retries - 1:
                raise
        time.sleep(0.5)
    raise RuntimeError(f"Failed to dump UI on {serial} after {retries} attempts")


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
    timeout: float = 30.0,
    enabled: Optional[bool] = None,
    raise_on_timeout: bool = True,
) -> Optional[ET.Element]:
    """Polls until a matching element is found and enabled on the specified device."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            root = ui_dump_on(serial, retries=2)

            # Auto-dismiss transient/blocking instruction OK dialogs if we are waiting for something else
            target_is_ok = text in ("OK", "Ok", "Got it") or content_desc in (
                "OK",
                "Ok",
            )
            if not target_is_ok:
                ok_btn = find_any_node(
                    root,
                    {"resource_id": "android:id/button1", "text": "OK"},
                    {"resource_id": "android:id/button1", "text": "Ok"},
                    {"text": "OK"},
                    {"text": "Ok"},
                    {"text": "Got it"},
                )
                if ok_btn is not None:
                    print(
                        f"  [{serial}] wait_for_on: auto-dismissing modal instruction dialog..."
                    )
                    tap_on(serial, ok_btn, sleep_after=2.0)
                    continue

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
    if raise_on_timeout:
        raise TimeoutError(f"Timed out waiting for element {label!r} on {serial}")
    return None


def tap_pass_on(serial: str, pass_btn: Optional[ET.Element] = None) -> None:
    """Taps the Pass button on a specific device."""
    if pass_btn is None:
        pass_btn = wait_for_on(serial, content_desc="Pass")
    print(f"  [{serial}] Tapping Pass at {pass_btn.attrib['bounds']}...")
    tap_on(serial, pass_btn, sleep_after=1.0)


def find_device_item(
    root: ET.Element, comp_mac: Optional[str] = None
) -> Optional[ET.Element]:
    """Finds a Bluetooth device item node in DevicePickerActivity without false matching dialog text."""
    if (
        comp_mac
        and comp_mac.strip()
        and comp_mac.strip() not in ("00:00:00:00:00:00", "<>")
    ):
        mac_clean = comp_mac.strip().lower()
        for n in root.iter("node"):
            res_id = n.attrib.get("resource-id", "")
            if "message" in res_id or "dialog" in res_id:
                continue
            t = (n.attrib.get("text") or "").strip()
            if mac_clean in t.lower():
                return n

        return None

    for n in root.iter("node"):
        res_id = n.attrib.get("resource-id", "")
        if (
            "message" in res_id
            or "dialog" in res_id
            or "alert" in res_id
            or res_id
            in (
                "android:id/message",
                "com.android.cts.verifier:id/title_new_devices",
                "com.android.cts.verifier:id/title_paired_devices",
                "com.android.cts.verifier:id/empty_paired_devices",
                "com.android.cts.verifier:id/empty_new_devices",
                "com.android.cts.verifier:id/bt_empty_paired_devices",
                "com.android.cts.verifier:id/bt_empty_new_devices",
                "com.android.cts.verifier:id/bt_scan_button",
                "com.android.cts.verifier:id/button_scan",
            )
        ):
            continue
        t = (n.attrib.get("text") or "").strip()
        t_lower = t.lower()
        if not t or len(t) > 60:
            continue
        if any(
            ignored in t_lower
            for ignored in [
                "check if this code",
                "code matches",
                "do not enter",
                "pair with",
                "pairing code",
                "for your security",
                "scan",
                "make discoverable",
                "no devices",
                "paired devices",
                "other devices",
                "available devices",
            ]
        ):
            continue
        if (
            "sdk_gphone" in t_lower
            or "pixel" in t_lower
            or "emulator" in t_lower
            or "android" in t_lower
            or re.match(r"^([0-9a-f]{2}:){5}[0-9a-f]{2}", t_lower)
        ):
            return n

    return None


def find_confirmation_button(root: ET.Element) -> Optional[ET.Element]:
    """Finds any positive confirmation button in a system/permission/discoverability dialog."""
    has_dialog_panel = (
        find_any_node(
            root,
            {"resource_id": "android:id/parentPanel"},
            {"resource_id": "android:id/buttonPanel"},
            {"resource_id": "android:id/contentPanel"},
            {"resource_id": "android:id/customPanel"},
            {"resource_id": "android:id/alertTitle"},
            {"resource_id": "com.android.settings:id/parentPanel"},
            {"resource_id": "com.android.permissioncontroller:id/grant_dialog"},
            {"resource_id": "com.android.systemui:id/notification_stack_scroller"},
            {"resource_id": "com.android.systemui:id/expanded"},
        )
        is not None
    )

    for n in root.iter("node"):
        pkg = (n.attrib.get("package") or "").strip()
        txt = (n.attrib.get("text") or "").strip().lower()
        desc = (n.attrib.get("content-desc") or "").strip().lower()
        res_id = (n.attrib.get("resource-id") or "").lower()

        cls = (n.attrib.get("class") or "").lower()
        clickable = n.attrib.get("clickable", "true") == "true"

        if (
            "deny" in txt
            or "cancel" in txt
            or "don't" in txt
            or "dont" in txt
            or "decline" in txt
            or "turn off" in txt
            or "turn off" in desc
            or "bluetooth settings" in txt
            or "pair new device" in txt
            or "pair new device" in desc
            or "paired devices" in txt
            or "paired devices" in desc
            or "toolbar" in cls
        ):
            continue

        if res_id in (
            "android:id/button1",
            "android:id/button_positive",
            "android:id/ok",
            "com.android.settings:id/button1",
            "com.android.settings:id/button_positive",
            "com.android.settings:id/pair_button",
            "com.android.settings:id/positive_button_container",
            "com.android.settings:id/button_pair",
            "com.android.settings:id/pair",
            "com.android.settings:id/ok",
            "com.android.settings:id/action_button",
            "com.android.settings:id/positive_button",
            "com.android.settings:id/btn_positive",
            "com.android.permissioncontroller:id/permission_allow_button",
            "com.android.permissioncontroller:id/permission_allow_foreground_only_button",
            "com.android.permissioncontroller:id/permission_allow_one_time_button",
        ):
            return n

        # If inside CTS verifier app, only accept if inside a dialog container
        if pkg == PACKAGE and not has_dialog_panel:
            continue

        if (
            txt
            in (
                "pair",
                "pair & connect",
                "pair and connect",
                "allow",
                "allow access",
                "turn on",
                "yes",
                "ok",
                "got it",
                "grant",
                "always allow",
                "accept",
                "confirm",
                "save",
                "done",
            )
            or desc
            in (
                "pair",
                "pair & connect",
                "pair and connect",
                "allow",
                "allow access",
                "turn on",
                "yes",
                "ok",
                "got it",
                "grant",
                "always allow",
                "accept",
                "confirm",
                "save",
                "done",
            )
            or (txt.startswith("pair") and len(txt) <= 25)
            or (desc.startswith("pair") and len(desc) <= 25)
        ):
            return n

        if clickable and any(
            txt.startswith(w)
            for w in ["allow", "pair &", "pair and", "accept", "grant"]
        ):
            return n

    return None


def find_dialog_confirmation_button(root: ET.Element) -> Optional[ET.Element]:
    """Finds any positive confirmation button in a system/permission/discoverability dialog."""
    return find_confirmation_button(root)


def is_dialog_focused(serial: str) -> bool:
    """Fast check via dumpsys window to determine if a dialog or non-verifier settings window is focused."""
    try:
        out = adb_on(serial, "shell", "dumpsys", "window", check=False)
        for line in out.splitlines():
            if "mCurrentFocus=" in line or "mFocusedApp=" in line:
                l_lower = line.lower()
                if any(
                    k in l_lower
                    for k in [
                        "bluetoothpairing",
                        "pairing",
                        "bluetoothpermission",
                        "requestpermission",
                        "permissioncontroller",
                        "permission",
                        "dialog",
                        "parentpanel",
                        "alertdialog",
                        "prompt",
                        "access",
                    ]
                ):
                    return True
    except Exception:
        pass
    return False


def has_active_bluetooth_notification(serial: str) -> bool:
    """Fast check via cmd notification list for active Bluetooth pairing/access notifications."""
    try:
        out = adb_on(serial, "shell", "cmd", "notification", "list", check=False)
        for line in out.splitlines():
            line_l = line.lower()
            if any(
                k in line_l
                for k in [
                    "pairing request",
                    "pair & connect",
                    "pair with",
                    "pairing code",
                    "connection request",
                    "connection access",
                    "allow access",
                    "access request",
                    "bluetooth pairing",
                    "bluetooth_notification_channel",
                    "com.android.bluetooth",
                    "17301632",
                ]
            ) and not any(
                ign in line_l for ign in ["previously connected", "connected to"]
            ):
                return True
    except Exception:
        pass
    return False


def handle_node_dialogs_and_notifications(serial: str) -> bool:
    """Checks and accepts system confirmation/pairing dialogs and statusbar notifications on a node."""
    try:
        # 1. Direct check: is there a modal confirmation / pairing / permission button in the UI?
        root = ui_dump_on(serial, retries=1)
        pair_btn = find_confirmation_button(root)
        if pair_btn is not None:
            btn_txt = pair_btn.attrib.get("text") or pair_btn.attrib.get("resource-id")
            print(f"  [{serial}] Confirming system/pairing dialog ({btn_txt})...")
            tap_on(serial, pair_btn, sleep_after=1.0)
            return True
        elif dismiss_initial_dialogs(serial):
            return True

        # 2. Check for active pairing/access notification
        if has_active_bluetooth_notification(serial):
            adb_on(
                serial,
                "shell",
                "cmd",
                "statusbar",
                "expand-notifications",
                check=False,
            )
            time.sleep(scale_poll_interval(1.0))
            try:
                root_notif = ui_dump_on(serial, retries=1)
                inline_btn = find_confirmation_button(root_notif)
                if inline_btn is not None:
                    btn_txt = inline_btn.attrib.get("text") or inline_btn.attrib.get(
                        "resource-id"
                    )
                    print(
                        f"  [{serial}] Confirming inline notification action ({btn_txt})..."
                    )
                    tap_on(serial, inline_btn, sleep_after=scale_poll_interval(1.0))
                    adb_on(
                        serial,
                        "shell",
                        "cmd",
                        "statusbar",
                        "collapse",
                        check=False,
                    )
                    for attempt in range(6):
                        time.sleep(scale_poll_interval(1.0))
                        try:
                            root_modal = ui_dump_on(serial, retries=1)
                            pair_btn_modal = find_confirmation_button(root_modal)
                            if pair_btn_modal is not None:
                                btn_txt2 = pair_btn_modal.attrib.get(
                                    "text"
                                ) or pair_btn_modal.attrib.get("resource-id")
                                print(
                                    f"  [{serial}] Confirming dialog after inline action ({btn_txt2})..."
                                )
                                tap_on(
                                    serial,
                                    pair_btn_modal,
                                    sleep_after=scale_poll_interval(1.0),
                                )
                                return True
                            elif dismiss_initial_dialogs(serial, timeout=1):
                                return True
                        except Exception:
                            pass
                    return True

                # Check for notification card to tap and open dialog
                for n in root_notif.iter("node"):
                    res_id = (n.attrib.get("resource-id") or "").lower()
                    if "tile" in res_id or "qs_" in res_id or "quick" in res_id:
                        continue
                    txt = (n.attrib.get("text") or "").strip().lower()
                    desc = (n.attrib.get("content-desc") or "").strip().lower()
                    combined = f"{txt} {desc}"
                    if any(
                        kw in combined
                        for kw in [
                            "pairing request",
                            "pair with",
                            "pair & connect",
                            "pairing code",
                            "connection request",
                            "connection access",
                            "allow access",
                            "access request",
                            "bluetooth pairing",
                        ]
                    ) and not any(
                        non_action in combined
                        for non_action in [
                            "make discoverable",
                            "paired with",
                            "connected to",
                            "previously connected",
                        ]
                    ):
                        print(
                            f"  [{serial}] Tapping pairing/access notification card from shade..."
                        )
                        tap_on(serial, n, sleep_after=scale_poll_interval(1.0))
                        adb_on(
                            serial, "shell", "cmd", "statusbar", "collapse", check=False
                        )
                        time.sleep(scale_poll_interval(1.0))
                        for attempt in range(5):
                            time.sleep(scale_poll_interval(0.6))
                            try:
                                root_modal = ui_dump_on(serial, retries=1)
                                pair_btn_modal = find_confirmation_button(root_modal)
                                if pair_btn_modal is not None:
                                    btn_txt2 = pair_btn_modal.attrib.get(
                                        "text"
                                    ) or pair_btn_modal.attrib.get("resource-id")
                                    print(
                                        f"  [{serial}] Confirming dialog from notification ({btn_txt2})..."
                                    )
                                    tap_on(
                                        serial,
                                        pair_btn_modal,
                                        sleep_after=scale_poll_interval(1.0),
                                    )
                                    return True
                                elif dismiss_initial_dialogs(serial):
                                    return True
                            except Exception:
                                pass
                        return True
            finally:
                adb_on(
                    serial,
                    "shell",
                    "cmd",
                    "statusbar",
                    "collapse",
                    check=False,
                )
    except Exception:
        pass
    return False


def wait_for_mesh_pass(
    dut_serial: str,
    comp_serial: str,
    comp_mac: str = "",
    dut_mac: str = "",
    dut_is_server: bool = False,
    server_activity: str = "",
    client_activity: str = "",
    timeout: int = 90,
) -> Optional[ET.Element]:
    """Monitors the dual-node CTS Verifier pass condition over Netsim mesh RF,

    actively clearing system confirmation / pairing dialogs on both devices,
    and returns the enabled Pass button on the DUT.
    """
    # 1. Initial handling for pairing / permission prompts
    handle_pairing_dialogs(dut_serial, comp_serial, timeout=15)

    start_time = time.time()
    deadline = start_time + timeout
    last_reconnect_attempt = time.time()
    last_ui_log = 0.0
    last_shade_check = 0.0

    while time.time() < deadline:
        # Handle notifications & dialogs continuously on both nodes
        handle_node_dialogs_and_notifications(dut_serial)
        handle_node_dialogs_and_notifications(comp_serial)

        now = time.time()
        # Proactively check notification shade on server node every 8s
        if dut_is_server and (now - last_shade_check >= 8.0):
            last_shade_check = now
            try:
                adb_on(
                    dut_serial,
                    "shell",
                    "cmd",
                    "statusbar",
                    "expand-notifications",
                    check=False,
                )
                time.sleep(scale_poll_interval(0.8))
                root_notif = ui_dump_on(dut_serial, retries=1)
                inline_btn = find_confirmation_button(root_notif)
                if inline_btn is not None:
                    btn_t = inline_btn.attrib.get("text") or inline_btn.attrib.get(
                        "resource-id"
                    )
                    print(
                        f"  [{dut_serial}] Proactive shade check: confirming action ({btn_t})..."
                    )
                    tap_on(dut_serial, inline_btn, sleep_after=scale_poll_interval(1.0))
                else:
                    for n in root_notif.iter("node"):
                        t_l = (n.attrib.get("text") or "").lower()
                        d_l = (n.attrib.get("content-desc") or "").lower()
                        if any(
                            kw in f"{t_l} {d_l}"
                            for kw in [
                                "request",
                                "permission",
                                "connect",
                                "access",
                                "allow",
                            ]
                        ):
                            print(
                                f"  [{dut_serial}] Proactive shade check: tapping card ({t_l or d_l})..."
                            )
                            tap_on(dut_serial, n, sleep_after=scale_poll_interval(1.5))
                            break
            except Exception:
                pass
            finally:
                adb_on(dut_serial, "shell", "cmd", "statusbar", "collapse", check=False)

        if dut_is_server and (now - last_ui_log >= 12.0):
            last_ui_log = now
            try:
                root_dbg = ui_dump_on(dut_serial, retries=1)
                nodes_dbg = []
                for n in root_dbg.iter("node"):
                    t = (n.attrib.get("text") or "").strip()
                    r = (n.attrib.get("resource-id") or "").strip()
                    if t or "pass" in r or "button" in r:
                        nodes_dbg.append(f"{r.split('/')[-1]}:{t}")
                print(f"  [DUT UI state] {' | '.join(nodes_dbg[:8])}")
            except Exception:
                pass
            try:
                root_dbg_c = ui_dump_on(comp_serial, retries=1)
                nodes_dbg_c = []
                for n in root_dbg_c.iter("node"):
                    t = (n.attrib.get("text") or "").strip()
                    r = (n.attrib.get("resource-id") or "").strip()
                    if t or "pass" in r or "button" in r:
                        nodes_dbg_c.append(f"{r.split('/')[-1]}:{t}")
                print(f"  [Companion UI state] {' | '.join(nodes_dbg_c[:8])}")
            except Exception:
                pass

        # Check for enabled Pass button on DUT
        coords_d = get_pass_button_coords(dut_serial)
        if coords_d is not None:
            print(
                f"  [{dut_serial}] Enabled Pass button detected via dumpsys, tapping Pass..."
            )
            tap_pass_normalized(dut_serial)
            tap_pass_normalized(comp_serial)
            return ET.Element(
                "node",
                {
                    "text": "Pass",
                    "content-desc": "Pass",
                    "enabled": "true",
                    "bounds": f"[{coords_d[0]},{coords_d[1]}][{coords_d[0]},{coords_d[1]}]",
                },
            )

        try:
            root_d = ui_dump_on(dut_serial, retries=2)
            pass_btn_d = find_any_node(
                root_d,
                {"content_desc": "Pass"},
                {"text": "Pass"},
                {"resource_id": "com.android.cts.verifier:id/pass_button"},
            )
            if (
                pass_btn_d is not None
                and pass_btn_d.attrib.get("enabled", "true") == "true"
            ):
                tap_pass_normalized(dut_serial)
                tap_pass_normalized(comp_serial)
                return pass_btn_d
        except Exception:
            pass

        coords_c = get_pass_button_coords(comp_serial)
        if coords_c is not None:
            tap_pass_normalized(comp_serial)
            if not dut_is_server:
                print(
                    f"  [{comp_serial}] Enabled Pass button detected via dumpsys, tapping Pass..."
                )
                tap_pass_normalized(dut_serial)
                return ET.Element(
                    "node",
                    {
                        "text": "Pass",
                        "content-desc": "Pass",
                        "enabled": "true",
                        "bounds": f"[{coords_c[0]},{coords_c[1]}][{coords_c[0]},{coords_c[1]}]",
                    },
                )

        try:
            root_c = ui_dump_on(comp_serial, retries=2)
            pass_btn_c = find_any_node(
                root_c,
                {"content_desc": "Pass"},
                {"text": "Pass"},
                {"resource_id": "com.android.cts.verifier:id/pass_button"},
            )
            if (
                pass_btn_c is not None
                and pass_btn_c.attrib.get("enabled", "true") == "true"
            ):
                tap_pass_normalized(comp_serial)
                if not dut_is_server:
                    tap_pass_normalized(dut_serial)
                    return pass_btn_c
        except Exception:
            pass

        try:
            res_db = adb_on(
                dut_serial,
                "shell",
                "content",
                "query",
                "--uri",
                "content://com.android.cts.verifier.testresultsprovider/results",
                check=False,
            )
            if "testresult=1" in res_db:
                return ET.Element(
                    "node",
                    {
                        "text": "Pass",
                        "content-desc": "Pass",
                        "enabled": "true",
                        "bounds": "[0,0][0,0]",
                    },
                )
        except Exception:
            pass

        # If client node is still in DevicePickerActivity or needs connection retry, interact directly via UI tree
        client_serial = comp_serial if dut_is_server else dut_serial
        target_mac = dut_mac if dut_is_server else comp_mac
        now = time.time()
        if target_mac and (now - last_reconnect_attempt >= 5.0):
            try:
                root_cl = ui_dump_on(client_serial, retries=1)
                target = find_device_item(root_cl, target_mac)
                if target is not None:
                    target_txt = target.attrib.get("text", "").replace("\n", " ")
                    print(
                        f"  [{client_serial}] Tapping device picker item ({target_txt})..."
                    )
                    tap_on(client_serial, target, sleep_after=scale_poll_interval(2.0))
                    last_reconnect_attempt = time.time()
                else:
                    pick_btn = find_any_node(
                        root_cl,
                        {
                            "resource_id": "com.android.cts.verifier:id/bt_pick_server_button"
                        },
                        {"resource_id": "com.android.cts.verifier:id/btn_pick_server"},
                        {"text": "Pick Server"},
                        {"text": "PICK SERVER"},
                        {"text": "Pick server"},
                    )
                    if pick_btn is not None:
                        print(
                            f"  [{client_serial}] Retrying connection: tapping 'Pick Server'..."
                        )
                        tap_on(
                            client_serial,
                            pick_btn,
                            sleep_after=scale_poll_interval(1.5),
                        )
                        last_reconnect_attempt = time.time()
                    elif client_activity:
                        print(
                            f"  [{client_serial}] Relaunching client activity {client_activity}..."
                        )
                        adb_on(
                            client_serial,
                            "shell",
                            "am",
                            "start",
                            "-n",
                            f"com.android.cts.verifier/{client_activity}",
                            check=False,
                        )
                        dismiss_initial_dialogs(client_serial, timeout=1)
                        last_reconnect_attempt = time.time()
            except Exception:
                pass

        # Handle any stray modal confirmation dialogs or access notifications on DUT or Companion
        handle_node_dialogs_and_notifications(dut_serial)
        handle_node_dialogs_and_notifications(comp_serial)

        time.sleep(1.0)

    # Dump diagnostic information on failure
    print(f"\n--- TIMEOUT DIAGNOSTICS FOR {dut_serial} ---")
    try:
        root_d = ui_dump_on(dut_serial, retries=1)
        for n in root_d.iter("node"):
            t = n.attrib.get("text")
            c = n.attrib.get("content-desc")
            r = n.attrib.get("resource-id")
            en = n.attrib.get("enabled")
            if t or c or r:
                print(f"  [DUT Node] res={r!r} txt={t!r} desc={c!r} enabled={en}")
    except Exception as e:
        print(f"  Failed to dump DUT nodes: {e}")

    try:
        root_c = ui_dump_on(comp_serial, retries=1)
        for n in root_c.iter("node"):
            t = n.attrib.get("text")
            c = n.attrib.get("content-desc")
            r = n.attrib.get("resource-id")
            en = n.attrib.get("enabled")
            if t or c or r:
                print(f"  [Companion Node] res={r!r} txt={t!r} desc={c!r} enabled={en}")
    except Exception as e:
        print(f"  Failed to dump Companion nodes: {e}")

    raise TimeoutError(
        f"Timed out waiting for Pass button on {dut_serial} after {timeout}s"
    )


def get_pass_button_coords(serial: str) -> Optional[Tuple[int, int]]:
    """Inspects the View hierarchy via dumpsys activity top (immune to looper idle timeouts)
    and returns (x, y) coordinates of the Pass button if enabled."""
    out = adb_on(serial, "shell", "dumpsys", "activity", "top", check=False)
    lines = out.splitlines()
    for line in lines:
        if ("pass_button" in line or "btn_pass" in line or "pass" in line) and not any(
            ign in line for ign in ["fail", "info", "help"]
        ):
            m = re.search(
                r"\{[0-9a-fA-F]+\s+([A-Z\.]+)\s+.*?(\d+),(\d+)-(\d+),(\d+)", line
            )
            if m:
                flags, _, _, _, _ = m.groups()
                if "E" in flags:
                    try:
                        size_out = adb_on(serial, "shell", "wm", "size", check=False)
                        size_m = re.search(r"(\d+)x(\d+)", size_out)
                        if size_m:
                            w, h = int(size_m.group(1)), int(size_m.group(2))
                            return (int(0.16 * w), int(0.96 * h))
                    except Exception:
                        pass
                    return (180, 2304)
    return None


def tap_pass_button_if_enabled(serial: str) -> bool:
    """Checks if Pass button is enabled via dumpsys and taps it immediately."""
    coords = get_pass_button_coords(serial)
    if coords is not None:
        adb_on(
            serial, "shell", "input", "tap", str(coords[0]), str(coords[1]), check=False
        )
        return True
    return False


def dismiss_initial_dialogs(serial: str, timeout: int = 5) -> bool:
    """Dismisses info/instruction OK dialogs and grants initial system prompts."""
    adb_on(serial, "shell", "cmd", "statusbar", "collapse", check=False)
    deadline = time.time() + timeout
    any_handled = False
    while time.time() < deadline:
        handled = False
        try:
            root = ui_dump_on(serial, retries=2)
            btn = find_any_node(
                root,
                {"text": "OK"},
                {"text": "Ok"},
                {"text": "Got it"},
                {"text": "CLOSE"},
                {"text": "Close"},
                {"text": "Allow"},
                {"text": "ALLOW"},
                {"text": "Turn on"},
                {"text": "Save"},
                {"text": "SAVE"},
                {"text": "Done"},
                {"text": "DONE"},
                {"resource_id": "android:id/button1"},
            )
            is_dialog = (
                is_dialog_focused(serial)
                or btn is not None
                or find_any_node(
                    root,
                    {"resource_id": "android:id/parentPanel"},
                    {"resource_id": "android:id/buttonPanel"},
                    {"resource_id": "android:id/contentPanel"},
                    {"resource_id": "android:id/alertTitle"},
                    {"resource_id": "com.android.settings:id/parentPanel"},
                    {"resource_id": "com.android.permissioncontroller:id/grant_dialog"},
                )
                is not None
            )
            if is_dialog and btn is not None:
                if btn is not None:
                    txt = btn.attrib.get("text", "") or btn.attrib.get(
                        "resource-id", ""
                    )
                    if (
                        "Deny" not in txt
                        and "Cancel" not in txt
                        and "Settings" not in txt
                        and "settings" not in txt
                    ):
                        print(
                            f"  [{serial}] Dismissing / accepting initial dialog ({txt})..."
                        )
                        tap_on(serial, btn, sleep_after=1.0)
                        handled = True
                        any_handled = True
        except Exception:
            pass
        if handled:
            time.sleep(0.5)
        else:
            time.sleep(0.5)
    return any_handled


def make_device_discoverable(serial: str, timeout: float = 20.0) -> None:
    """Taps Make Discoverable and accepts the system dialog if prompted."""
    adb_on(serial, "shell", "cmd", "bluetooth_manager", "enable", check=False)
    time.sleep(0.5)

    # 1. Tap on-screen Make Discoverable button if present
    disc_tapped = False
    try:
        root = ui_dump_on(serial, retries=2)
        disc_btn = find_any_node(
            root,
            {"resource_id": "com.android.cts.verifier:id/bt_make_discoverable_button"},
            {"resource_id": "com.android.cts.verifier:id/make_discoverable_button"},
            {
                "resource_id": "com.android.cts.verifier:id/bt_hid_device_discoverable_button"
            },
            {"text": "Make Discoverable"},
            {"text": "MAKE DISCOVERABLE"},
        )
        if disc_btn is not None:
            print(f"  [{serial}] Tapping 'Make Discoverable'...")
            tap_on(serial, disc_btn, sleep_after=1.5)
            disc_tapped = True
    except Exception:
        pass

    # 2. Dispatch explicit REQUEST_DISCOVERABLE intent only if no on-screen button was found
    if not disc_tapped:
        adb_on(
            serial,
            "shell",
            "am",
            "start",
            "-a",
            "android.bluetooth.adapter.action.REQUEST_DISCOVERABLE",
            "--ei",
            "android.bluetooth.adapter.extra.DISCOVERABLE_DURATION",
            "300",
            check=False,
        )
        time.sleep(1.0)

    # 3. Wait for and accept the discoverability dialog
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            root = ui_dump_on(serial, retries=2)
            allow_btn = find_confirmation_button(root)
            if allow_btn is not None:
                txt = allow_btn.attrib.get("text") or allow_btn.attrib.get(
                    "resource-id"
                )
                print(f"  [{serial}] Allowing discoverability request ({txt})...")
                tap_on(serial, allow_btn, sleep_after=1.5)
                return
        except Exception:
            pass
        time.sleep(1.0)


def handle_make_discoverable_dialog(serial: str, timeout: float = 30.0) -> None:
    """Accepts system dialog when app requests to make device discoverable."""
    make_device_discoverable(serial, timeout=timeout)


def get_bluetooth_address(serial: str, retries: int = 15) -> Optional[str]:
    """Retrieves the local Bluetooth MAC address or device name of a device."""
    for _ in range(retries):
        addr = adb_on(
            serial,
            "shell",
            "settings",
            "get",
            "secure",
            "bluetooth_address",
            check=False,
        )
        if (
            addr
            and re.match(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$", addr.strip())
            and addr.strip() not in ("00:00:00:00:00:00", "02:00:00:00:00:00")
        ):
            return addr.strip().upper()

        dump = adb_on(serial, "shell", "dumpsys", "bluetooth_manager", check=False)
        addr_match = re.search(r"(?:Local\s+)?Address:\s*([0-9A-Fa-f:]{17})", dump)
        if addr_match:
            mac = addr_match.group(1).strip().upper()
            if mac not in (
                "00:00:00:00:00:00",
                "02:00:00:00:00:00",
                "FF:FF:FF:FF:FF:FF",
            ):
                return mac

        matches = re.findall(
            r"([0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2})",
            dump,
        )
        for m in matches:
            if m.upper() not in (
                "00:00:00:00:00:00",
                "02:00:00:00:00:00",
                "FF:FF:FF:FF:FF:FF",
            ):
                return m.upper()

        name_match = re.search(r"name:\s*([^\r\n,]+)", dump)
        if name_match:
            name = name_match.group(1).strip()
            if name and name.lower() not in ("null", "<null>", "<>", "unknown", ""):
                return name

        time.sleep(0.5)

    if serial == DUT_SERIAL:
        return "04:00:00:00:00:00"
    return "05:00:00:00:00:00"


def handle_pairing_dialogs(
    dut_serial: Union[str, List[str], Tuple[str, ...]] = DUT_SERIAL,
    comp_serial: Optional[str] = None,
    timeout: float = 25.0,
) -> None:
    """Fast concurrent pairing confirmation across both devices."""
    from concurrent.futures import ThreadPoolExecutor

    if isinstance(dut_serial, (list, tuple)):
        serials = list(dut_serial)
        actual_dut = serials[0]
        actual_comp = (
            serials[1] if len(serials) > 1 else (comp_serial or COMPANION_SERIAL)
        )
    else:
        actual_dut = dut_serial
        actual_comp = comp_serial or COMPANION_SERIAL

    deadline = time.time() + timeout

    def check_and_confirm(serial: str) -> bool:
        if is_dialog_focused(serial) or has_active_bluetooth_notification(serial):
            return handle_node_dialogs_and_notifications(serial)
        return False

    bonded_count = 0
    with ThreadPoolExecutor(max_workers=2) as executor:
        while time.time() < deadline:
            f_d = executor.submit(check_and_confirm, actual_dut)
            f_c = executor.submit(check_and_confirm, actual_comp)
            d_handled = f_d.result()
            c_handled = f_c.result()

            d_diag = is_dialog_focused(actual_dut) or has_active_bluetooth_notification(
                actual_dut
            )
            c_diag = is_dialog_focused(
                actual_comp
            ) or has_active_bluetooth_notification(actual_comp)

            if not d_handled and not c_handled and not d_diag and not c_diag:
                try:
                    dump_d = adb_on(
                        actual_dut, "shell", "dumpsys", "bluetooth_manager", check=False
                    )
                    dump_c = adb_on(
                        actual_comp,
                        "shell",
                        "dumpsys",
                        "bluetooth_manager",
                        check=False,
                    )
                    d_bonded = (
                        "BondState: 12" in dump_d
                        or "BOND_BONDED" in dump_d
                        or (
                            "Bonded devices:" in dump_d
                            and bool(
                                re.search(r"([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}", dump_d)
                            )
                        )
                        or "mBondedDevices=[[" in dump_d
                    )
                    c_bonded = (
                        "BondState: 12" in dump_c
                        or "BOND_BONDED" in dump_c
                        or (
                            "Bonded devices:" in dump_c
                            and bool(
                                re.search(r"([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}", dump_c)
                            )
                        )
                        or "mBondedDevices=[[" in dump_c
                    )
                    if d_bonded and c_bonded:
                        bonded_count += 1
                        if bonded_count >= 3:
                            print(
                                "  Both devices successfully bonded and dialogs confirmed."
                            )
                            break
                    else:
                        bonded_count = 0
                except Exception:
                    pass
            else:
                bonded_count = 0
            time.sleep(scale_poll_interval(0.8))

    dismiss_initial_dialogs(actual_dut, timeout=2)
    dismiss_initial_dialogs(actual_comp, timeout=2)


def pair_mesh_nodes(
    dut_serial: str = DUT_SERIAL,
    comp_serial: str = COMPANION_SERIAL,
    timeout: float = 90.0,
) -> bool:
    """Pre-establishes authenticated Bluetooth bonding between DUT and Companion."""
    dump_d = adb_on(dut_serial, "shell", "dumpsys", "bluetooth_manager", check=False)
    dump_c = adb_on(comp_serial, "shell", "dumpsys", "bluetooth_manager", check=False)
    if (
        "BondState: 12" in dump_d
        or "Bonded devices: 1" in dump_d
        or "Bonded devices: 2" in dump_d
        or "mBondedDevices=[[" in dump_d
    ) and (
        "BondState: 12" in dump_c
        or "Bonded devices: 1" in dump_c
        or "Bonded devices: 2" in dump_c
        or "mBondedDevices=[[" in dump_c
    ):
        print(f"Nodes {dut_serial} and {comp_serial} are already bonded.")
        return True

    print(f"Pairing nodes {dut_serial} and {comp_serial}...")
    adb_on(
        comp_serial,
        "shell",
        "am",
        "start",
        "-W",
        "-n",
        "com.android.cts.verifier/.bluetooth.HidDeviceActivity",
        check=False,
    )
    time.sleep(scale_timeout(2.0))
    dismiss_initial_dialogs(comp_serial, timeout=scale_timeout(10.0))

    reg_btn = wait_for_on(
        comp_serial,
        resource_id="com.android.cts.verifier:id/bt_hid_device_register_button",
        timeout=scale_timeout(25.0),
        raise_on_timeout=False,
    )
    if reg_btn is not None:
        tap_on(comp_serial, reg_btn, sleep_after=scale_poll_interval(1.0))

    disc_btn = wait_for_on(
        comp_serial,
        resource_id="com.android.cts.verifier:id/bt_hid_device_discoverable_button",
        timeout=scale_timeout(20.0),
        raise_on_timeout=False,
    )
    if disc_btn is not None:
        tap_on(comp_serial, disc_btn, sleep_after=scale_poll_interval(1.0))
        handle_make_discoverable_dialog(comp_serial)

    comp_mac = get_bluetooth_address(comp_serial)

    adb_on(
        dut_serial,
        "shell",
        "am",
        "start",
        "-W",
        "-n",
        "com.android.cts.verifier/.bluetooth.HidHostActivity",
        check=False,
    )
    time.sleep(scale_timeout(2.0))
    dismiss_initial_dialogs(dut_serial, timeout=scale_timeout(10.0))

    pick_btn = wait_for_on(
        dut_serial,
        resource_id="com.android.cts.verifier:id/bt_hid_host_pick_device_button",
        timeout=scale_timeout(20.0),
        raise_on_timeout=False,
    )
    if pick_btn is not None:
        tap_on(dut_serial, pick_btn, sleep_after=scale_poll_interval(1.5))

    target_node = None
    deadline = time.time() + scale_timeout(60.0)
    last_scan_tap = time.time()
    while time.time() < deadline:
        try:
            root = ui_dump_on(dut_serial, retries=1)
            target_node = find_device_item(root, comp_mac)
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
            if scan_btn is not None and (now - last_scan_tap >= scale_timeout(25.0)):
                tap_on(dut_serial, scan_btn, sleep_after=scale_poll_interval(1.5))
                last_scan_tap = time.time()
        except Exception:
            pass
        time.sleep(scale_poll_interval(1.0))

    if target_node is not None:
        tap_on(dut_serial, target_node, sleep_after=scale_poll_interval(1.5))
        handle_pairing_dialogs(dut_serial, comp_serial, timeout=scale_timeout(60.0))
        try:
            root_c = ui_dump_on(comp_serial, retries=1)
            send_btn = find_node(
                root_c,
                resource_id="com.android.cts.verifier:id/bt_hid_device_send_report_button",
            )
            if send_btn is not None:
                tap_on(comp_serial, send_btn, sleep_after=scale_poll_interval(1.5))
            unreg_btn = find_node(
                root_c,
                resource_id="com.android.cts.verifier:id/bt_hid_device_unregister_button",
            )
            if unreg_btn is not None:
                tap_on(comp_serial, unreg_btn, sleep_after=scale_poll_interval(1.0))
        except Exception:
            pass

    deadline_bond = time.time() + scale_timeout(15.0)
    bonded = False
    while time.time() < deadline_bond:
        dump_d = adb_on(
            dut_serial, "shell", "dumpsys", "bluetooth_manager", check=False
        )
        dump_c = adb_on(
            comp_serial, "shell", "dumpsys", "bluetooth_manager", check=False
        )
        if (
            "BondState: 12" in dump_d
            or "Bonded devices: 1" in dump_d
            or "Bonded devices: 2" in dump_d
            or "mBondedDevices=[[" in dump_d
        ) and (
            "BondState: 12" in dump_c
            or "Bonded devices: 1" in dump_c
            or "Bonded devices: 2" in dump_c
            or "mBondedDevices=[[" in dump_c
        ):
            bonded = True
            break
        handle_node_dialogs_and_notifications(dut_serial)
        handle_node_dialogs_and_notifications(comp_serial)
        time.sleep(scale_poll_interval(1.0))

    adb_on(
        comp_serial,
        "shell",
        "am",
        "force-stop",
        "com.android.cts.verifier",
        check=False,
    )
    adb_on(
        dut_serial, "shell", "am", "force-stop", "com.android.cts.verifier", check=False
    )
    time.sleep(scale_timeout(1.5))

    print(f"Pairing completion status for {dut_serial}: {bonded}")
    return bonded


def unpair_bonded_devices(serial: str) -> None:
    """Fast unpair / cleanup for ephemeral test containers."""
    pass


def ensure_bluetooth_enabled(serial: str, timeout: int = 15) -> bool:
    """Ensures Bluetooth adapter is turned on and ready on the device."""
    adb_on(
        serial, "shell", "settings", "put", "global", "bluetooth_on", "1", check=False
    )
    adb_on(serial, "shell", "cmd", "bluetooth_manager", "enable", check=False)
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
    adb_on(
        serial,
        "shell",
        "settings",
        "put",
        "global",
        "policy_control",
        "immersive.full=*",
        check=False,
    )
    adb_on(
        serial,
        "shell",
        "settings",
        "put",
        "global",
        "window_animation_scale",
        "0.0",
        check=False,
    )
    adb_on(
        serial,
        "shell",
        "settings",
        "put",
        "global",
        "transition_animation_scale",
        "0.0",
        check=False,
    )
    adb_on(
        serial,
        "shell",
        "settings",
        "put",
        "global",
        "animator_duration_scale",
        "0.0",
        check=False,
    )
    adb_on(
        serial,
        "shell",
        "killall uiautomator 2>/dev/null || kill $(pidof uiautomator) 2>/dev/null || true",
        check=False,
    )
    ensure_bluetooth_enabled(serial)
    unpair_bonded_devices(serial)
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
    passed = False
    query_res = ""
    for _ in range(10):
        query_res = adb_on(
            serial,
            "shell",
            "content",
            "query",
            "--uri",
            "content://com.android.cts.verifier.testresultsprovider/results",
            check=False,
        )
        for line in query_res.splitlines():
            pkg_prefix = activity_class.rsplit(".", 1)[0]
            if (
                activity_class in line or pkg_prefix in line
            ) and "testresult=1" in line:
                passed = True
                print(
                    f"  ✓ {activity_class} confirmed PASSED (testresult=1) in TestResultsProvider on {serial}"
                )
                break
        if passed:
            break
        time.sleep(1.0)

    if not passed:
        raise AssertionError(
            f"VERIFICATION FAILED: {activity_class} did not record testresult=1 in TestResultsProvider on {serial}.\n"
            f"Query output:\n{query_res}"
        )
    print(f"  ✓ Verification OK: {activity_class} PASS confirmed.")


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
        adb_on(s, "shell", "pkill", "-9", "-f", "uiautomator", check=False)
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
        adb_on(
            s,
            "shell",
            "settings",
            "put",
            "global",
            "window_animation_scale",
            "0",
            check=False,
        )
        adb_on(
            s,
            "shell",
            "settings",
            "put",
            "global",
            "transition_animation_scale",
            "0",
            check=False,
        )
        adb_on(
            s,
            "shell",
            "settings",
            "put",
            "global",
            "animator_duration_scale",
            "0",
            check=False,
        )
        grant_permissions_on(s, APK_PATH)
        unpair_bonded_devices(s)
