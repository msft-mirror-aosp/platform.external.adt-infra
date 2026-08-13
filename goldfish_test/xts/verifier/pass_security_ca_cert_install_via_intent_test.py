#!/usr/bin/env python3
"""
CA Cert install via intent Test (SECURITY section)
UI flow:
  1. Dismiss initial instruction/info dialog if present.
  2. Tap 'Go' button to launch CA certificate installation intent.
  3. Verify dialog appears with 'Install CA certificates in Settings'.
  4. Dismiss dialog via 'Close' button.
  5. Verify Pass button is enabled and export test report.
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
    find_node_containing,
    tap,
    tap_fail,
    find_fail_button,
    screenshot,
)
from security_common import (
    setup_and_navigate,
    parse_security_args,
    dismiss_initial_dialog,
    tap_button_or_fail,
    wait_for_pass_and_export,
)

TEST_NAME = "CA Cert install via intent"


def main():
    args = parse_security_args("Run CTS Verifier CA Cert install via intent Test.")
    setup_and_navigate(
        TEST_NAME,
        skip_prereqs=args.skip_prereqs,
        screenshot_subdir="security_ca_cert_install_via_intent",
    )
    dismiss_initial_dialog()

    tap_button_or_fail("Go", resource_id="run_test_button")

    # Verify dialog pops up saying "Install CA certificates in Settings"
    print("  Verifying 'Install CA certificates in Settings' dialog...")
    dialog_found = False
    close_btn = None
    deadline = time.time() + 10
    while time.time() < deadline:
        root = ui_dump()
        node, text = find_node_containing(root, "Install CA certificates in Settings")
        if node is None:
            node, text = find_node_containing(root, "Install CA certificate")
        if node is not None:
            print(f"    Found expected dialog: {text!r}")
            dialog_found = True
            screenshot("ca_cert_dialog_appeared")
            close_btn = find_node(root, text="Close")
            if close_btn is None:
                match = find_node_containing(root, "Close")
                close_btn = match[0] if match else None
            break
        time.sleep(1)

    if not dialog_found:
        print(
            "  [ERROR] Expected 'Install CA certificates in Settings' dialog did not appear. Tapping Fail..."
        )
        screenshot("error_dialog_not_found")
        fail_btn = find_fail_button(ui_dump())
        if fail_btn is not None:
            tap_fail(fail_btn)
        sys.exit(1)

    # Dismiss dialog via 'Close' button
    if close_btn is not None:
        print(
            f"  Dismissing dialog via 'Close' button at {close_btn.attrib['bounds']}..."
        )
        screenshot("tapping_close")
        tap(close_btn)
        time.sleep(2)
    else:
        print("  [WARN] 'Close' button not found by text, sending KEYCODE_BACK...")
        adb("shell", "input", "keyevent", "KEYCODE_BACK")
        time.sleep(2)

    wait_for_pass_and_export(TEST_NAME)


if __name__ == "__main__":
    main()
