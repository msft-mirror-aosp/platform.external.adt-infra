#!/usr/bin/env python3
"""
Camera Orientation Test (CAMERA section)

UI Flow:
1. Launch CtsVerifier and navigate to 'Camera Orientation'.
2. `CameraOrientationActivity` runs through `mNumCameras * 4` stages (4 orientations per camera:
   0, 90, 180, 270 degrees).
3. In each stage:
   a. Dismiss any initial Info dialog ("OK" button) if shown.
   b. Wait for `take_picture_button` (`R.id.take_picture_button`) to become enabled once preview starts.
   c. Tap `take_picture_button` to capture a photo.
   d. Wait for `pass_button` (`R.id.pass_button`) to become enabled after `onPictureTaken`.
   e. Tap `pass_button`, which either launches the next stage or completes the test and returns to
      the main CtsVerifier list after the final stage.
4. Export and verify the test results.
"""

import os
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.append(SCRIPT_DIR)

from cts_common import (
    export_and_verify,
    find_node,
    navigate_to,
    screenshot,
    set_screenshot_dir,
    setup,
    tap,
    ui_dump,
)

TEST_NAME = "Camera Orientation"
set_screenshot_dir("camera_orientation_test")


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


def run_orientation_stages():
    """Run all orientation stages across all cameras until returning to main CtsVerifier list."""
    stage = 0
    while stage < 20:
        dismiss_initial_dialogs()

        # Wait for take_picture_button to become enabled (or return to main list after all stages)
        take_btn = None
        for attempt in range(20):
            root = ui_dump()
            ok_btn = find_node(root, text="OK")
            if ok_btn is not None:
                tap(ok_btn)
                time.sleep(1)
                continue
            take_btn = find_node(
                root, resource_id="com.android.cts.verifier:id/take_picture_button"
            )
            if take_btn is not None and take_btn.attrib.get("enabled") == "true":
                break
            # Only treat android:id/list as completion once at least 8 stages (2 cameras x 4 orientations)
            # have completed, or after waiting several seconds for the next stage activity to launch.
            if (
                stage >= 8
                and attempt >= 2
                and find_node(root, resource_id="android:id/list") is not None
                and take_btn is None
            ):
                print(
                    f"  Completed all {stage} orientation stages; returned to main CtsVerifier list."
                )
                return
            time.sleep(1)

        if take_btn is None:
            root = ui_dump()
            if (
                stage >= 4
                and find_node(root, resource_id="android:id/list") is not None
            ):
                print(
                    f"  Completed all {stage} orientation stages; returned to main CtsVerifier list."
                )
                return

        if take_btn is None or take_btn.attrib.get("enabled") != "true":
            print(
                f"  Stage {stage}: take_picture_button not enabled yet, toggling onPause/onResume to recover camera preview..."
            )
            from cts_common import adb

            adb("shell", "input", "keyevent", "KEYCODE_APP_SWITCH", check=False)
            time.sleep(1.5)
            adb("shell", "input", "keyevent", "KEYCODE_APP_SWITCH", check=False)
            time.sleep(3)
            for _ in range(15):
                root = ui_dump()
                take_btn = find_node(
                    root, resource_id="com.android.cts.verifier:id/take_picture_button"
                )
                if take_btn is not None and take_btn.attrib.get("enabled") == "true":
                    break
                time.sleep(1)

        if take_btn is None or take_btn.attrib.get("enabled") != "true":
            raise TimeoutError(f"take_picture_button not enabled in stage {stage}")

        time.sleep(1.5)
        print(f"  Stage {stage}: tapping Take Photo...")
        tap(take_btn)
        time.sleep(2.5)

        # Wait for pass_button to become enabled
        pass_btn = None
        for _ in range(15):
            root = ui_dump()
            pass_btn = find_node(root, content_desc="Pass")
            if pass_btn is None:
                pass_btn = find_node(
                    root, resource_id="com.android.cts.verifier:id/pass_button"
                )
            if pass_btn is not None and pass_btn.attrib.get("enabled") == "true":
                break
            time.sleep(1)

        if pass_btn is None or pass_btn.attrib.get("enabled") != "true":
            raise TimeoutError(
                f"pass_button not enabled after taking photo in stage {stage}"
            )

        print(f"  Stage {stage}: tapping Pass to advance...")
        tap(pass_btn)
        stage += 1
        time.sleep(2)


def main():
    setup()
    print("Navigating to test...")
    screenshot("navigating_to_test")
    navigate_to(TEST_NAME)
    time.sleep(2)
    screenshot("activity_launched")

    print("Running Camera Orientation stages...")
    run_orientation_stages()
    screenshot("all_stages_completed")

    export_and_verify(TEST_NAME)
    screenshot("export_done")


if __name__ == "__main__":
    main()
