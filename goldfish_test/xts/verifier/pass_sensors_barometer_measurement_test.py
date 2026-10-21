#!/usr/bin/env python3
"""
Barometer Measurement Test automation script.
On Goldfish emulator, sensor.barometer.high_quality.implemented is not set, so
BarometerMeasurementTestActivity skips all subtests and enables Pass after setup.
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

TEST_NAME = "Barometer Measurement Test"
set_screenshot_dir("sensors_barometer_measurement_test")


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


setup()
sensor_settings()
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
for _ in range(30):
    root = ui_dump()
    pass_btn = find_node(root, content_desc="Pass") or find_node(root, text="Pass")
    if pass_btn is not None and pass_btn.get("enabled") == "true":
        print("Tapping overall Pass...")
        tap(pass_btn)
        time.sleep(2)
        screenshot("pass_tapped")
        overall_done = True
        break

    nxt = find_node(root, text="Next")
    if nxt is not None and nxt.get("enabled") == "true":
        tap(nxt)
        time.sleep(2)
        root2 = ui_dump()
        in_cts = any(PACKAGE in n.get("package", "") for n in root2.iter("node"))
        if not in_cts:
            adb("shell", "input", "keyevent", "KEYCODE_BACK")
            time.sleep(2)
        continue

    time.sleep(2)

if not overall_done:
    raise RuntimeError("Barometer Measurement Test did not reach Pass")

export_and_verify(TEST_NAME)
screenshot("export_done")
