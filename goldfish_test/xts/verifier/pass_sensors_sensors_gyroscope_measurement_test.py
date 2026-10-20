#!/usr/bin/env python3
"""
Gyroscope Measurement Test
Injects a constant clockwise angular-velocity into the emulator's Goldfish gyroscope
sensor for the testCalibratedAndUncalibrated sub-test, which asks the user to "keep
rotating the device clockwise."  In Android device coordinates (Z+ out of screen),
clockwise rotation viewed from above is negative angular velocity around Z.

Flow:
  1. Configure system settings (airplane, brightness, auto-rotate, stay-awake, location)
  2. setup() — reinstall + launch CTS Verifier
  3. navigate_to "SENSORS" → navigate_to TEST_NAME
  4. Dismiss intro OK dialog if present
  5. Loop: tap setup Next → detect sub-test → inject gyroscope → tap Next → wait for result
  6. Tap final Pass
  7. Export ZIP and verify test_result.xml
"""

import os, re, time, xml.etree.ElementTree as ET, zipfile, subprocess
from cts_common import screenshot, set_screenshot_dir
from cts_common import (
    PACKAGE, adb, setup, navigate_to,
    ui_dump, find_node, find_node_containing, tap,
    export_and_verify
)

TEST_NAME  = "Gyroscope Measurement Test"
set_screenshot_dir("gyroscope_measurement_test")

OUTPUT_DIR = os.environ.get("CTS_OUTPUT_DIR", "/tmp")

# Gyroscope injection: rad/s in device frame (X+, Y+, Z+ toward user)
# Static sub-tests: 0 rad/s (Integration check expects ~0 deg drift)
# Rotation sub-tests: 2π/10 ≈ 0.6283 rad/s so 10s × 0.6283 × (180/π) ≈ 360deg
# All rotation tests check axis=0 (X) expecting 360deg integration.
# Static sub-tests expect ~0 deg drift; rotation sub-tests expect ~360 deg in ~10s.
# Measurement window ≈ 10s → ω = 2π/10 ≈ 0.6283 rad/s per axis.
# testRotateBottomSide checks axis=0 (X); testRotateClockwise checks axis=2 (Z).
GYRO_ORIENTATIONS = {
    "testCalibratedAndUncalibrated": (0.0,    0.0,    0.0   ),
    "testDeviceStatic":              (0.0,    0.0,    0.0   ),
    "testRotateBottomSide":          (0.6283, 0.0,    0.0   ),
    "testRotateTopSide":             (-0.6283, 0.0,   0.0   ),  # -X = opposite of BottomSide
    "testRotateLeftSide":            (0.0,   -0.6283, 0.0   ),  # -Y = left side up
    "testRotateRightSide":           (0.0,    0.6283, 0.0   ),  # +Y = right side up
    "testRotateFaceUp":              (0.0,    0.0,    0.6283),
    "testRotateFaceDown":            (0.0,    0.0,    0.6283),
    "testRotateClockwise":           (0.0,    0.0,   -0.6283),  # -Z = clockwise from front
    "testRotateCounterClockwise":    (0.0,    0.0,    0.6283),  # +Z = counterclockwise
}
DEFAULT_GYRO = (0.0, 0.0, 0.0)




def sensor_settings():
    subprocess.run(["adb", "shell", "am", "broadcast", "-a",
                    "android.intent.action.AIRPLANE_MODE", "--ez", "state", "true"],
                   capture_output=True)
    adb("shell", "settings", "put", "global", "airplane_mode_on", "1")
    adb("shell", "settings", "put", "system", "screen_brightness_mode", "0")
    adb("shell", "settings", "put", "system", "accelerometer_rotation", "0")
    adb("shell", "settings", "put", "global", "stay_on_while_plugged_in", "0")
    adb("shell", "settings", "put", "secure", "location_mode", "0")


def inject_gyro(x, y, z):
    val = f"{x}:{y}:{z}"
    subprocess.run(["adb", "-e", "emu", "sensor", "set", "gyroscope", val],
                   capture_output=True)
    # Uncalibrated = calibrated + bias; inject with zero bias so calibrated ≈ uncalibrated
    uncal_val = f"{x}:{y}:{z}:0:0:0"
    subprocess.run(["adb", "-e", "emu", "sensor", "set", "gyroscope-uncalibrated", uncal_val],
                   capture_output=True)


def current_sub_test(root):
    last = None
    for n in root.iter("node"):
        t = n.get("text", "")
        if re.match(r"^test[A-Za-z]", t):
            last = t
    return last


