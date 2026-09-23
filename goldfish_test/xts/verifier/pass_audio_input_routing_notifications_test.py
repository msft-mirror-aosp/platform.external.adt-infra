#!/usr/bin/env python3
"""
Audio Input Routing Notifications Test (AUDIO section)

On the Android Emulator:
- The emulator has no wired USB or Analog audio peripherals (no 3.5mm jack, no USB port).
- Depending on the CtsVerifier APK version:
  1. In older/prebuilt APKs, the activity prompts:
     "Does this device support wired USB or Analog audio peripherals?"
     with 'No' (resource-id="com.android.cts.verifier:id/audio_wired_no") and 'Yes' buttons.
     Tapping 'No' immediately enables the Pass button (`R.id.pass_button`).
  2. In newer AOSP main APKs, AudioNotificationsBaseActivity checks
     `AudioDeviceUtils.supportsAnalogHeadset(mContext)`, `supportsUsbHeadset(mContext)`,
     and `supportsUsbAudioInterface(mContext)`, which return SUPPORTSDEVICE_NO.
     `!mSupportsWiredPeripheral` calls `markAsSkipped(SkipReason.WIRED_PERIPHERAL_UNSUPPORTED)`
     during `onCreate()`, immediately enabling the Pass button (`R.id.pass_button`).
- This script handles both flows by dismissing any "OK" dialogs, tapping 'No'
  (`audio_wired_no`) if present, waiting for the Pass button to become enabled, and
  tapping Pass.
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

TEST_NAME = "Audio Input Routing Notifications Test"
set_screenshot_dir("audio_input_routing_notifications_test")


def complete_test_and_wait_for_pass(timeout=30):
    """Dismiss OK dialogs, tap 'No' for wired audio support if prompted, and wait for Pass."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        root = ui_dump()

        # 1. Dismiss any modal dialog with an 'OK' button
        ok_btn = find_node(root, text="OK")
        if ok_btn is not None:
            print("  Dismissing dialog via 'OK' button...")
            tap(ok_btn)
            time.sleep(1)
            continue

        # 2. Check if Pass button is already enabled
        pass_btn = find_node(root, content_desc="Pass")
        if pass_btn is None:
            pass_btn = find_node(
                root, resource_id="com.android.cts.verifier:id/pass_button"
            )

        if pass_btn is not None and pass_btn.attrib.get("enabled") == "true":
            print("  Pass button is enabled!")
            return pass_btn

        # 3. Check if 'No' button for wired peripheral support is present and enabled
        no_btn = find_node(
            root, resource_id="com.android.cts.verifier:id/audio_wired_no"
        )
        if no_btn is not None and no_btn.attrib.get("enabled") == "true":
            print("  Tapping 'No' for wired USB/Analog audio peripheral support...")
            tap(no_btn)
            time.sleep(1)
            continue

        time.sleep(1)

    raise TimeoutError(
        "Timed out waiting for enabled Pass button in Audio Input Routing Notifications Test"
    )


def main():
    setup()
    print("Navigating to test...")
    screenshot("navigating_to_test")
    navigate_to(TEST_NAME)
    time.sleep(2)
    screenshot("activity_launched")

    print("Completing test flow and waiting for Pass button...")
    pass_btn = complete_test_and_wait_for_pass()
    screenshot("pass_enabled")

    print("Tapping Pass...")
    tap_pass(pass_btn)
    screenshot("pass_tapped")

    export_and_verify(TEST_NAME)
    screenshot("export_done")


if __name__ == "__main__":
    main()
