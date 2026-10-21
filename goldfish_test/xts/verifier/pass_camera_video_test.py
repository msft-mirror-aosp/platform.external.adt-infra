#!/usr/bin/env python3
"""
Camera Video Test (CAMERA section)

UI Flow:
1. Launch CtsVerifier and navigate to 'Camera Video'.
2. Dismiss any initial Info dialog ("OK" button) if shown.
3. For each camera in `cameras_selection` (`R.id.cameras_selection`), select the camera and tap
   `next_button` (`R.id.next_button`), which automatically selects the next untested video resolution,
   records a 3-second video (`VIDEO_LENGTH = 3000ms`), plays it back, and re-enables `record_button`
   (`R.id.record_button`).
4. Once all resolutions for all cameras are tested (`mUntestedCombinations.isEmpty() &&
   mUntestedCameras.isEmpty()`), `pass_button` becomes enabled.
5. Tap Pass and export/verify the test results.
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

TEST_NAME = "Camera Video"
set_screenshot_dir("camera_video_test")


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


def wait_for_recording_and_playback():
    """Wait until record_button becomes enabled again after recording + playback (~7s)."""
    time.sleep(4.5)
    for _ in range(15):
        root = ui_dump()
        rec_btn = find_node(
            root, resource_id="com.android.cts.verifier:id/record_button"
        )
        if rec_btn is not None and rec_btn.attrib.get("enabled") == "true":
            return
        time.sleep(1)


def complete_video_combinations():
    """Test all video resolutions across all cameras until Pass button is enabled."""
    cameras = get_camera_options()
    print(f"  Found camera options: {cameras}")

    for cam in cameras:
        print(f"  Testing {cam}...")
        select_spinner_option("com.android.cts.verifier:id/cameras_selection", cam)

        for step in range(15):
            root = ui_dump()
            pass_btn = find_node(root, content_desc="Pass")
            if pass_btn is None:
                pass_btn = find_node(
                    root, resource_id="com.android.cts.verifier:id/pass_button"
                )
            if pass_btn is not None and pass_btn.attrib.get("enabled") == "true":
                print("  Pass button is enabled!")
                return pass_btn

            status_node = find_node(
                root, resource_id="com.android.cts.verifier:id/status_label"
            )
            status_text = (
                status_node.attrib.get("text", "") if status_node is not None else ""
            )
            if (
                f"{cam}," not in status_text.split("Untested combinations:")[-1]
                and step > 0
            ):
                print(f"  All {cam} combinations completed.")
                break

            next_btn = find_node(
                root, resource_id="com.android.cts.verifier:id/next_button"
            )
            if next_btn is None:
                raise RuntimeError("next_button not found in CameraVideoActivity")

            print(
                f"    {cam} step {step}: tapping Next (records 3s video & plays back)..."
            )
            tap(next_btn)
            wait_for_recording_and_playback()

    root = ui_dump()
    pass_btn = find_node(root, content_desc="Pass")
    if pass_btn is None:
        pass_btn = find_node(
            root, resource_id="com.android.cts.verifier:id/pass_button"
        )
    if pass_btn is not None and pass_btn.attrib.get("enabled") == "true":
        return pass_btn

    raise TimeoutError(
        "Pass button did not become enabled after completing Camera Video combinations"
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

    print("Completing Camera Video combinations...")
    pass_btn = complete_video_combinations()
    screenshot("pass_enabled")

    print("Tapping Pass...")
    tap_pass(pass_btn)
    screenshot("pass_tapped")

    export_and_verify(TEST_NAME)
    screenshot("export_done")


if __name__ == "__main__":
    main()
