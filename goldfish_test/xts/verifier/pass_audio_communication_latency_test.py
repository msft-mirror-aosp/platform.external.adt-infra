#!/usr/bin/env python3
"""
Audio Communication Latency Test (AUDIO section)

On the Android Emulator:
1. AudioCommunicationLatencyActivity checks supported output devices among REQUIRED_DEVICES
   (TYPE_USB_HEADSET, TYPE_WIRED_HEADSET, TYPE_BUILTIN_SPEAKER, TYPE_BUILTIN_EARPIECE).
2. Because the emulator only supports TYPE_BUILTIN_SPEAKER (no USB port, no 3.5mm jack,
   no earpiece), `hasMoreThanOneDeviceToTest()` returns false.
3. `checkSkipReason()` returns `SkipReason.INSUFFICIENT_COMMUNICATION_DEVICES`, which calls
   `markAsSkipped(...)` and automatically enables the Pass button (`R.id.pass_button`).
4. Two stacked AlertDialogs are shown during onCreate():
   - Skip Dialog ("Skippable or Non-Mandatory"): lacks support for multiple communication devices.
   - Info Dialog ("Audio Communication Latency Test"): test instructions.
5. Dismissing both dialogs via their "OK" buttons reveals the enabled Pass button.
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

TEST_NAME = "Audio Communication Latency Test"
set_screenshot_dir("audio_communication_latency_test")


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
