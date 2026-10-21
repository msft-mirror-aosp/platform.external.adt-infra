#!/usr/bin/env python3
"""
Multichannel Mixdown Test (AUDIO section)

UI Flow:
1. Launch CtsVerifier and navigate to 'Multichannel Mixdown Test'.
2. Dismiss any initial dialogs ("OK" buttons, such as the MPC level notice dialog and Info dialog).
3. Ensure the Speaker/Mic route (`R.id.audio_mixdown_micspeaker`) is selected (on a handheld
   emulator, `mSpeakerMicRequired` is true while USB/Analog routes are not required).
4. Tap 'Start' (`R.id.audio_mixdown_start`). The test runs 32 multichannel mixdown phases
   (~19 seconds total).
5. Wait for the test phases to finish (`audio_mixdown_start` becomes enabled again).
6. Upon completion, `mSpeakerMicRun` is set to true (`hasRun() == true`), and `updateTestState()`
   calls `markAsFailedButNotMandated(...)` (since MPC < UpsideDownCake), enabling the Pass button
   (`R.id.pass_button`).
7. Scroll down if needed, tap Pass, and export/verify the test results.
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
)

TEST_NAME = "Multichannel Mixdown Test"
set_screenshot_dir("audio_multichannel_mixdown_test")


def dismiss_initial_dialogs():
    """Dismiss any initial OK dialogs (MPC notice / Info dialog)."""
    for _ in range(4):
        root = ui_dump()
        ok_btn = find_node(root, text="OK")
        if ok_btn is not None:
            print("  Dismissing dialog via 'OK' button...")
            tap(ok_btn)
            time.sleep(1)
        else:
            break


def run_mixdown_and_wait_for_pass(timeout=90):
    """Select Speaker/Mic route, tap Start, wait for 32 phases to complete, and return Pass button."""
    root = ui_dump()

    # Check if Pass button is already enabled (e.g. non-handheld device)
    pass_btn = find_node(root, content_desc="Pass")
    if pass_btn is None:
        pass_btn = find_node(
            root, resource_id="com.android.cts.verifier:id/pass_button"
        )
    if pass_btn is not None and pass_btn.attrib.get("enabled") == "true":
        print("  Pass button is already enabled!")
        return pass_btn

    # Ensure Speaker/Mic radio button is checked
    mic_speaker_rb = find_node(
        root, resource_id="com.android.cts.verifier:id/audio_mixdown_micspeaker"
    )
    if mic_speaker_rb is not None and mic_speaker_rb.attrib.get("checked") != "true":
        print("  Selecting Speaker/Mic route...")
        tap(mic_speaker_rb)
        time.sleep(1)
        root = ui_dump()

    # Tap Start button
    start_btn = find_node(
        root, resource_id="com.android.cts.verifier:id/audio_mixdown_start"
    )
    if start_btn is not None and start_btn.attrib.get("enabled") == "true":
        print("  Tapping 'Start' button to run Multichannel Mixdown phases (~19s)...")
        screenshot("before_start")
        tap(start_btn)
        time.sleep(21)

    # Wait for mixdown test phases to complete and Pass button to become enabled
    phases_done = False
    deadline = time.time() + timeout
    while time.time() < deadline:
        root = ui_dump()

        # Check if any dialog popped up
        ok_btn = find_node(root, text="OK")
        if ok_btn is not None:
            tap(ok_btn)
            time.sleep(1)
            continue

        pass_btn = find_node(root, content_desc="Pass")
        if pass_btn is None:
            pass_btn = find_node(
                root, resource_id="com.android.cts.verifier:id/pass_button"
            )

        if pass_btn is not None and pass_btn.attrib.get("enabled") == "true":
            print("  Pass button is enabled!")
            return pass_btn

        # Check if Start button re-enabled (test finished) or already scrolled past
        start_btn = find_node(
            root, resource_id="com.android.cts.verifier:id/audio_mixdown_start"
        )
        if start_btn is not None and start_btn.attrib.get("enabled") == "true":
            phases_done = True

        if phases_done or start_btn is None:
            print("  Mixdown phases finished; scrolling down to find Pass button...")
            adb("shell", "input", "swipe", "540", "2000", "540", "300", "200", check=False)
            time.sleep(1)
            continue

        print("  Mixdown test in progress...")
        time.sleep(3)

    raise TimeoutError(
        "Timed out waiting for enabled Pass button in Multichannel Mixdown Test"
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

    print("Running Multichannel Mixdown test and waiting for Pass button...")
    pass_btn = run_mixdown_and_wait_for_pass()
    screenshot("pass_enabled")

    print("Tapping Pass...")
    tap_pass(pass_btn)
    screenshot("pass_tapped")

    export_and_verify(TEST_NAME)
    screenshot("export_done")


if __name__ == "__main__":
    main()
