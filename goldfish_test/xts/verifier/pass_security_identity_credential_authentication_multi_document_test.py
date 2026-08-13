#!/usr/bin/env python3
"""
Identity Credential Authentication Multi-Document Test (SECURITY section)
Prerequisites:
  - Secure lock screen (PIN '1111') and enrolled fingerprint (Finger 1).
  - Use --skip-prereqs / -s to skip credential setup and verify natural failure.

UI flow:
  1. Setup PIN '1111' and enroll fingerprint 1 (unless skip_prereqs is set).
  2. Launch and navigate to 'Identity Credential Authentication Multi-Document'.
  3. Dismiss initial instruction/permission dialogs if present.
  4. Find and tap 'Start Test' button.
  5. Wait for fingerprint authentication prompt ('Identity Credential') and simulate touch.
  6. Verify Pass button is enabled and export test report.
"""

import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(SCRIPT_DIR)

from security_common import (
    PrereqState,
    parse_security_args,
    setup_and_navigate,
    dismiss_initial_dialog,
    tap_button_or_fail,
    wait_for_fingerprint_prompt_and_touch,
    wait_for_pass_and_export,
)

TEST_NAME = "Identity Credential Authentication Multi-Document"


def main():
    args = parse_security_args(
        "Run CTS Verifier Identity Credential Authentication Multi-Document Test."
    )
    setup_and_navigate(
        TEST_NAME,
        prereq_state=PrereqState.PIN_AND_FINGERPRINT,
        skip_prereqs=args.skip_prereqs,
        screenshot_subdir="security_identity_credential_authentication_multi_document",
    )
    dismiss_initial_dialog()
    tap_button_or_fail("Start Test", resource_id="sec_start_test_button")
    wait_for_fingerprint_prompt_and_touch(finger_id=1)
    wait_for_pass_and_export(TEST_NAME)


if __name__ == "__main__":
    main()
