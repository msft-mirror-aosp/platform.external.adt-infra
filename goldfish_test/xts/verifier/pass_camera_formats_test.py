#!/usr/bin/env python3
"""
Camera Formats Test (CAMERA section)

UI Flow (CameraFormatsActivity.java):
1. Launch CtsVerifier and navigate to 'Camera Formats'.
2. Dismiss any initial Info dialog ("OK" button) if shown.
3. For each camera in `cameras_selection` (`R.id.cameras_selection`):
   - Select the camera and wait briefly for the initial preview frame callback to mark the initial
     `(camera, resolution, format)` combination as tested.
   - Repeatedly tap 'Next' (`R.id.next_button`), which calls `setUntestedCombination()` and
     `startPreview()`.
   - When `mTestedCombinations.size() == mAllCombinationsSize`, `setPassButtonEnabled(true)` is
     called.
   - When clicking 'Next' no longer changes the selected resolution/format pair, all combinations
     for the current camera are complete; advance to the next camera.
4. Once `pass_button` is enabled, tap Pass and export/verify the test results.
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
    tap_pass,
    ui_dump,
)

TEST_NAME = "Camera Formats"
set_screenshot_dir("camera_formats_test")


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


def get_spinner_text(root, spinner_res_id):
    """Return text of child TextView inside the specified spinner node."""
    spinner = find_node(root, resource_id=spinner_res_id)
    if spinner is None:
        return ""
    for child in spinner.iter("node"):
        txt = child.attrib.get("text", "")
        if txt:
            return txt
    return ""


def get_camera_options():
    """Return list of camera names from the cameras_selection spinner."""
    root = ui_dump()
    spinner = find_node(
        root, resource_id="com.android.cts.verifier:id/cameras_selection"
    )
    if spinner is None:
        return []
    tap(spinner)
    time.sleep(1)
    root = ui_dump()
    options = []
    for n in root.iter("node"):
        txt = n.attrib.get("text", "")
        if txt.startswith("Camera "):
            options.append(txt)
    if options:
        first_node = find_node(root, text=options[0])
        if first_node is not None:
            tap(first_node)
            time.sleep(1)
    return options


def select_spinner_option(spinner_res_id, option_text):
    """Open spinner and select the item matching option_text."""
    root = ui_dump()
    spinner = find_node(root, resource_id=spinner_res_id)
    if spinner is not None:
        tap(spinner)
        time.sleep(1)
        root = ui_dump()
        item = find_node(root, text=option_text)
        if item is not None:
            tap(item)
            time.sleep(1.5)


def complete_format_combinations():
    """Iterate through all cameras and tap Next until all format combinations are tested."""
    cameras = get_camera_options()
    print(f"  Found camera options: {cameras}")

    for cam in cameras:
        print(f"  Testing {cam}...")
        select_spinner_option("com.android.cts.verifier:id/cameras_selection", cam)
        time.sleep(1)

        prev_combo = None
        unchanged_count = 0
        for step in range(40):
            root = ui_dump()
            pass_btn = find_node(root, content_desc="Pass")
            if pass_btn is None:
                pass_btn = find_node(
                    root, resource_id="com.android.cts.verifier:id/pass_button"
                )
            if pass_btn is not None and pass_btn.attrib.get("enabled") == "true":
                print("  Pass button is enabled!")
                return pass_btn

            res_txt = get_spinner_text(
                root, "com.android.cts.verifier:id/resolution_selection"
            )
            fmt_txt = get_spinner_text(
                root, "com.android.cts.verifier:id/format_selection"
            )
            curr_combo = (res_txt, fmt_txt)
            print(f"    {cam} step {step}: {curr_combo}")

            if curr_combo == prev_combo:
                unchanged_count += 1
                if unchanged_count >= 2:
                    print(f"    All combinations for {cam} completed.")
                    break
            else:
                unchanged_count = 0
                prev_combo = curr_combo

            next_btn = find_node(
                root, resource_id="com.android.cts.verifier:id/next_button"
            )
            if next_btn is not None:
                tap(next_btn)
                time.sleep(1.0)

    root = ui_dump()
    pass_btn = find_node(root, content_desc="Pass")
    if pass_btn is None:
        pass_btn = find_node(
            root, resource_id="com.android.cts.verifier:id/pass_button"
        )
    if pass_btn is not None and pass_btn.attrib.get("enabled") == "true":
        return pass_btn

    raise TimeoutError(
        "Pass button did not become enabled after completing Camera Formats combinations"
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

    print("Completing Camera Formats combinations...")
    pass_btn = complete_format_combinations()
    screenshot("pass_enabled")

    print("Tapping Pass...")
    tap_pass(pass_btn)
    screenshot("pass_tapped")

    export_and_verify(TEST_NAME)
    screenshot("export_done")


if __name__ == "__main__":
    main()
