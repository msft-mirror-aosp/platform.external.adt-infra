#!/usr/bin/env python3
"""
Magnetic Field Measurement Tests automation script.
Injects calibrated and uncalibrated magnetic-field values (30:30:15 uT, magnitude 45 uT,
zero bias) to satisfy testNorm, testOffset, testStandardDeviation, and
testCalibratedAndUncalibrated.
"""

import subprocess
import time
from cts_common import (
    PACKAGE,
    adb,
    export_and_verify,
    find_node,
    get_focused_activity,
    navigate_to,
    screenshot,
    set_screenshot_dir,
    setup,
    tap,
    ui_dump,
)

TEST_NAME = "Magnetic Field Measurement Tests"
set_screenshot_dir("sensors_magnetic_field_measurement_tests")

MAG_VEC = (30.0, 30.0, 15.0)  # norm = sqrt(900 + 900 + 225) = 45.0 uT


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


def inject_mag(x=30.0, y=30.0, z=15.0):
    val = f"{x}:{y}:{z}"
    subprocess.run(
        ["adb", "-e", "emu", "sensor", "set", "magnetic-field", val],
        capture_output=True,
    )
    uncal_val = f"{x}:{y}:{z}:0:0:0"
    subprocess.run(
        ["adb", "-e", "emu", "sensor", "set", "magnetic-field-uncalibrated", uncal_val],
        capture_output=True,
    )


last_next_node = None


def safe_ui_dump():
    try:
        return ui_dump(retries=3)
    except RuntimeError:
        # calibrateMagnetometer() calls clearText() + logMessage() on every sensor event,
        # preventing uiautomator from observing an idle UI tree until Next is tapped.
        print(
            "  [safe_ui_dump] UI busy (calibrateMagnetometer active); tapping Next..."
        )
        if last_next_node is not None:
            tap(last_next_node)
        else:
            adb("shell", "input", "tap", "720", "3008")
            adb("shell", "input", "tap", "540", "2276")
        time.sleep(2)
        return ui_dump()


setup()
sensor_settings()
inject_mag(*MAG_VEC)
screenshot("launched")

root = safe_ui_dump()
close_btn = find_node(root, text="Close")
if close_btn is not None:
    tap(close_btn)
    time.sleep(2)

navigate_to(TEST_NAME)
time.sleep(2)
screenshot("test_opened")

root = safe_ui_dump()
ok = find_node(root, text="OK")
if ok is not None and ok.get("enabled") == "true":
    tap(ok)
    time.sleep(2)

overall_done = False
next_count = 0
for _ in range(90):
    inject_mag(*MAG_VEC)
    focused = get_focused_activity()
    if "com.android.settings" in focused:
        print(f"  In Settings ({focused}); pressing BACK...")
        adb("shell", "input", "keyevent", "KEYCODE_BACK")
        time.sleep(2)
        continue

    root = safe_ui_dump()

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
        inject_mag(*MAG_VEC)
        tap(retry_btn)
        time.sleep(2)
        continue

    nxt = find_node(root, text="Next")
    if nxt is not None and nxt.get("enabled") == "true":
        last_next_node = nxt
        texts = " ".join(n.get("text", "") for n in root.iter("node")).lower()
        if "testcalibratedanduncalibrated" in texts or next_count >= 7:
            # Before Next (#8), restoreInitialState() expects Location restored to OFF (0).
            adb("shell", "settings", "put", "secure", "location_mode", "0")
            time.sleep(1)
        next_count += 1
        print(f"  Tapping Next (#{next_count})...")
        tap(nxt)
        time.sleep(2)
        if next_count == 1:
            # Next (#1) completes SensorFeaturesDeactivator.requestDeactivationOfFeatures()
            # (which required location_mode=0). Immediately after, activitySetUp() calls
            # requestToSetLocationMode(true) and pauses at Next (#2).
            print("  Enabling location_mode=3 for activitySetUp()...")
            adb("shell", "settings", "put", "secure", "location_mode", "3")
            time.sleep(1)
            next_count += 1
            print(
                f"  Tapping Next (#{next_count}) to satisfy requestToSetLocationMode(true)..."
            )
            tap(nxt)
            time.sleep(2)
            # Now calibrateMagnetometer() is at waitForUserToContinue() #1 (001e).
            next_count += 1
            print(
                f"  Tapping Next (#{next_count}) to start calibrateMagnetometer() 50Hz listener..."
            )
            tap(nxt)
            time.sleep(2)
            inject_mag(*MAG_VEC)
            # Now calibrateMagnetometer() is at waitForUserToContinue() #2 (002e).
            next_count += 1
            print(
                f"  Tapping Next (#{next_count}) to complete calibrateMagnetometer()..."
            )
            tap(nxt)
            time.sleep(2)
        continue

    time.sleep(2)

adb("shell", "settings", "put", "secure", "location_mode", "0")

if not overall_done:
    raise RuntimeError("Magnetic Field Measurement Tests did not reach Pass")

export_and_verify(TEST_NAME)
screenshot("export_done")
