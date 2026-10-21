#!/usr/bin/env python3
"""
Audio Descriptor Test (AUDIO section)

UI Flow:
1. Launch CtsVerifier and navigate to 'Audio Descriptor Test' (AudioDescriptorActivity).
2. Dismiss the initial Info dialog ("OK" button) if shown.
3. Tap 'Run Test' (resource-id="com.android.cts.verifier:id/audioDescriptorRunTestBtn").
4. AudioDescriptorActivity checks HDMI support (none on emulator), queries AudioManager HAL version,
   and validates any reported AudioDescriptors (none or valid on emulator), marking the test as passed.
5. Wait for the Pass button to become enabled, tap Pass, and export/verify results.
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
    wait_for,
)

TEST_NAME = "Audio Descriptor Test"
set_screenshot_dir("audio_descriptor_test")


def dismiss_initial_dialogs():
    """Dismiss any initial OK info dialog if present."""
    for _ in range(3):
        root = ui_dump()
        ok_btn = find_node(root, text="OK")
        if ok_btn is not None:
            print("  Dismissing info dialog via 'OK' button...")
            tap(ok_btn)
            time.sleep(1)
        else:
            break


def run_test_and_wait_for_pass(max_attempts=3):
    """Tap 'Run Test' and wait for the Pass button to become enabled."""
    for attempt in range(1, max_attempts + 1):
        print(f"Running Audio Descriptor Test (attempt {attempt}/{max_attempts})...")
        run_btn = wait_for(
            resource_id="com.android.cts.verifier:id/audioDescriptorRunTestBtn",
            timeout=10,
        )
        screenshot(f"tapping_run_attempt_{attempt}")
        tap(run_btn)

        deadline = time.time() + 10
        while time.time() < deadline:
            root = ui_dump()
            status_node = find_node(
                root,
                resource_id="com.android.cts.verifier:id/audioDescriptorTestStatusLbl",
            )
            if status_node is not None and status_node.attrib.get("text"):
                print(f"  Status text: {status_node.attrib.get('text')!r}")

            pass_btn = find_node(root, content_desc="Pass")
            if pass_btn is None:
                pass_btn = find_node(
                    root, resource_id="com.android.cts.verifier:id/pass_button"
                )

            if pass_btn is not None and pass_btn.attrib.get("enabled") == "true":
                print("  Pass button is enabled!")
                return pass_btn

            time.sleep(1)

        print(
            f"  Attempt {attempt} did not enable Pass button within timeout, retrying..."
        )

    raise TimeoutError(
        "Pass button did not become enabled after running Audio Descriptor Test"
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

    pass_btn = run_test_and_wait_for_pass()
    screenshot("test_passed")

    print("Tapping Pass...")
    tap_pass(pass_btn)
    screenshot("pass_tapped")

    export_and_verify(TEST_NAME)
    screenshot("export_done")


if __name__ == "__main__":
    main()
