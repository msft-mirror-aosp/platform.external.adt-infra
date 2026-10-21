#!/usr/bin/env python3
"""
Audio Stream Disconnect Test (AUDIO section)

On the Android Emulator:
- The emulator does not have a physical analog or USB headset port.
- Depending on the CtsVerifier APK version:
  1. In older/prebuilt APKs, the activity prompts:
     "Does this device have an analog headset port?"
     with 'No' (resource-id="com.android.cts.verifier:id/headset_analog_port_no") and 'Yes' buttons.
     Tapping 'No' sets `mSupportsHeadset = false` and calls `updateTestState()`, which marks the
     test as skipped/passed and immediately enables the Pass button (`R.id.pass_button`).
  2. In newer AOSP main APKs, `AudioDeviceUtils.supportsAnalogHeadset(this)` and
     `AudioDeviceUtils.supportsUsbHeadset(this)` return `SUPPORTSDEVICE_NO` automatically,
     displaying a Skip dialog ("OK" button) and immediately enabling the Pass button.
- This script handles both flows by dismissing any "OK" dialogs, tapping 'No'
  (`headset_analog_port_no`) if present, waiting for the Pass button to become enabled, and
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

TEST_NAME = "Audio Stream Disconnect Test"
set_screenshot_dir("audio_stream_disconnect_test")


def complete_test_and_wait_for_pass(timeout=30):
    """Dismiss OK dialogs, tap 'No' for analog headset port if prompted, and wait for Pass."""
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

        # 3. Check if 'No' button for analog headset port is present and enabled
        no_btn = find_node(
            root, resource_id="com.android.cts.verifier:id/headset_analog_port_no"
        )
        if no_btn is not None and no_btn.attrib.get("enabled") == "true":
            print("  Tapping 'No' for analog headset port support...")
            tap(no_btn)
            time.sleep(1)
            continue

        time.sleep(1)

    raise TimeoutError(
        "Timed out waiting for enabled Pass button in Audio Stream Disconnect Test"
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
