#!/usr/bin/env python3
"""
Accelerometer Measurement Tests automation script.
Injects expected gravity vector into the emulator's Goldfish accelerometer for each
device orientation sub-test:
  - testFaceUp:     (0, 0, +9.81)
  - testFaceDown:   (0, 0, -9.81)
  - testRightSide:  (-9.81, 0, 0)
  - testLeftSide:   (+9.81, 0, 0)
  - testTopSide:    (0, -9.81, 0)
  - testBottomSide: (0, +9.81, 0)
"""

import re
import subprocess
import time
from cts_common import (
    PACKAGE,
    adb,
    export_and_verify,
    find_node,
    navigate_to,
    screenshot,
    set_screenshot_dir,
    setup,
    tap,
    ui_dump,
)

TEST_NAME = "Accelerometer Measurement Tests"
set_screenshot_dir("sensors_accelerometer_measurement_tests")

G = 9.81
ACCEL_ORIENTATIONS = {
    "testFaceUp": (0.0, 0.0, G),
    "testFaceDown": (0.0, 0.0, -G),
    "testRightSide": (-G, 0.0, 0.0),
    "testLeftSide": (G, 0.0, 0.0),
    "testTopSide": (0.0, -G, 0.0),
    "testBottomSide": (0.0, G, 0.0),
}
DEFAULT_ACCEL = (0.0, 0.0, G)


def sensor_settings():
    subprocess.run(
        [
            "adb",
            "shell",
            "am",
            "broadcast",
            "-a",
            "android.intent.action.AIRPLANE_MODE",
            "--ez",
            "state",
            "true",
        ],
        capture_output=True,
    )
    adb("shell", "settings", "put", "global", "airplane_mode_on", "1")
    adb("shell", "settings", "put", "system", "screen_brightness_mode", "0")
    adb("shell", "settings", "put", "secure", "doze_enabled", "0")
    adb("shell", "settings", "put", "system", "accelerometer_rotation", "0")
    adb("shell", "settings", "put", "global", "stay_on_while_plugged_in", "0")
    adb("shell", "settings", "put", "system", "screen_off_timeout", "1800000")
    adb("shell", "settings", "put", "secure", "location_mode", "0")
    adb("shell", "input", "keyevent", "KEYCODE_WAKEUP")


def inject_accel(x, y, z):
    val = f"{x}:{y}:{z}"
    subprocess.run(
        ["adb", "-e", "emu", "sensor", "set", "acceleration", val],
        capture_output=True,
    )
    uncal_val = f"{x}:{y}:{z}:0:0:0"
    subprocess.run(
        ["adb", "-e", "emu", "sensor", "set", "acceleration-uncalibrated", uncal_val],
        capture_output=True,
    )


def current_sub_test(root):
    last = None
    for n in root.iter("node"):
        t = n.get("text", "")
        if re.match(r"^test[A-Za-z]", t):
            last = t
    return last


def wait_for_sub_test_result(sub_name, x, y, z, max_wait=120):
    print(f"    Waiting for {sub_name!r} result (up to {max_wait}s)...")
    start = time.time()
    while time.time() - start < max_wait:
        inject_accel(x, y, z)
        time.sleep(2)
        root = ui_dump()

        pass_btn = find_node(root, content_desc="Pass") or find_node(root, text="Pass")
        if pass_btn is not None and pass_btn.get("enabled") == "true":
            print(f"    >> OVERALL PASS after {time.time()-start:.0f}s")
            return "overall_pass"

        retry_btn = next(
            (n for n in root.iter("node") if n.get("text", "").startswith("Retry")),
            None,
        )
        if retry_btn is not None and retry_btn.get("enabled") == "true":
            print(f"    >> {sub_name!r} FAILED: {retry_btn.get('text')}")
            return "fail"

        nxt = find_node(root, text="Next")
        if nxt is not None and nxt.get("enabled") == "true":
            texts = [n.get("text", "") for n in root.iter("node")]
            try:
                idx = next(i for i, t in enumerate(texts) if t == sub_name)
                after = texts[idx + 1 :]
                if any("PASS" in a for a in after):
                    print(f"    >> {sub_name!r} PASSED after {time.time()-start:.0f}s!")
                    return "pass"
            except StopIteration:
                pass
            if current_sub_test(root) != sub_name:
                return "pass"

    return "timeout"


setup()
sensor_settings()
inject_accel(*DEFAULT_ACCEL)
screenshot("launched")

root = ui_dump()
close_btn = find_node(root, text="Close")
if close_btn is not None:
    tap(close_btn)
    time.sleep(2)

navigate_to(TEST_NAME)
time.sleep(2)
screenshot("test_opened")

root = ui_dump()
ok = find_node(root, text="OK")
if ok is not None and ok.get("enabled") == "true":
    tap(ok)
    time.sleep(2)
    screenshot("ok_dismissed")

overall_done = False
last_sub = None
for outer in range(60):
    root = ui_dump()

    pass_btn = find_node(root, content_desc="Pass") or find_node(root, text="Pass")
    if pass_btn is not None and pass_btn.get("enabled") == "true":
        print("Tapping overall Pass...")
        tap(pass_btn)
        time.sleep(2)
        screenshot("pass_tapped")
        overall_done = True
        break

    retry_btn = next(
        (n for n in root.iter("node") if n.get("text", "").startswith("Retry")), None
    )
    if retry_btn is not None and retry_btn.get("enabled") == "true":
        sub = current_sub_test(root) or last_sub
        ax, ay, az = ACCEL_ORIENTATIONS.get(sub, DEFAULT_ACCEL)
        print(f"  Retry for {sub!r} — re-injecting {ax}:{ay}:{az} and tapping Retry")
        inject_accel(ax, ay, az)
        time.sleep(1)
        tap(retry_btn)
        time.sleep(2)
        result = wait_for_sub_test_result(sub or "unknown", ax, ay, az)
        if result == "overall_pass":
            root_f = ui_dump()
            pb = find_node(root_f, content_desc="Pass") or find_node(
                root_f, text="Pass"
            )
            if pb is not None and pb.get("enabled") == "true":
                tap(pb)
                time.sleep(2)
                screenshot("pass_tapped")
            overall_done = True
            break
        continue

    nxt = find_node(root, text="Next")
    if nxt is not None and nxt.get("enabled") == "true":
        sub = current_sub_test(root)
        if sub is not None:
            last_sub = sub
        ax, ay, az = ACCEL_ORIENTATIONS.get(sub, DEFAULT_ACCEL)
        print(f"  Next enabled; sub-test={sub!r}; injecting accel {ax}:{ay}:{az}")
        inject_accel(ax, ay, az)
        time.sleep(0.5)
        tap(nxt)
        time.sleep(2)
        root2 = ui_dump()
        in_cts = any(PACKAGE in n.get("package", "") for n in root2.iter("node"))
        if not in_cts:
            adb("shell", "input", "keyevent", "KEYCODE_BACK")
            time.sleep(2)
            continue
        if sub is not None:
            result = wait_for_sub_test_result(sub, ax, ay, az)
            if result == "overall_pass":
                root_f = ui_dump()
                pb = find_node(root_f, content_desc="Pass") or find_node(
                    root_f, text="Pass"
                )
                if pb is not None and pb.get("enabled") == "true":
                    tap(pb)
                    time.sleep(2)
                    screenshot("pass_tapped")
                overall_done = True
                break
        continue

    time.sleep(2)

inject_accel(*DEFAULT_ACCEL)

if not overall_done:
    raise RuntimeError("Test loop exited without reaching Pass")

export_and_verify(TEST_NAME)
screenshot("export_done")