def wait_for_sub_test_result(sub_name, x, y, z, max_wait=660):
    print(f"    Waiting for {sub_name!r} result (up to {max_wait}s)...")
    start = time.time()
    while time.time() - start < max_wait:
        inject_gyro(x, y, z)
        time.sleep(3)
        root = ui_dump()

        pass_btn = find_node(root, content_desc="Pass")
        if pass_btn is None:
            pass_btn = find_node(root, text="Pass")
        if pass_btn is not None and pass_btn.get("enabled") == "true":
            print(f"    >> OVERALL PASS after {time.time()-start:.0f}s")
            return "overall_pass"
        fail_btn = find_node(root, text="Fail")
        if fail_btn is not None:
            print(f"    >> OVERALL FAIL after {time.time()-start:.0f}s")
            return "overall_fail"

        retry_btn = next((n for n in root.iter("node")
                          if n.get("text", "").startswith("Retry")), None)
        if retry_btn is not None:
            print(f"    >> {sub_name!r} FAILED: {retry_btn.get('text')}")
            return "fail"

        nxt = find_node(root, text="Next")
        if nxt is not None and nxt.get("enabled") == "true":
            texts = [n.get("text", "") for n in root.iter("node")]
            try:
                idx = next(i for i, t in enumerate(texts) if t == sub_name)
                after = texts[idx + 1:]
                if "PASS" in after:
                    print(f"    >> {sub_name!r} PASSED after {time.time()-start:.0f}s!")
                    return "pass"
            except StopIteration:
                pass

    return "timeout"


def ensure_on_main_list():
    for _ in range(10):
        root = ui_dump()
        if find_node(root, content_desc="More options") is not None:
            return
        adb("shell", "input", "keyevent", "KEYCODE_BACK")
        time.sleep(1.5)
    raise RuntimeError("Could not reach main CTS Verifier list")


# ── Main ──────────────────────────────────────────────────────────────────────

setup()
sensor_settings()
inject_gyro(0.0, 0.0, 0.0)
screenshot("launched")

root = ui_dump()
close_btn = find_node(root, text="Close")
if close_btn is not None:
    print("Dismissing 'No location access' dialog...")
    tap(close_btn); time.sleep(2)

navigate_to("SENSORS")
time.sleep(2)
navigate_to(TEST_NAME)
time.sleep(2)
screenshot("test_opened")

root = ui_dump()
ok = find_node(root, text="OK")
if ok is not None and ok.get("enabled") == "true":
    print("Dismissing intro dialog...")
    tap(ok); time.sleep(2); screenshot("ok_dismissed")
    root = ui_dump()

overall_done = False
last_sub = None  # remember sub across Retry iterations (name scrolls off screen)
for outer in range(60):
    root = ui_dump()

    pass_btn = find_node(root, content_desc="Pass")
    if pass_btn is None:
        pass_btn = find_node(root, text="Pass")
    if pass_btn is not None and pass_btn.get("enabled") == "true":
        print("Tapping overall Pass...")
        tap(pass_btn); time.sleep(2); screenshot("pass_tapped")
        overall_done = True; break

    fail_btn = find_node(root, text="Fail")
    if fail_btn is not None:
        raise AssertionError("Test ended with Fail button")

    retry_btn = next((n for n in root.iter("node")
                      if n.get("text", "").startswith("Retry")), None)
    if retry_btn is not None:
        sub = current_sub_test(root) or last_sub
        gx, gy, gz = GYRO_ORIENTATIONS.get(sub, DEFAULT_GYRO)
        print(f"  Retry for {sub!r} — re-injecting and tapping Retry")
        inject_gyro(gx, gy, gz); time.sleep(1)
        tap(retry_btn); time.sleep(3)
        result = wait_for_sub_test_result(sub or "unknown", gx, gy, gz)
        if result == "overall_pass":
            root_f = ui_dump()
            pb = find_node(root_f, content_desc="Pass")
            if pb is None:
                pb = find_node(root_f, text="Pass")
            if pb is not None and pb.get("enabled") == "true":
                tap(pb); time.sleep(2); screenshot("pass_tapped")
            overall_done = True; break
        continue

    nxt = find_node(root, text="Next")
    if nxt is not None and nxt.get("enabled") == "true":
        sub = current_sub_test(root)
        if sub is not None:
            last_sub = sub
        gx, gy, gz = GYRO_ORIENTATIONS.get(sub, DEFAULT_GYRO)
        print(f"  Next enabled; sub-test={sub!r}; injecting gyro {gx}:{gy}:{gz}")
        inject_gyro(gx, gy, gz); time.sleep(0.5)
        tap(nxt); time.sleep(4)
        root2 = ui_dump()
        in_cts = any(PACKAGE in n.get("package", "") for n in root2.iter("node"))
        if not in_cts:
            adb("shell", "input", "keyevent", "KEYCODE_BACK"); time.sleep(2)
            continue
        if sub is not None:
            result = wait_for_sub_test_result(sub, gx, gy, gz)
            if result == "overall_pass":
                root_f = ui_dump()
                pb = find_node(root_f, content_desc="Pass")
                if pb is None:
                    pb = find_node(root_f, text="Pass")
                if pb is not None and pb.get("enabled") == "true":
                    tap(pb); time.sleep(2); screenshot("pass_tapped")
                overall_done = True; break
            elif result == "timeout":
                raise TimeoutError(f"Sub-test {sub!r} timed out")
        continue

    time.sleep(3)

if not overall_done:
    raise RuntimeError("Test loop exited without reaching Pass")

# Restore gyroscope to zero (stationary)
inject_gyro(0.0, 0.0, 0.0)

export_and_verify(TEST_NAME)
screenshot("export_done")
