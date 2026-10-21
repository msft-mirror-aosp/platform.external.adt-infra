#!/usr/bin/env python3
"""
Audio Cold Start Output Latency Test (AUDIO section)

UI Flow & Prerequisites:
1. AudioOutColdStartLatencyActivity.onResume() checks SettingsUtils.areTouchSoundsActive(this),
   which reads Settings.System.SOUND_EFFECTS_ENABLED. If touch sounds are enabled (default=1),
   the 'Run' button is disabled.
2. Therefore, we set `settings put system sound_effects_enabled 0` before launching the test.
3. Launch CtsVerifier and navigate to 'Audio Cold Start Output Latency Test'.
4. Dismiss the initial Info dialog ("OK" button) if shown.
5. Tap the 'Run' button (resource-id="com.android.cts.verifier:id/coldstart_run_btn").
6. The test opens an audio output stream, waits 500ms via Timer, queries AudioTimestamp, and
   computes cold start output latency. When latency <= 500ms (LATENCY_MS_MUST), Pass is enabled.
7. Wait for the Pass button to become enabled (retrying 'Run' if needed).
8. Tap Pass, restore `sound_effects_enabled`, and export/verify the test results.
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
    tap_pass,
    ui_dump,
    wait_for,
)

TEST_NAME = "Audio Cold Start Output Latency Test"
set_screenshot_dir("audio_cold_start_output_latency_test")


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
            f"Starting cold start output latency measurement (attempt {attempt}/{max_attempts})..."
        )
        run_btn = wait_for(
            resource_id="com.android.cts.verifier:id/coldstart_run_btn", timeout=10
        )
        screenshot(f"tapping_run_attempt_{attempt}")
        tap(run_btn)

        # Poll for up to 10 seconds for the 500ms timer + measurement to complete and enable Pass
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
        "Pass button did not become enabled after running Audio Cold Start Output Latency Test"
    )


def main():
    setup()

    # Disable touch sounds so AudioOutColdStartLatencyActivity enables the 'Run' button
    orig_touch_sounds = adb(
        "shell", "settings", "get", "system", "sound_effects_enabled", check=False
    ).strip()
    print(
        f"Disabling touch sounds (sound_effects_enabled was {orig_touch_sounds!r})..."
    )
    adb("shell", "settings", "put", "system", "sound_effects_enabled", "0", check=False)

    try:
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
    finally:
        if orig_touch_sounds in ("0", "1"):
            print(f"Restoring sound_effects_enabled to {orig_touch_sounds}...")
            adb(
                "shell",
                "settings",
                "put",
                "system",
                "sound_effects_enabled",
                orig_touch_sounds,
                check=False,
            )

    export_and_verify(TEST_NAME)
    screenshot("export_done")


if __name__ == "__main__":
    main()
