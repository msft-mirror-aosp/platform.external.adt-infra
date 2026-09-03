#!/usr/bin/env python3
"""Authentic CTS Verifier Multinetwork Connectivity Test Automation.

Tests simultaneous Wi-Fi and Cellular multi-network fallback:
1. Creates an isolated simulated Wi-Fi Access Point with no WAN internet gateway via Netsim.
2. Navigates to MultiNetworkConnectivityTestActivity.
3. Inputs the SSID and WPA2 passphrase.
4. Taps Start Test to execute multi-network validation passes.
5. Manages AP lifecycle (simulating Wi-Fi connectivity loss) during fallback validation.
6. Verifies toolbar Pass button enabled and tap Pass.
7. Exports test report and asserts passing result in test_result.xml.
"""

import glob
import os
import re
import shutil
import subprocess
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
    adb,
    export_and_verify,
    find_any_node,
    find_node,
    navigate_to,
    set_screenshot_dir,
    setup,
    tap,
    tap_pass,
    ui_dump,
    wait_for,
)

TEST_NAME = "Multinetwork connectivity Test"
ACTIVITY_CLASS = "com.android.cts.verifier.net.MultiNetworkConnectivityTestActivity"
AP_SSID = "CtsVerifierAp"
AP_PASSWORD = "password123"


def find_netsim_binary():
    """Locate the netsim CLI executable."""
    env_bin = os.environ.get("NETSIM_BIN")
    if env_bin and os.path.isfile(env_bin) and os.access(env_bin, os.X_OK):
        return env_bin

    which_netsim = shutil.which("netsim")
    if which_netsim:
        return which_netsim

    # Check alongside emulator binary if known
    which_emu = shutil.which("emulator")
    if which_emu:
        emu_dir = os.path.dirname(which_emu)
        candidates = [
            os.path.join(emu_dir, "netsim"),
            os.path.join(emu_dir, "bin", "netsim"),
            os.path.join(os.path.dirname(emu_dir), "bin", "netsim"),
        ]
        for c in candidates:
            if os.path.isfile(c) and os.access(c, os.X_OK):
                return c

    default_paths = [
        "/tmp/emu/emulator/bin/netsim",
        "/tmp/emu/emulator/netsim",
    ]
    for p in default_paths:
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p

    # Search in Bazel runfiles or cache
    matches = glob.glob(
        "/usr/local/google/home/jansene/.cache/bazel/**/bin/netsim",
        recursive=True,
    )
    for m in matches:
        if os.path.isfile(m) and os.access(m, os.X_OK):
            return m

    return "netsim"


def create_netsim_ap(netsim_bin, ssid, password):
    """Create a new Wi-Fi Access Point in Netsim."""
    print(f"  Creating Netsim Wi-Fi AP: SSID={ssid}...")
    try:
        out = subprocess.check_output(
            [
                netsim_bin,
                "ap",
                "create",
                "--ssid",
                ssid,
                "--password",
                password,
                "--protocol",
                "g",
                "--channel",
                "6",
            ],
            text=True,
            stderr=subprocess.STDOUT,
        )
        print(f"  Netsim AP create response: {out.strip()}")
    except Exception as e:
        print(f"  Warning: netsim ap create failed: {e}")

    # Query AP ID
    ap_id = None
    try:
        list_out = subprocess.check_output(
            [netsim_bin, "ap", "list"], text=True, stderr=subprocess.STDOUT
        )
        for line in list_out.splitlines():
            if ssid in line:
                parts = line.split("|")
                if parts:
                    ap_id = parts[0].strip()
                    break
    except Exception as e:
        print(f"  Warning: netsim ap list failed: {e}")

    return ap_id


def remove_netsim_ap(netsim_bin, ap_id):
    """Remove a Wi-Fi Access Point in Netsim."""
    if not ap_id:
        return
    print(f"  Removing Netsim Wi-Fi AP ID={ap_id}...")
    try:
        subprocess.run(
            [netsim_bin, "ap", "remove", str(ap_id)],
            check=False,
            capture_output=True,
        )
    except Exception as e:
        print(f"  Warning: netsim ap remove failed: {e}")


def dismiss_initial_dialog():
    """Dismiss instructions dialog if displayed."""
    root = ui_dump()
    ok_btn = find_any_node(root, [("text", "OK"), ("text", "Ok"), ("text", "ok")])
    if ok_btn is not None:
        print("  Dismissing instructions OK dialog...")
        tap(ok_btn)
        time.sleep(1.5)


