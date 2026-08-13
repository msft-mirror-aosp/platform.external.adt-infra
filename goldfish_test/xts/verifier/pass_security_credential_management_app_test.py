#!/usr/bin/env python3
"""
Credential Management App Test (SECURITY section)
UI flow:
  1. Dismiss initial instruction/info dialog if present.
  2. Tap first item: 'Request to manage credentials'.
     - Handle permission request dialog by tapping 'Allow'.
  3. Sequentially tap each remaining test button/item:
     - 'Check is credential management app'
     - 'Check correct authentication policy is set'
     - 'Generate key pair'
     - 'Create and install certificate'
     - 'Request certificate for authentication'
     - 'Sign data with the private key'
     - 'Verify signature with the public key'
     - 'Remove credential management app'
  4. Verify Pass button is enabled and export test report.
"""

import os
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(SCRIPT_DIR)

from cts_common import (
    ui_dump,
    find_node,
    tap,
    scroll_and_tap_item_or_fail,
    screenshot,
)
from security_common import (
    setup_and_navigate,
    parse_security_args,
    dismiss_initial_dialog,
    wait_for_pass_and_export,
)

TEST_NAME = "Credential Management App Test"

BUTTON_SEQUENCE = [
    "Request to manage credentials",
    "Check is credential management app",
    "Check correct authentication policy is set",
    "Generate key pair",
    "Create and install certificate",
    "Request certificate for authentication",
    "Sign data with the private key",
    "Verify signature with the public key",
    "Remove credential management app",
]


def main():
    args = parse_security_args("Run CTS Verifier Credential Management App Test.")
    setup_and_navigate(
        TEST_NAME,
        skip_prereqs=args.skip_prereqs,
        screenshot_subdir="security_credential_management_app",
    )
    dismiss_initial_dialog()

    # Step 1: Tap 'Request to manage credentials'
    step1_text = BUTTON_SEQUENCE[0]
    print(f"  Executing Step 1: {step1_text!r}...")
    scroll_and_tap_item_or_fail(step1_text, max_swipes=10)

    time.sleep(2)
    screenshot("permission_dialog_requested")

    # Handle system permission dialog: click 'Allow'
    print("  Looking for 'Allow' permission button...")
    allow_found = False
    for _ in range(5):
        root = ui_dump()
        allow_btn = find_node(root, text="Allow")
        if allow_btn is None:
            allow_btn = find_node(root, text="ALLOW")
        if allow_btn is None:
            for n in root.iter("node"):
                r_id = n.attrib.get("resource-id", "")
                if "permission_allow_button" in r_id or r_id.endswith(":id/button1"):
                    allow_btn = n
                    break
        if allow_btn is not None:
            print(f"  Tapping 'Allow' at {allow_btn.attrib['bounds']}...")
            tap(allow_btn)
            allow_found = True
            time.sleep(2)
            break
        time.sleep(1)

    if not allow_found:
        print("  [WARN] 'Allow' button not detected on permission request.")

    screenshot("permission_allowed")

    # Step 2 to 9: Click each remaining button in sequence
    for idx, button_text in enumerate(BUTTON_SEQUENCE[1:], start=2):
        print(f"  Executing Step {idx}: {button_text!r}...")
        scroll_and_tap_item_or_fail(button_text, max_swipes=10)
        screenshot(f"step_{idx}_completed")

    wait_for_pass_and_export(TEST_NAME)


if __name__ == "__main__":
    main()
