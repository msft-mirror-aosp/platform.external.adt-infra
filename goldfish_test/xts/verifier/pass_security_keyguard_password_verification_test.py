#!/usr/bin/env python3
"""
Keyguard Password Verification Test (SECURITY section)

UI Flow:
  1. Ensure PIN prerequisite is set (PIN_ONLY -> '1111').
  2. Setup CtsVerifier and navigate to 'Keyguard Password Verification'.
  3. Dismiss initial instruction dialog.
  4. Tap 'Change password' button.
  5. Verify PIN verification screen appears; fail if not shown.
  6. Enter PIN '1111' on the keypad.
  7. Verify 'Choose a new screen lock' / screen lock selection screen appears.
  8. Send KEYCODE_BACK to return to CtsVerifier.
  9. Tap Pass button and export test report.
"""

import os
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(SCRIPT_DIR)

from cts_common import (
    adb,
    ui_dump,
    find_node,
    tap_fail,
    find_fail_button,
    screenshot,
)
from security_common import (
    setup_and_navigate,
    parse_security_args,
    dismiss_initial_dialog,
    is_pin_prompt_present,
    enter_pin_on_keypad,
    tap_button_or_fail,
    wait_for_pass_and_export,
    PrereqState,
)

TEST_NAME = "Keyguard Password Verification"


def main():
    args = parse_security_args("Run CTS Verifier Keyguard Password Verification Test.")
    setup_and_navigate(
        TEST_NAME,
        prereq_state=PrereqState.PIN_ONLY,
        skip_prereqs=args.skip_prereqs,
        screenshot_subdir="security_keyguard_password_verification",
    )
    dismiss_initial_dialog()

    # Step 1: Tap 'Change password' button
    print("  Tapping 'Change password' button...")
    tap_button_or_fail("Change password")
    time.sleep(2)
    screenshot("03_change_password_clicked")

    # Step 2: Verify PIN prompt is displayed
    print("  Verifying PIN verification prompt appears...")
    pin_prompt_found = False
    for _ in range(5):
        root = ui_dump()
        if is_pin_prompt_present(root):
            pin_prompt_found = True
            break
        time.sleep(1)

    if not pin_prompt_found:
        print("  [ERROR] PIN verification prompt was not shown. Tapping Fail...")
        screenshot("error_no_pin_prompt")
        fail_btn = find_fail_button(ui_dump())
        if fail_btn is not None:
            tap_fail(fail_btn)
        sys.exit(1)

    screenshot("04_pin_prompt_shown")

    # Step 3: Enter PIN '1111' on keypad
    enter_pin_on_keypad("1111")
    time.sleep(2)
    screenshot("05_pin_entered")

    # Step 4: Verify screen lock selection screen appears
    print("  Verifying screen lock options screen appears...")
    lock_options_found = False
    for _ in range(5):
        root = ui_dump()
        if (
            find_node(root, text_contains="PIN") is not None
            or find_node(root, text_contains="Password") is not None
            or find_node(root, text_contains="Screen lock") is not None
        ):
            lock_options_found = True
            break
        time.sleep(1)

    if not lock_options_found:
        print("  [ERROR] Screen lock options screen was not shown. Tapping Fail...")
        screenshot("error_no_lock_options")
        fail_btn = find_fail_button(ui_dump())
        if fail_btn is not None:
            tap_fail(fail_btn)
        sys.exit(1)

    screenshot("06_screen_lock_options_verified")

    # Step 5: Press Back to return to CtsVerifier
    print("  Pressing Back to return to Keyguard Password Verification test...")
    adb("shell", "input", "keyevent", "KEYCODE_BACK")
    time.sleep(2)
    screenshot("07_returned_to_cts_verifier")

    # Step 6: Wait for Pass and export report
    wait_for_pass_and_export(TEST_NAME)


if __name__ == "__main__":
    main()