def locate_start_button(root):
    """Locate Start Test button."""
    btn = find_any_node(
        root,
        [
            ("resource_id", "com.android.cts.verifier:id/start_test"),
            ("text", "Start Test"),
            ("text", "Start test"),
            ("text", "START TEST"),
            ("text", "Start"),
        ],
    )
    if btn is not None:
        return btn
    for n in root.iter("node"):
        txt = (n.attrib.get("text") or "").upper()
        if "START" in txt:
            return n
    return None


def fill_input_fields(ssid, password):
    """Find and populate the SSID and Password EditText fields."""
    root = ui_dump()
    edit_texts = []
    for n in root.iter("node"):
        if n.attrib.get("class") == "android.widget.EditText":
            edit_texts.append(n)

    if len(edit_texts) >= 2:
        print(f"  Entering SSID '{ssid}' into first field...")
        tap(edit_texts[0])
        time.sleep(0.5)
        adb("shell", "input", "keyevent", "KEYCODE_MOVE_END", check=False)
        for _ in range(30):
            adb("shell", "input", "keyevent", "KEYCODE_DEL", check=False)
        adb("shell", "input", "text", ssid, check=False)
        time.sleep(1)

        print(f"  Entering Password into second field...")
        tap(edit_texts[1])
        time.sleep(0.5)
        adb("shell", "input", "keyevent", "KEYCODE_MOVE_END", check=False)
        for _ in range(30):
            adb("shell", "input", "keyevent", "KEYCODE_DEL", check=False)
        adb("shell", "input", "text", password, check=False)
        time.sleep(1)
        adb("shell", "input", "keyevent", "KEYCODE_BACK", check=False)
        time.sleep(1)


def main():
    setup()
    set_screenshot_dir("multinetwork_connectivity_test")

    netsim_bin = find_netsim_binary()
    print(f"Using netsim binary: {netsim_bin}")
    ap_id = None

    try:
        print("Pre-test setup: ensuring screen unlocked, cellular and Wi-Fi active...")
        adb("shell", "input", "keyevent", "KEYCODE_WAKEUP", check=False)
        adb("shell", "wm", "dismiss-keyguard", check=False)
        adb("shell", "svc", "data", "enable", check=False)
        adb("shell", "svc", "wifi", "enable", check=False)
        time.sleep(2)

        # Create simulated AP in Netsim
        ap_id = create_netsim_ap(netsim_bin, AP_SSID, AP_PASSWORD)

        navigate_to(TEST_NAME, verify_title="Multinetwork")
        time.sleep(2)
        dismiss_initial_dialog()

        fill_input_fields(AP_SSID, AP_PASSWORD)

        root = ui_dump()
        start_btn = locate_start_button(root)
        if start_btn is not None:
            print("  Tapping Start Test...")
            tap(start_btn)
            time.sleep(3)

        # Wait for test stages to progress
        print("Monitoring multinetwork test progression...")
        start_time = time.time()
        ap_removed = False

        while time.time() - start_time < 90:
            root = ui_dump()
            pass_btn = find_any_node(
                root,
                [
                    ("resource_id", "com.android.cts.verifier:id/pass_button"),
                    ("content_desc", "Pass"),
                ],
            )
            if pass_btn is not None and pass_btn.attrib.get("enabled") == "true":
                print("  Pass button is enabled!")
                break

            # If Test 3 is waiting for Wi-Fi loss, remove the AP
            if not ap_removed and (time.time() - start_time > 30):
                print("  Simulating Wi-Fi disconnection for fallback stage...")
                remove_netsim_ap(netsim_bin, ap_id)
                ap_removed = True

            time.sleep(3)

        if pass_btn is None or pass_btn.attrib.get("enabled") != "true":
            raise TimeoutError(
                "Multinetwork Connectivity Test did not pass: Pass button was not enabled"
            )

        tap_pass(pass_btn)
        time.sleep(2)

        print("Exporting and validating test report...")
        export_and_verify(ACTIVITY_CLASS)
        print(">>> Multinetwork Connectivity Test PASSED authentically!")
        return 0

    finally:
        if ap_id:
            remove_netsim_ap(netsim_bin, ap_id)
        adb("shell", "input", "keyevent", "KEYCODE_WAKEUP", check=False)
        adb("shell", "wm", "dismiss-keyguard", check=False)


if __name__ == "__main__":
    sys.exit(main())
