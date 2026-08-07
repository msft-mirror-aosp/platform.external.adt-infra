#!/usr/bin/env python3
"""
Android Protected Confirmation Test (SECURITY section)

Prerequisites:
  - Clean slate: No lockscreen set (PrereqState.NONE).
  - Use --skip-prereqs / -s to skip credential wipe.

UI Flow & Validation:
  1. Navigate to 'Android Protected Confirmation Test' in CtsVerifier.
  2. The test activity detects that Android Protected Confirmation is not supported
     on this device (optional feature) and shows an information dialog:
     "Android Protected Confirmation is not implemented by this device. This is okay
      because this is an optional feature. Set this test to passed and continue."
  3. Dismiss dialog (tap OK / Back).
  4. Verify Pass button is enabled, tap Pass, and export verified report.
"""

import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(SCRIPT_DIR)

from security_common import (
    PrereqState,
    dismiss_initial_dialog,
    parse_security_args,
    setup_and_navigate,
    wait_for_pass_and_export,
)

TEST_NAME = "Android Protected Confirmation Test"


def main():
    args = parse_security_args("Run CTS Verifier Android Protected Confirmation Test.")
    setup_and_navigate(
        TEST_NAME,
        prereq_state=PrereqState.NONE,
        skip_prereqs=args.skip_prereqs,
        screenshot_subdir="security_protected_confirmation",
    )
    dismiss_initial_dialog()
    wait_for_pass_and_export(TEST_NAME)


if __name__ == "__main__":
    main()
