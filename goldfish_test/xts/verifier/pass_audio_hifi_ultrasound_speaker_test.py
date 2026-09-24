#!/usr/bin/env python3
"""
Hifi Ultrasound Speaker Test (AUDIO section)

On the Android Emulator:
- Depending on the CtsVerifier APK version:
  1. In newer AOSP main APKs, `Build.IS_EMULATOR` causes `updateTestState()` to call
     `markAsSkipped(SkipReason.DEVICE_IS_EMULATOR)` and show a Skip Dialog ("OK"), immediately
     enabling the Pass button (`R.id.pass_button`).
  2. In older/prebuilt APKs, `PLAY` (`R.id.player_button`) is enabled. Tapping `PLAY` plays the
     ultrasound signal and displays an instruction popup window (`instruWindow`) with an 'OK'
     button (`R.id.ok`). Dismissing the popup via 'OK' (or BACK) sets `mPlayerTestCompleted = true`
     and calls `updateTestState()`, which calls `markAsPassed(null)` and enables the Pass button.
- This script handles both flows automatically.
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

TEST_NAME = "Hifi Ultrasound Speaker Test"
set_screenshot_dir("audio_hifi_ultrasound_speaker_test")


def complete_test_and_wait_for_pass(timeout=30):
    """Dismiss OK dialogs, tap PLAY and dismiss popup if needed, and wait for enabled Pass button."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        root = ui_dump()

        # 1. Dismiss any modal dialog or popup window with an 'OK' button
        ok_btn = find_node(root, resource_id="com.android.cts.verifier:id/ok")
        if ok_btn is None:
            ok_btn = find_node(root, text="OK")
        if ok_btn is not None:
            print("  Dismissing dialog/popup via 'OK' button...")
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

        # 3. Check if PLAY button (`player_button`) is enabled
        play_btn = find_node(
            root, resource_id="com.android.cts.verifier:id/player_button"
        )
        if play_btn is not None and play_btn.attrib.get("enabled") == "true":
            print("  Tapping 'PLAY' button...")
            tap(play_btn)
            time.sleep(2)
            # If PopupWindow isn't captured in uiautomator dump or needs BACK to dismiss:
            root2 = ui_dump()
            popup_ok = find_node(root2, resource_id="com.android.cts.verifier:id/ok")
            if popup_ok is None:
                popup_ok = find_node(root2, text="OK")
            if popup_ok is not None:
                print("  Dismissing instruction popup via 'OK'...")
                tap(popup_ok)
            else:
                print("  Sending BACK key to dismiss instruction popup...")
                adb("shell", "input", "keyevent", "KEYCODE_BACK", check=False)
            time.sleep(1)
            continue

        time.sleep(1)

    raise TimeoutError(
        "Timed out waiting for enabled Pass button in Hifi Ultrasound Speaker Test"
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
