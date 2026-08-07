#!/usr/bin/env python3
"""
KeyChain Storage Test (SECURITY section)

UI flow:
  1. Setup and navigate to 'KeyChain Storage Test'.
  2. Dismiss initial instruction/info dialog.
  3. Phase 1: Setup & Cert Installation:
     - Tap 'Next' 3 times.
     - Handle 'Choose a certificate type' dialog -> Tap 'OK'.
     - Handle 'Name this certificate' dialog ('KeyChainTest Keys') -> Tap 'OK'.
  4. Phase 2: HTTPS Test & Certificate Selection:
     - Tap 'Next' 2 times.
     - Handle 'Choose certificate' dialog with 'KeyChainTest Keys' selected -> Tap 'SELECT'.
  5. Phase 3: Settings Cleanup:
     - Tap 'Next' 2 times -> launches Settings (Security & privacy).
     - In Settings, scroll and tap 'More security & privacy'.
     - In submenu, scroll and tap 'Encryption & credentials'.
     - Tap 'Clear credentials'.
     - Tap 'OK' in Attention dialog.
     - If PIN prompt appears, enter PIN '1111'.
     - Send KEYCODE_BACK 3 times to return to KeyChainTest.
  6. Phase 4: Finish & Pass:
     - Tap 'Next'.
     - Wait for Pass button to become enabled, tap Pass, and export test report.
     - If any step fails, tap Fail button.
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
    scroll_and_tap_item_or_fail,
    screenshot,
)
from security_common import (
    setup_and_navigate,
    parse_security_args,
    dismiss_initial_dialog,
    is_pin_prompt_present,
    enter_pin_on_keypad,
    wait_for_pass_and_export,
)

TEST_NAME = "KeyChain Storage Test"


def tap_next_button(times=1, delay=1.5):
    """Find and tap the 'Next' button in KeyChainTest N times."""
    for i in range(times):
        print(f"  Tapping 'Next' (iteration {i + 1}/{times})...")
        root = ui_dump()
        next_btn = find_node(root, text="Next")
        if next_btn is None:
            for n in root.iter("node"):
                if "action_next" in n.attrib.get("resource-id", ""):
                    next_btn = n
                    break

        if next_btn is None or next_btn.attrib.get("enabled", "true") != "true":
            print("  [ERROR] 'Next' button not found or disabled. Tapping Fail...")
            screenshot(f"error_no_next_btn_{i}")
            fail_btn = find_fail_button(ui_dump())
            if fail_btn is not None:
                tap_fail(fail_btn)
            sys.exit(1)

        tap(next_btn)
        time.sleep(delay)


def wait_and_tap(text, timeout=10, step_name="dialog_button"):
    """Wait for a node containing specific text and tap it."""
    print(f"  Waiting for button/text: {text!r}...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        root = ui_dump()
        btn = find_node(root, text=text)
        if btn is None:
            btn = find_node(root, text=text.upper())
        if btn is None:
            match = find_node_containing(root, text)
            btn = match[0] if match else None

        if btn is not None:
            print(f"    Found {text!r} at {btn.attrib['bounds']}, tapping...")
            screenshot(f"found_{step_name}")
            tap(btn)
            time.sleep(2)
            return True
        time.sleep(1)

    print(f"  [ERROR] Failed to find {text!r} within {timeout}s. Tapping Fail...")
    screenshot(f"error_not_found_{step_name}")
    fail_btn = find_fail_button(ui_dump())
    if fail_btn is not None:
        tap_fail(fail_btn)
    sys.exit(1)


def main():
    args = parse_security_args("Run CTS Verifier KeyChain Storage Test.")
    setup_and_navigate(
        TEST_NAME,
        skip_prereqs=args.skip_prereqs,
        screenshot_subdir="security_keychain_storage",
    )
    dismiss_initial_dialog()

    # ── Phase 1: Setup & Cert Installation ────────────────────────────────────
    print("\n[Phase 1] Setup and Certificate Installation...")
    tap_next_button(times=3, delay=1.5)
    screenshot("03_after_3_nexts")

    # Dialog: 'Choose a certificate type' -> Hit 'OK'
    wait_and_tap("OK", timeout=10, step_name="choose_cert_type_ok")

    # Prompt: 'Name this certificate' ('KeyChainTest Keys') -> Hit 'OK'
    wait_and_tap("OK", timeout=10, step_name="name_certificate_ok")

    # ── Phase 2: HTTPS Test & Certificate Selection ───────────────────────────
    print("\n[Phase 2] HTTPS Test & Certificate Selection...")
    tap_next_button(times=2, delay=1.5)
    screenshot("04_after_2_nexts")

    # 'Choose certificate' screen with 'KeyChainTest Keys' -> Hit 'SELECT'
    wait_and_tap("SELECT", timeout=10, step_name="select_certificate")
    time.sleep(2)
    screenshot("05_cert_selected")

    # ── Phase 3: Settings Cleanup ─────────────────────────────────────────────
    print("\n[Phase 3] Settings Cleanup...")
    # Click Next twice to launch Settings -> 'Security & privacy'
    tap_next_button(times=2, delay=2.0)
    screenshot("06_settings_launched")

    # In Settings: scroll to 'More security & privacy' and tap
    scroll_and_tap_item_or_fail("More security & privacy")
    screenshot("07_inside_more_security_privacy")

    # In submenu: scroll to 'Encryption & credentials' and tap
    scroll_and_tap_item_or_fail("Encryption & credentials")
    screenshot("08_inside_encryption_credentials")

    # Click 'Clear credentials'
    scroll_and_tap_item_or_fail("Clear credentials")
    screenshot("09_clear_credentials_clicked")

    # Attention dialogue -> Hit 'OK'
    wait_and_tap("OK", timeout=10, step_name="attention_clear_credentials_ok")
    time.sleep(1)

    # Check if PIN prompt appears after clearing credentials
    root = ui_dump()
    if is_pin_prompt_present(root):
        print("  PIN prompt detected after clearing credentials.")
        screenshot("10_pin_prompt")
        enter_pin_on_keypad("1111")
        time.sleep(2)

    # Return to CtsVerifier KeyChainTest via 3 Back presses
    print("  Returning to KeyChainTest (pressing Back 3 times)...")
    for _ in range(3):
        adb("shell", "input", "keyevent", "KEYCODE_BACK")
        time.sleep(1)

    screenshot("11_returned_to_test")

    # ── Phase 4: Finish & Pass ────────────────────────────────────────────────
    print("\n[Phase 4] Finish & Pass...")
    tap_next_button(times=1, delay=1.5)

    wait_for_pass_and_export(TEST_NAME)


if __name__ == "__main__":
    main()
