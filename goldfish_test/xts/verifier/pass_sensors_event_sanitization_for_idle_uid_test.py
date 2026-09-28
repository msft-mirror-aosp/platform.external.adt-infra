#!/usr/bin/env python3
"""
Event sanitization for idle UID test automation script.
Runs `adb shell cmd sensorservice set-uid-state com.android.cts.verifier idle`
when prompted in activitySetUp(), steps through Next prompts while keeping sensors
stationary during the 30s idle UID verification window, then runs
`adb shell cmd sensorservice reset-uid-state com.android.cts.verifier` in
activityCleanUp() and taps Pass.
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

TEST_NAME = "Event sanitization for idle UID test"
set_screenshot_dir("sensors_event_sanitization_for_idle_uid_test")


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
    adb("shell", "cmd", "sensorservice", "reset-uid-state", PACKAGE, check=False)


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
uid_set_idle = False
uid_reset = False

try:
    for _ in range(90):
        root = ui_dump()
        pass_btn = find_node(root, content_desc="Pass") or find_node(root, text="Pass")
        if pass_btn is not None and pass_btn.get("enabled") == "true":
            print("Tapping overall Pass...")
            tap(pass_btn)
            time.sleep(2)
            screenshot("pass_tapped")
            overall_done = True
            break

        fail_btn = find_node(root, text="Fail")
        if fail_btn is not None and fail_btn.get("enabled") == "true":
            raise AssertionError("Event sanitization for idle UID test ended with Fail")

        nxt = find_node(root, text="Next")
        if nxt is not None and nxt.get("enabled") == "true":
            texts = " ".join(n.get("text", "") for n in root.iter("node"))
            if "reset-uid-state" in texts and not uid_reset:
                print(f"  Running: cmd sensorservice reset-uid-state {PACKAGE}")
                adb("shell", "cmd", "sensorservice", "reset-uid-state", PACKAGE)
                uid_reset = True
                time.sleep(1)
            elif "set-uid-state" in texts and not uid_set_idle:
                print(f"  Running: cmd sensorservice set-uid-state {PACKAGE} idle")
                adb("shell", "cmd", "sensorservice", "set-uid-state", PACKAGE, "idle")
                uid_set_idle = True
                time.sleep(1)

            print("  Tapping Next...")
            tap(nxt)
            time.sleep(2)
            root2 = ui_dump()
            in_cts = any(PACKAGE in n.get("package", "") for n in root2.iter("node"))
            if not in_cts:
                adb("shell", "input", "keyevent", "KEYCODE_BACK")
                time.sleep(2)
            continue

        time.sleep(2)
finally:
    adb("shell", "cmd", "sensorservice", "reset-uid-state", PACKAGE, check=False)

if not overall_done:
    raise RuntimeError("Event sanitization for idle UID test did not reach Pass")

export_and_verify(TEST_NAME)
screenshot("export_done")
