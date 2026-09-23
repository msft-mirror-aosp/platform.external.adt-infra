#!/usr/bin/env python3
"""
Audio Cold Start Input Latency Test (AUDIO section)

UI Flow:
1. Launch CtsVerifier and navigate to 'Audio Cold Start Input Latency Test'.
2. Dismiss the initial Info dialog ("OK" button) if shown.
3. Tap the 'Run' button (resource-id="com.android.cts.verifier:id/coldstart_run_btn").
4. The test opens an audio input stream and measures cold start latency until the first
   callback arrives. When latency <= 500ms (LATENCY_MS_MUST), the Pass button is enabled.
5. Wait for the Pass button to become enabled (retrying 'Run' if needed under CPU load).
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
    wait_for,
)

TEST_NAME = "Audio Cold Start Input Latency Test"
set_screenshot_dir("audio_cold_start_input_latency_test")


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


def run_measurement_and_wait_for_pass(max_attempts=3):
    """Tap 'Run' and wait for the Pass button to become enabled."""
    for attempt in range(1, max_attempts + 1):
        print(
            f"Starting cold start input latency measurement (attempt {attempt}/{max_attempts})..."
        )
        run_btn = wait_for(
            resource_id="com.android.cts.verifier:id/coldstart_run_btn", timeout=10
        )
        screenshot(f"tapping_run_attempt_{attempt}")
        tap(run_btn)

        # Poll for up to 10 seconds for the measurement to complete and enable Pass
        deadline = time.time() + 10
        while time.time() < deadline:
            root = ui_dump()
            res_node = find_node(
                root, resource_id="com.android.cts.verifier:id/coldstart_coldResultsTxt"
            )
            if res_node is not None and res_node.attrib.get("text"):
                print(f"  Result text: {res_node.attrib.get('text')!r}")

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
        "Pass button did not become enabled after running Audio Cold Start Input Latency Test"
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

    pass_btn = run_measurement_and_wait_for_pass()
    screenshot("measurement_passed")

    print("Tapping Pass...")
    tap_pass(pass_btn)
    screenshot("pass_tapped")

    export_and_verify(TEST_NAME)
    screenshot("export_done")


if __name__ == "__main__":
    main()
