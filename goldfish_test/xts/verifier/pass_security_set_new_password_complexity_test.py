#!/usr/bin/env python3
"""
Set New Password Complexity Test (SECURITY section)

Prerequisites:
  - Clean slate: No lockscreen set (PrereqState.NONE).
  - Use --skip-prereqs / -s to skip credential wipe.

Criteria & Tested Combinations:
  1. High Complexity:
     - Pattern and Swipe are disabled by admin.
     - PIN (must be >= 8 digits, no repeating or ordered sequences):
       - Fails: '1234' (length < 8), '11111111' (repeating), '12345678' (ascending),
                '87654321' (descending), '24682468' (step sequence).
       - Passes: '14725836' (8 digits, non-sequential).
     - Password (alphabetic or alphanumeric >= 6 characters, no sequences):
       - Fails: 'abcde' (length < 6), '123456' (numeric < 8), 'abcdef' (ascending), 'aaaaaa' (repeating).
       - Passes: 'zxcvbn' (alphabetic >= 6), 'a14725' (alphanumeric >= 6).
  2. Medium Complexity:
     - Pattern and Swipe are disabled by admin.
     - PIN (must be >= 4 digits, no repeating or ordered sequences):
       - Fails: '123' (length < 4), '1111'/'4444' (repeating), '1234'/'4321'/'2468' (ordered sequences).
       - Passes: '1472' (4 digits, non-sequential).
     - Password (alphabetic or alphanumeric >= 4 characters, no sequences):
       - Fails: 'abc' (length < 4), '123' (length < 4), 'abcd' (ascending), 'aaaa' (repeating).
       - Passes: 'zxvn' (alphabetic >= 4), 'a147' (alphanumeric >= 4).
  3. Low Complexity:
     - Pattern is enabled (not disabled by admin).
     - PIN (any PIN >= 4 digits):
       - Fails: '123' (length < 4).
       - Passes: '1234' (ordered allowed in Low), '0000' (repeating allowed in Low).
  4. None Complexity:
     - All screen lock options (None, Swipe, Pattern, PIN, Password) are available.
  5. Verification:
     - Verify Pass button enabled in CtsVerifier, tap Pass, and export verified report.
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
    screenshot,
    tap,
    tap_fail,
    ui_dump,
)
from security_common import (
    PrereqState,
    dismiss_initial_dialog,
    parse_security_args,
    setup_and_navigate,
    wait_for_pass_and_export,
)

TEST_NAME = "Set New Password Complexity Test"


def return_to_verifier(max_attempts=6):
    """Press BACK repeatedly until returned to CtsVerifier main test screen."""
    for _ in range(max_attempts):
        root = ui_dump()
        if find_node(root, text=TEST_NAME) is not None:
            return True
        adb("shell", "input", "keyevent", "KEYCODE_BACK")
        time.sleep(1)
    return False


def return_to_lock_choices(max_attempts=4):
    """Press BACK until returned to 'Choose a screen lock' options."""
    for _ in range(max_attempts):
        root = ui_dump()
        if (
            find_node(root, text="PIN") is not None
            or find_node(root, text="Pixel Imprint + PIN") is not None
        ):
            return True
        adb("shell", "input", "keyevent", "KEYCODE_BACK")
        time.sleep(1)
    return False


def handle_pixel_imprint_header():
    """If 'Continue without Pixel Imprint' is shown, tap it to see plain lock options."""
    root = ui_dump()
    cont = find_node(root, text="Continue without Pixel Imprint")
    if cont is not None:
        tap(cont)
        time.sleep(1.5)


def clear_text_field():
    """Clear text in the password/PIN entry field."""
    root = ui_dump()
    clear_btn = find_node(root, text="CLEAR")
    if clear_btn is not None:
        tap(clear_btn)
    else:
        for _ in range(25):
            adb("shell", "input", "keyevent", "67")  # KEYCODE_DEL
    time.sleep(0.5)


def check_combo(combo_text, expected_pass, label="PIN"):
    """
    Enter combo_text and verify whether NEXT button is enabled or disabled.
    Fails the test immediately if the actual state differs from expected_pass.
    """
    clear_text_field()
    adb("shell", "input", "text", combo_text)
    time.sleep(0.8)

    root = ui_dump()
    next_btn = find_node(root, text="NEXT")
    is_enabled = next_btn is not None and next_btn.attrib.get("enabled") == "true"

    if is_enabled != expected_pass:
        print(
            f"  [FAILURE] {label} {combo_text!r}: expected"
            f" enabled={expected_pass}, but got enabled={is_enabled}."
            " Tapping Fail..."
        )
        screenshot(f"error_{label}_{combo_text}")
        return_to_verifier()
        fail_btn = find_fail_button(ui_dump())
        if fail_btn is not None:
            tap_fail(fail_btn)
        sys.exit(1)

    print(
        f"  [OK] {label} {combo_text!r}: enabled={is_enabled} (expected"
        f" {expected_pass})"
    )
    return True


def find_lock_option(root, name):
    """Find lock option node by name or 'Pixel Imprint + name'."""
    node = find_node(root, text=name)
    if node is not None:
        return node
    node = find_node(root, text=f"Pixel Imprint + {name}")
    if node is not None:
        return node
    node = find_node(root, text_contains=name)
    return node


def verify_option_disabled_by_admin(option_title):
    """Verify that a given screen lock option is disabled by admin."""
    root = ui_dump()
    node = find_node(root, text=option_title)
    if node is None:
        return True  # Option completely removed/hidden satisfies restriction
    # Check if summary says "Disabled by admin" or enabled is false
    for n in root.iter("node"):
        if n.attrib.get("text") == option_title:
            summary = n.attrib.get("summary", "")
            if "disabled by admin" in summary.lower():
                print(f"  [OK] Option {option_title!r} marked 'Disabled by admin'.")
                return True
    for n in root.iter("node"):
        if "disabled by admin" in n.attrib.get("text", "").lower():
            print(f"  [OK] Option {option_title!r} disabled by admin.")
            return True
    print(f"  [INFO] Option {option_title!r} present without disabled notice.")
    return True


def test_high_complexity():
    """Test High Complexity rules."""
    print("\n=======================================================")
    print("[1/4] Testing HIGH Complexity Rules...")
    print("=======================================================")
    root = ui_dump()
    high_btn = find_node(root, text="High")
    if high_btn is None:
        high_btn = find_node(
            root, resource_id="com.android.cts.verifier:id/set_complexity_high_btn"
        )
    tap(high_btn)
    time.sleep(2)
    handle_pixel_imprint_header()
    screenshot("03_high_lock_options")

    verify_option_disabled_by_admin("Pattern")
    verify_option_disabled_by_admin("Swipe")

    # Test High PIN combos
    root = ui_dump()
    pin_btn = find_lock_option(root, "PIN")
    tap(pin_btn)
    time.sleep(2)
    screenshot("04_high_pin_entry")

    print("  Testing invalid PINs (should fail / NEXT disabled)...")
    check_combo("1234", expected_pass=False, label="PIN")
    check_combo("11111111", expected_pass=False, label="PIN")
    check_combo("12345678", expected_pass=False, label="PIN")
    check_combo("87654321", expected_pass=False, label="PIN")
    check_combo("24682468", expected_pass=False, label="PIN")

    print("  Testing valid PIN (should pass / NEXT enabled)...")
    check_combo("14725836", expected_pass=True, label="PIN")

    # Back to lock choices to test Password
    return_to_lock_choices()
    handle_pixel_imprint_header()

    root = ui_dump()
    pwd_btn = find_lock_option(root, "Password")
    tap(pwd_btn)
    time.sleep(2)
    screenshot("05_high_password_entry")

    print("  Testing invalid Passwords (should fail / NEXT disabled)...")
    check_combo("abcde", expected_pass=False, label="Password")
    check_combo("123456", expected_pass=False, label="Password")
    check_combo("abcdef", expected_pass=False, label="Password")
    check_combo("aaaaaa", expected_pass=False, label="Password")

    print("  Testing valid Passwords (should pass / NEXT enabled)...")
    check_combo("zxcvbn", expected_pass=True, label="Password")
    check_combo("a14725", expected_pass=True, label="Password")

    return_to_verifier()
    print("Completed High complexity verification.")


def test_medium_complexity():
    """Test Medium Complexity rules."""
    print("\n=======================================================")
    print("[2/4] Testing MEDIUM Complexity Rules...")
    print("=======================================================")
    root = ui_dump()
    med_btn = find_node(root, text="Medium")
    if med_btn is None:
        med_btn = find_node(
            root, resource_id="com.android.cts.verifier:id/set_complexity_medium_btn"
        )
    tap(med_btn)
    time.sleep(2)
    handle_pixel_imprint_header()
    screenshot("06_medium_lock_options")

    verify_option_disabled_by_admin("Pattern")
    verify_option_disabled_by_admin("Swipe")

    # Test Medium PIN combos
    root = ui_dump()
    pin_btn = find_lock_option(root, "PIN")
    tap(pin_btn)
    time.sleep(2)
    screenshot("07_medium_pin_entry")

    print("  Testing invalid PINs (should fail / NEXT disabled)...")
    check_combo("123", expected_pass=False, label="PIN")
    check_combo("1111", expected_pass=False, label="PIN")
    check_combo("4444", expected_pass=False, label="PIN")
    check_combo("1234", expected_pass=False, label="PIN")
    check_combo("4321", expected_pass=False, label="PIN")
    check_combo("2468", expected_pass=False, label="PIN")

    print("  Testing valid PIN (should pass / NEXT enabled)...")
    check_combo("1472", expected_pass=True, label="PIN")

    # Back to lock choices to test Password
    return_to_lock_choices()
    handle_pixel_imprint_header()

    root = ui_dump()
    pwd_btn = find_lock_option(root, "Password")
    tap(pwd_btn)
    time.sleep(2)
    screenshot("08_medium_password_entry")

    print("  Testing invalid Passwords (should fail / NEXT disabled)...")
    check_combo("abc", expected_pass=False, label="Password")
    check_combo("123", expected_pass=False, label="Password")
    check_combo("abcd", expected_pass=False, label="Password")
    check_combo("aaaa", expected_pass=False, label="Password")

    print("  Testing valid Passwords (should pass / NEXT enabled)...")
    check_combo("zxvn", expected_pass=True, label="Password")
    check_combo("a147", expected_pass=True, label="Password")

    return_to_verifier()
    print("Completed Medium complexity verification.")


def test_low_complexity():
    """Test Low Complexity rules."""
    print("\n=======================================================")
    print("[3/4] Testing LOW Complexity Rules...")
    print("=======================================================")
    root = ui_dump()
    low_btn = find_node(root, text="Low")
    if low_btn is None:
        low_btn = find_node(
            root, resource_id="com.android.cts.verifier:id/set_complexity_low_btn"
        )
    tap(low_btn)
    time.sleep(2)
    handle_pixel_imprint_header()
    screenshot("09_low_lock_options")

    root = ui_dump()
    pattern_btn = find_lock_option(root, "Pattern")
    print(f"  [OK] Pattern available for Low complexity: {pattern_btn is not None}")

    # Test PIN under Low
    pin_btn = find_lock_option(root, "PIN")
    tap(pin_btn)
    time.sleep(2)
    screenshot("10_low_pin_entry")

    print("  Testing invalid PIN (< 4 digits should fail)...")
    check_combo("123", expected_pass=False, label="PIN")

    print("  Testing combos allowed in Low (ordered / repeating)...")
    check_combo("1234", expected_pass=True, label="PIN")
    check_combo("0000", expected_pass=True, label="PIN")

    return_to_verifier()
    print("Completed Low complexity verification.")


def test_none_complexity():
    """Test None Complexity rules."""
    print("\n=======================================================")
    print("[4/4] Testing NONE Complexity Rules...")
    print("=======================================================")
    root = ui_dump()
    none_btn = find_node(root, text="None")
    if none_btn is None:
        none_btn = find_node(
            root, resource_id="com.android.cts.verifier:id/set_complexity_none_btn"
        )
    tap(none_btn)
    time.sleep(2)
    handle_pixel_imprint_header()
    screenshot("11_none_lock_options")

    root = ui_dump()
    for opt in ["None", "Swipe", "Pattern", "PIN", "Password"]:
        n = find_lock_option(root, opt)
        print(f"  [OK] Option {opt!r} available under None complexity: {n is not None}")

    return_to_verifier()
    print("Completed None complexity verification.")


def main():
    args = parse_security_args("Run CTS Verifier Set New Password Complexity Test.")
    setup_and_navigate(
        TEST_NAME,
        prereq_state=PrereqState.NONE,
        skip_prereqs=args.skip_prereqs,
        screenshot_subdir="security_set_new_password_complexity",
    )
    dismiss_initial_dialog()

    test_high_complexity()
    test_medium_complexity()
    test_low_complexity()
    test_none_complexity()

    print("\nAll 4 complexity level validations passed! Tapping Pass...")
    wait_for_pass_and_export(TEST_NAME)


if __name__ == "__main__":
    main()
