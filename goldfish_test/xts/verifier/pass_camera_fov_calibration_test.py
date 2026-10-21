#!/usr/bin/env python3
"""
Camera FOV Calibration Test (CAMERA section)

UI Flow:
1. Launch CtsVerifier and navigate to 'Camera FOV Calibration'.
2. Dismiss any initial Info dialog ("OK" button) if shown.
3. For each camera resolution in the test:
   - When the calibration prompt (`R.id.camera_fov_tap_to_take_photo`, text "Tap to calibrate")
     is displayed, tap in the middle of the screen (`(540, 1200)`) to capture/calibrate.
   - When the calibration slider screen appears with the 'Done' button (`R.id.camera_fov_fov_done`),
     tap 'Done' to advance to the next untested camera resolution.
4. Once all resolutions for all cameras have been calibrated and 'Done' is tapped on the final
   resolution, the activity automatically marks the test result as PASSED and returns to the
   main CtsVerifier test list.
5. Export and verify the test results in `test_result.xml`.
"""

import os
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.append(SCRIPT_DIR)

from cts_common import (
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

TEST_NAME = "Camera FOV Calibration"
set_screenshot_dir("camera_fov_calibration_test")


def dismiss_initial_dialogs():
    """Dismiss any initial OK info dialog if present."""
    for _ in range(3):
        root = ui_dump()
        ok_btn = find_node(root, text="OK")
        if ok_btn is not None:
            print("  Dismissing dialog via 'OK' button...")
            tap(ok_btn)
            time.sleep(1)
        else:
            break


def run_fov_calibration_loop(max_steps=50):
    """Loop through all camera resolutions by tapping middle of screen and 'Done'."""
    for step in range(max_steps):
        root = ui_dump()

        # Check if we have returned to the main CtsVerifier list activity (all resolutions done)
        if find_node(root, resource_id="android:id/list") is not None:
            print(
                "  All FOV resolutions calibrated; returned to CtsVerifier test list!"
            )
            return

        # Dismiss any dialog if present
        ok_btn = find_node(root, text="OK")
        if ok_btn is not None:
            tap(ok_btn)
            time.sleep(1)
            continue

        # If 'Done' button is visible on the FOV slider screen, tap it
        done_btn = find_node(
            root, resource_id="com.android.cts.verifier:id/camera_fov_fov_done"
        )
        if done_btn is not None:
            print(f"  Step {step}: tapping 'Done'...")
            tap(done_btn)
            time.sleep(1.5)
            continue

        # If 'Tap to calibrate' prompt is visible, tap in the middle of the screen
        cal_prompt = find_node(
            root, resource_id="com.android.cts.verifier:id/camera_fov_tap_to_take_photo"
        )
        if cal_prompt is not None:
            res_node = find_node(root, resource_id="android:id/text1")
            res_label = res_node.attrib.get("text", "") if res_node is not None else ""
            print(
                f"  Step {step} ({res_label}): tapping middle of screen (540, 1200) to calibrate..."
            )
            adb("shell", "input", "tap", "540", "1200", check=False)
            time.sleep(2.5)
            continue

        time.sleep(1)

    raise TimeoutError(
        "Did not complete all Camera FOV Calibration resolutions within max_steps"
    )


def main():
    setup()
    print("Navigating to test...")
    screenshot("navigating_to_test")
    navigate_to(TEST_NAME)
    time.sleep(2)
    screenshot("activity_launched")

    dismiss_initial_dialogs()
    screenshot("dialogs_dismissed")

    print("Running Camera FOV Calibration loop...")
    run_fov_calibration_loop()
    screenshot("calibration_done")

    export_and_verify(TEST_NAME)
    screenshot("export_done")


if __name__ == "__main__":
    main()
