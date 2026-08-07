#!/usr/bin/env python3
"""
Unlocked Device Required Keys Test (SECURITY section)

Prerequisites:
  - Secure lock screen (PIN '1111') and Fingerprint 1 enrolled (PrereqState.PIN_AND_FINGERPRINT).
  - Use --skip-prereqs / -s to skip credential setup and test natural behavior.

UI Flow & Validation:
  1. Navigate to 'Unlocked Device Required Keys Test' in CtsVerifier.
  2. Dismiss initial instruction dialog if present.
  3. Tap 'Start Test' button.
  4. Cycle 1 (Biometric Unlock):
     - Turn off screen (KEYCODE_POWER).
     - Wait 5 seconds with screen locked.
     - Unlock screen with Fingerprint 1.
     - CtsVerifier verifies key is unavailable when locked and available after biometric unlock.
  5. Cycle 2 (Credential Unlock):
     - Turn off screen (KEYCODE_POWER).
     - Wait 5 seconds with screen locked.
     - Wake screen and unlock with PIN '1111'.
     - CtsVerifier verifies key is available after credential unlock.
  6. Dismiss 'Test completed successfully.' dialog.
  7. Verify Pass button is enabled, tap Pass, and export verified report.
"""

import os
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(SCRIPT_DIR)

from cts_common import (
    adb,
    find_fail_button,
    find_node,
    is_pass_button_enabled,
    screenshot,
    tap,
    tap_fail,
    ui_dump,
)
from security_common import (
    PrereqState,
    dismiss_initial_dialog,
    enter_pin_on_keypad,
    parse_security_args,
    setup_and_navigate,
    wait_for_pass_and_export,
)

TEST_NAME = "Unlocked Device Required Keys Test"


def perform_biometric_cycle(finger_id=1, lock_delay=5):
    """Lock screen, wait lock_delay seconds, then unlock with fingerprint."""
    print(f"\n--- [Cycle 1/2] Biometric Unlock Test (Fingerprint {finger_id}) ---")
    print(f"  Turning off screen and waiting {lock_delay}s...")
    adb("shell", "input", "keyevent", "26")  # KEYCODE_POWER
    time.sleep(lock_delay)

    print(f"  Unlocking with Fingerprint {finger_id}...")
    adb("emu", "finger", "touch", str(finger_id), check=False)
    time.sleep(3)
    screenshot("03_after_biometric_unlock")


def perform_credential_cycle(pin="1111", lock_delay=5):
    """Lock screen, wait lock_delay seconds, then unlock with PIN."""
    print(f"\n--- [Cycle 2/2] Credential Unlock Test (PIN {pin}) ---")
    print(f"  Turning off screen and waiting {lock_delay}s...")
    adb("shell", "input", "keyevent", "26")  # KEYCODE_POWER
    time.sleep(lock_delay)

    print("  Waking screen...")
    adb("shell", "input", "keyevent", "26")  # KEYCODE_POWER
    time.sleep(1)

    print("  Swiping up to reveal lock screen keypad...")
    adb("shell", "input", "swipe", "540", "1800", "540", "600", "200")
    time.sleep(1.5)

    enter_pin_on_keypad(pin)
    time.sleep(3)
    screenshot("04_after_credential_unlock")


def main():
    args = parse_security_args("Run CTS Verifier Unlocked Device Required Keys Test.")
    setup_and_navigate(
        TEST_NAME,
        prereq_state=PrereqState.PIN_AND_FINGERPRINT,
        skip_prereqs=args.skip_prereqs,
        screenshot_subdir="security_unlocked_device_required_keys",
    )
    dismiss_initial_dialog()

    root = ui_dump()
    start_btn = find_node(
        root, resource_id="com.android.cts.verifier:id/sec_start_test_button"
    )
    if start_btn is None:
        start_btn = find_node(root, text="Start Test")

    if start_btn is None:
        print("  [ERROR] 'Start Test' button not found on screen.")
        fail_btn = find_fail_button(ui_dump())
        if fail_btn is not None:
            tap_fail(fail_btn)
        sys.exit(1)

    print("Tapping 'Start Test' button...")
    tap(start_btn)
    time.sleep(2)
    screenshot("02_after_start_test")

    # Cycle 1: Biometric unlock
    perform_biometric_cycle(finger_id=1, lock_delay=5)

    # If Pass button is not yet enabled, perform credential cycle
    root = ui_dump()
    if not is_pass_button_enabled(root):
        perform_credential_cycle(pin="1111", lock_delay=5)

    # Dismiss any completion / instruction dialog that may remain
    root = ui_dump()
    msg_node = find_node(root, resource_id="android:id/message")
    if msg_node is not None:
        msg_text = msg_node.attrib.get("text", "")
        print(f"  Dialog displayed: {msg_text!r}")
        print("  Dismissing dialog...")
        adb("shell", "input", "keyevent", "KEYCODE_BACK")
        time.sleep(1.5)

    print("\nWaiting for Pass button to become enabled...")
    wait_for_pass_and_export(TEST_NAME)


if __name__ == "__main__":
    main()
