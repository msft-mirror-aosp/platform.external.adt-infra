#!/usr/bin/env python3
"""
Audio MMAP PCM Offload Test (AUDIO section)

UI Flow on the Android Emulator:
1. Launch CtsVerifier and navigate to 'Audio MMAP PCM Offload Test' (AudioMmapOffloadTestActivity).
2. Dismiss the initial Info dialog ("OK" button) if shown.
3. On the emulator, only TYPE_BUILTIN_SPEAKER is supported (wired headset and USB layouts are hidden
   and automatically marked as TEST_SKIP_NOT_SUPPORTED).
4. Tap the speaker test button (resource-id="com.android.cts.verifier:id/audio_mmap_offload_speaker_btn").
5. `testConfig()` checks MMAP offload capability (`PERFORMANCE_MODE_POWER_SAVING_OFFLOADED`),
   returns `TEST_SKIP_NOT_SUPPORTED` (which is accepted by `isTestResultAccepted()`), and enables
   the Pass button (`R.id.pass_button`).
6. Wait for Pass button to become enabled, tap Pass, and export/verify the report.
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

TEST_NAME = "Audio MMAP PCM Offload Test"
set_screenshot_dir("audio_mmap_pcm_offload_test")


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


def run_speaker_test_and_wait_for_pass(max_attempts=3):
    """Tap the speaker test button and wait for the Pass button to become enabled."""
    for attempt in range(1, max_attempts + 1):
        print(
            f"Running MMAP PCM Offload speaker test (attempt {attempt}/{max_attempts})..."
        )
        root = ui_dump()
        # Check if Pass is already enabled
        pass_btn = find_node(root, content_desc="Pass")
        if pass_btn is None:
            pass_btn = find_node(
                root, resource_id="com.android.cts.verifier:id/pass_button"
            )
        if pass_btn is not None and pass_btn.attrib.get("enabled") == "true":
            print("  Pass button is already enabled!")
            return pass_btn

        speaker_btn = wait_for(
            resource_id="com.android.cts.verifier:id/audio_mmap_offload_speaker_btn",
            timeout=10,
        )
        screenshot(f"tapping_speaker_btn_attempt_{attempt}")
        tap(speaker_btn)

        deadline = time.time() + 10
        while time.time() < deadline:
            root = ui_dump()
            status_node = find_node(
                root,
                resource_id="com.android.cts.verifier:id/audio_mmap_offload_speaker_status",
            )
            if status_node is not None and status_node.attrib.get("text"):
                print(f"  Speaker status: {status_node.attrib.get('text')!r}")

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
        "Pass button did not become enabled after running Audio MMAP PCM Offload Test"
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

    pass_btn = run_speaker_test_and_wait_for_pass()
    screenshot("test_passed")

    print("Tapping Pass...")
    tap_pass(pass_btn)
    screenshot("pass_tapped")

    export_and_verify(TEST_NAME)
    screenshot("export_done")


if __name__ == "__main__":
    main()
