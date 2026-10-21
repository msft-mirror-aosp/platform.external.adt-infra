#!/usr/bin/env python3
"""
Audio Data Paths USB Interface Test (AUDIO section)

On the Android Emulator:
1. AudioDataPathsUSBInterfaceActivity extends AudioDataPathsBaseActivity, which sets
   `mIsEmulator = Build.IS_EMULATOR` (true on emulator).
2. During `initializeTestManager()` -> `updateTestState()`, `mIsEmulator` causes
   `markAsSkipped(SkipReason.DEVICE_IS_EMULATOR)` to be called, immediately enabling
   the Pass button (`R.id.pass_button`).
3. Two stacked AlertDialogs are shown during onCreate():
   - Skip Dialog ("Skippable or Non-Mandatory"): device is an emulator.
   - Info Dialog ("Audio Data Paths USB Interface Test"): test instructions.
4. Dismissing both dialogs via their "OK" buttons reveals the enabled Pass button.
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

TEST_NAME = "Audio Data Paths USB Interface Test"
set_screenshot_dir("audio_data_paths_usb_interface_test")


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
    pass_btn = dismiss_dialogs_and_wait_for_pass(timeout=60)
    screenshot("dialogs_dismissed_pass_enabled")

    print("Tapping Pass...")
    tap_pass(pass_btn)
    screenshot("pass_tapped")

    export_and_verify(TEST_NAME)
    screenshot("export_done")


if __name__ == "__main__":
    main()
