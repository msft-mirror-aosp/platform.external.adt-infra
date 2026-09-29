#!/usr/bin/env python3
"""
Camera Bokeh Test (CAMERA section)

UI Flow:
1. Launch CtsVerifier and navigate to 'Camera Bokeh'.
2. Dismiss any initial Info dialog ("OK" button) if shown.
3. If the device has no supported bokeh modes, `CameraBokehActivity` immediately enables the Pass
   button (`R.id.pass_button`).
4. Otherwise, for each camera listed in the `cameras_selection` spinner (`R.id.cameras_selection`),
   select the camera and tap 'Next' (`R.id.next_button`) to step through all bokeh mode
   combinations (`STILL_CAPTURE` and `CONTINUOUS`, both `PREVIEW` and `STILL_CAPTURE`).
5. Once all combinations for all cameras are tested, `setPassButtonEnabled(true)` is called.
6. Tap Pass and export/verify the test results.
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

TEST_NAME = "Camera Bokeh"
set_screenshot_dir("camera_bokeh_test")


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
    # Close dropdown by selecting first option if open
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


def complete_bokeh_combinations():
    """Iterate through all cameras and their bokeh combinations until Pass button is enabled."""
    root = ui_dump()
    pass_btn = find_node(root, content_desc="Pass")
    if pass_btn is None:
        pass_btn = find_node(
            root, resource_id="com.android.cts.verifier:id/pass_button"
        )
    if pass_btn is not None and pass_btn.attrib.get("enabled") == "true":
        print("  Pass button is already enabled!")
        return pass_btn

    cameras = get_camera_options()
    print(f"  Found bokeh camera options: {cameras}")

    for cam in cameras:
        print(f"  Testing {cam}...")
        select_spinner_option("com.android.cts.verifier:id/cameras_selection", cam)
        for step in range(8):
            root = ui_dump()
            pass_btn = find_node(root, content_desc="Pass")
            if pass_btn is None:
                pass_btn = find_node(
                    root, resource_id="com.android.cts.verifier:id/pass_button"
                )
            if pass_btn is not None and pass_btn.attrib.get("enabled") == "true":
                print("  Pass button is enabled!")
                return pass_btn

            next_btn = find_node(
                root, resource_id="com.android.cts.verifier:id/next_button"
            )
            if next_btn is not None and next_btn.attrib.get("enabled") == "true":
                print(f"    {cam} step {step}: tapping Next...")
                tap(next_btn)
                time.sleep(1.5)
            else:
                break

    root = ui_dump()
    pass_btn = find_node(root, content_desc="Pass")
    if pass_btn is None:
        pass_btn = find_node(
            root, resource_id="com.android.cts.verifier:id/pass_button"
        )
    if pass_btn is not None and pass_btn.attrib.get("enabled") == "true":
        return pass_btn

    raise TimeoutError(
        "Pass button did not become enabled after completing Camera Bokeh combinations"
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

    print("Completing Camera Bokeh combinations...")
    pass_btn = complete_bokeh_combinations()
    screenshot("pass_enabled")

    print("Tapping Pass...")
    tap_pass(pass_btn)
    screenshot("pass_tapped")

    export_and_verify(TEST_NAME)
    screenshot("export_done")


if __name__ == "__main__":
    main()
