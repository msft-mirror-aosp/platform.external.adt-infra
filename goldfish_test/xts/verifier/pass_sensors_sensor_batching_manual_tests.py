#!/usr/bin/env python3
"""
Sensor Batching Manual Tests automation script.
On Goldfish emulator, step_counter and step_detector are skipped (not present), while
proximity and light sensors are exercised for batching (12s) and flush (5s) subtests.
We alternate injected proximity (0 / 5) and light (100 / 500) values so on-change
events are generated during each subtest window.
"""

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

TEST_NAME = "Sensor Batching Manual Tests"
set_screenshot_dir("sensors_sensor_batching_manual_tests")


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


def inject_prox_and_light(step_idx):
    prox_val = "0" if (step_idx % 2 == 0) else "5"
    light_val = "100" if (step_idx % 2 == 0) else "500"
    subprocess.run(
        ["adb", "-e", "emu", "sensor", "set", "proximity", prox_val],
        capture_output=True,
    )
    subprocess.run(
        ["adb", "-e", "emu", "sensor", "set", "light", light_val],
        capture_output=True,
    )


setup()
sensor_settings()
inject_prox_and_light(0)
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

overall_done = False
toggle_idx = 0
for _ in range(90):
    toggle_idx += 1
    inject_prox_and_light(toggle_idx)
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
        print("  Tapping Retry...")
        tap(retry_btn)
        for s in range(8):
            toggle_idx += 1
            inject_prox_and_light(toggle_idx)
            time.sleep(1.5)
        continue

    nxt = find_node(root, text="Next")
    if nxt is not None and nxt.get("enabled") == "true":
        print("  Tapping Next...")
        tap(nxt)
        # Keep toggling proximity and light while subtest collects events
        for s in range(4):
            toggle_idx += 1
            inject_prox_and_light(toggle_idx)
            time.sleep(1.0)
        root2 = ui_dump()
        in_cts = any(PACKAGE in n.get("package", "") for n in root2.iter("node"))
        if not in_cts:
            adb("shell", "input", "keyevent", "KEYCODE_BACK")
            time.sleep(2)
        continue

    time.sleep(1.5)

inject_prox_and_light(1)  # restore proximity=5, light=500

if not overall_done:
    raise RuntimeError("Sensor Batching Manual Tests did not reach Pass")

export_and_verify(TEST_NAME)
screenshot("export_done")
