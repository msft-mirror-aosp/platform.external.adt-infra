#!/usr/bin/env python3
"""
Immersive Audio Test (AUDIO section)

On the Android Emulator:
1. ImmersiveAudioActivity checks `AudioSystemFlags.claimsHeadTrackingLowLatency(this)` (false on
   emulator) in `onCreate()` and `updateTestState()`.
2. Because head tracking low latency is not supported, `updateTestState()` marks the test as
   skipped and immediately enables the Pass button (`R.id.pass_button`).
3. A Skip Dialog ("OK" button) is displayed stating that Head Tracking Low Latency is lacked.
4. Dismissing any "OK" dialogs reveals the enabled Pass button.
"""

import os
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.append(SCRIPT_DIR)

from cts_common import (
    dismiss_dialogs_and_wait_for_pass,
    export_and_verify,
    navigate_to,
    screenshot,
    set_screenshot_dir,
    setup,
    tap_pass,
)

TEST_NAME = "Immersive Audio Test"
set_screenshot_dir("audio_immersive_audio_test")


def main():
    setup()
    print("Navigating to test...")
    screenshot("navigating_to_test")
    navigate_to(TEST_NAME)
    time.sleep(2)
    screenshot("activity_launched")

    print(
        "Dismissing OK dialogs (Skip dialog and Info dialog) and waiting for Pass button..."
    )
    pass_btn = dismiss_dialogs_and_wait_for_pass()
    screenshot("dialogs_dismissed_pass_enabled")

    print("Tapping Pass...")
    tap_pass(pass_btn)
    screenshot("pass_tapped")

    export_and_verify(TEST_NAME)
    screenshot("export_done")


if __name__ == "__main__":
    main()
