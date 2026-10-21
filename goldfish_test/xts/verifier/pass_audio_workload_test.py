#!/usr/bin/env python3
"""
Audio Workload Test (AUDIO section)

UI Flow:
1. Launch CtsVerifier and navigate to 'Audio Workload Test'.
2. Dismiss any initial Info dialog ("OK" button) if shown.
3. Tap the 'Start' button (resource-id="com.android.cts.verifier:id/button_start") to run the
   3-second audio CPU workload round (`TARGET_DURATION_MS = 3000ms`), then tap 'Stop'
   (resource-id="com.android.cts.verifier:id/button_stop") so `hasRun()` is recorded.
4. On devices/emulators where `MEDIA_PERFORMANCE_CLASS < MPC_CINNAMON_BUN` (or where the
   workload threshold passes), `updatePassButtonState()` enables the Pass button
   (`R.id.pass_button`).
5. Wait for the Pass button to be enabled, tap Pass, and export/verify the test results.
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

TEST_NAME = "Audio Workload Test"
set_screenshot_dir("audio_workload_test")


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


def run_workload_and_wait_for_pass(timeout=30):
    """Run one workload iteration (Start -> wait 4s -> Stop) and wait for Pass button."""
    root = ui_dump()
    start_btn = find_node(root, resource_id="com.android.cts.verifier:id/button_start")
    if start_btn is not None and start_btn.attrib.get("enabled") == "true":
        print("  Tapping 'Start' button to run audio workload round...")
        tap(start_btn)
        time.sleep(4)
        root = ui_dump()
        stop_btn = find_node(
            root, resource_id="com.android.cts.verifier:id/button_stop"
        )
        if stop_btn is not None and stop_btn.attrib.get("enabled") == "true":
            print("  Tapping 'Stop' button...")
            tap(stop_btn)
            time.sleep(1)

    deadline = time.time() + timeout
    while time.time() < deadline:
        root = ui_dump()
        pass_btn = find_node(root, content_desc="Pass")
        if pass_btn is None:
            pass_btn = find_node(
                root, resource_id="com.android.cts.verifier:id/pass_button"
            )

        if pass_btn is not None and pass_btn.attrib.get("enabled") == "true":
            print("  Pass button is enabled!")
            return pass_btn

        time.sleep(1)

    raise TimeoutError(
        "Timed out waiting for enabled Pass button in Audio Workload Test"
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

    print("Running workload test and waiting for Pass button...")
    pass_btn = run_workload_and_wait_for_pass()
    screenshot("pass_enabled")

    print("Tapping Pass...")
    tap_pass(pass_btn)
    screenshot("pass_tapped")

    export_and_verify(TEST_NAME)
    screenshot("export_done")


if __name__ == "__main__":
    main()
