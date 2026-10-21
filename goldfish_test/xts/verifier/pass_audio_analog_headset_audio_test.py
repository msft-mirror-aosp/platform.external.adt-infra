#!/usr/bin/env python3
"""
Analog Headset Audio Test (AUDIO section)

On the Android Emulator (which has no 3.5mm audio jack and no USB port):
1. AudioDeviceUtils.supportsAnalogHeadset(this) checks AudioManager.getSupportedDeviceTypes()
   for TYPE_WIRED_HEADSET and returns SUPPORTSDEVICE_NO (0).
2. AnalogHeadsetAudioActivity.onCreate() calls updateTestState(), which sets the test status
   to TEST_STATUS_SKIPPED via markAsSkipped(SkipReason.ANALOG_HEADSET_UNSUPPORTED) and
   immediately enables the Pass button (R.id.pass_button).
3. Two AlertDialogs are queued via Activity.showDialog() during onCreate():
   - Skip Dialog ("Skippable or Non-Mandatory"): states the device lacks analog headset support.
   - Info Dialog ("Analog Headset Test"): describes the test instructions.
4. Dismissing both dialogs via their "OK" buttons reveals the main activity screen where the
   Pass button is enabled. Tapping Pass records the result and completes the test.
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

TEST_NAME = "Analog Headset Audio Test"
set_screenshot_dir("audio_analog_headset_audio_test")


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
