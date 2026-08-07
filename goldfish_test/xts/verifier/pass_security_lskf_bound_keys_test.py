#!/usr/bin/env python3
"""
LSKF Bound Keys Test (SECURITY section)

Prerequisites:
  - For PIN authentication: PIN '1111' set (PIN_ONLY).
  - For Fingerprint authentication: PIN '1111' + Fingerprint 1 enrolled (PIN_AND_FINGERPRINT).
  - Controlled via --auth-type {both,pin,fingerprint} (default: both).
  - Use --skip-prereqs / -s to skip credential setup and verify natural failure.

UI Flow:
  1. Set up credentials for selected auth type (unless skip_prereqs is set).
  2. Launch and navigate to 'LSKF Bound Keys Test'.
  3. Dismiss initial instruction dialog.
  4. Find and tap 'Start Test' button.
  5. Wait for authentication prompt:
     - If PIN: enter PIN '1111' on keypad.
     - If Fingerprint: simulate touch on fingerprint sensor (finger ID 1).
  6. Verify Pass button is enabled, tap Pass, and export verified test report.
"""

import argparse
import os
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(SCRIPT_DIR)

from cts_common import (
    adb,
    ui_dump,
    find_fail_button,
    tap_fail,
    screenshot,
)
from security_common import (
    PrereqState,
    dismiss_initial_dialog,
    enter_pin_on_keypad,
    is_fingerprint_prompt_present,
    is_pin_prompt_present,
    setup_and_navigate,
    tap_button_or_fail,
    wait_for_pass_and_export,
)

TEST_NAME = "LSKF Bound Keys Test"


def run_lskf_test(auth_type, skip_prereqs=False):
    """Run LSKF Bound Keys Test for a specific authentication mode ('pin' or 'fingerprint')."""
    print(f"\n=======================================================")
    print(f"[LSKF] Running test with auth mode: {auth_type.upper()}")
    print(f"=======================================================")

    prereq_state = (
        PrereqState.PIN_AND_FINGERPRINT
        if auth_type == "fingerprint"
        else PrereqState.PIN_ONLY
    )
    screenshot_sub = f"security_lskf_bound_keys_{auth_type}"

    setup_and_navigate(
        TEST_NAME,
        prereq_state=prereq_state,
        skip_prereqs=skip_prereqs,
        screenshot_subdir=screenshot_sub,
    )
    dismiss_initial_dialog()

    # Step 1: Tap 'Start Test' button
    print("  Tapping 'Start Test' button...")
    tap_button_or_fail("Start Test", resource_id="sec_start_test_button")
    screenshot(f"03_{auth_type}_start_test_tapped")

    # Step 2: Wait for authentication prompt and authenticate
    print(f"  Waiting for {auth_type} authentication prompt...")
    auth_handled = False
    deadline = time.time() + 15
    while time.time() < deadline:
        root = ui_dump()
        if auth_type == "fingerprint":
            if is_fingerprint_prompt_present(root):
                print("  Fingerprint prompt detected. Simulating touch for finger 1...")
                screenshot(f"04_{auth_type}_prompt_detected")
                adb("emu", "finger", "touch", "1", check=False)
                time.sleep(2)
                auth_handled = True
                break
            elif is_pin_prompt_present(root):
                # Fallback in case biometric defaulted directly to PIN
                print("  PIN prompt detected during fingerprint test.")
                screenshot(f"04_{auth_type}_pin_fallback_detected")
                enter_pin_on_keypad("1111")
                time.sleep(2)
                auth_handled = True
                break
        elif auth_type == "pin":
            if is_pin_prompt_present(root):
                print("  PIN prompt detected.")
                screenshot(f"04_{auth_type}_prompt_detected")
                enter_pin_on_keypad("1111")
                time.sleep(2)
                auth_handled = True
                break
        time.sleep(1)

    if not auth_handled:
        print(f"  [ERROR] Expected {auth_type} prompt did not appear. Tapping Fail...")
        screenshot(f"error_no_{auth_type}_prompt")
        fail_btn = find_fail_button(ui_dump())
        if fail_btn is not None:
            tap_fail(fail_btn)
        sys.exit(1)

    screenshot(f"05_{auth_type}_auth_completed")

    # Step 3: Wait for Pass button and export report
    wait_for_pass_and_export(
        f"{TEST_NAME} ({auth_type.upper()})", exit_on_complete=False
    )


def main():
    parser = argparse.ArgumentParser(
        description="CTS Verifier LSKF Bound Keys Test Automation"
    )
    parser.add_argument(
        "--auth-type",
        "--auth_type",
        "-a",
        choices=["both", "pin", "fingerprint"],
        default="both",
        help="Authentication mode to test: 'both' (default), 'pin', or 'fingerprint'.",
    )
    parser.add_argument(
        "--skip-prereqs",
        "--skip_prereqs",
        "-s",
        action="store_true",
        default=bool(os.environ.get("CTS_SECURITY_SKIP_PREREQS")),
        help="Skip prerequisite credential setup to verify natural test failure.",
    )
    args, _ = parser.parse_known_args()

    modes = ["pin", "fingerprint"] if args.auth_type == "both" else [args.auth_type]

    for mode in modes:
        run_lskf_test(mode, skip_prereqs=args.skip_prereqs)

    print(
        f"\n>>> PASSED: LSKF Bound Keys Test completed successfully ({args.auth_type})."
    )


if __name__ == "__main__":
    main()
