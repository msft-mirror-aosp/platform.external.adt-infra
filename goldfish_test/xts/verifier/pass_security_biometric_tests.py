#!/usr/bin/env python3
"""
Biometric Tests Automated Runner
Drives CTS Verifier Security -> Biometric Tests (BiometricTestList).

Architecture:
  - Each sub-test has a dedicated function (e.g. test_1a_credential_not_enrolled, etc.).
  - Prerequisite Grouping: Groups sub-tests by required credential state
    (NONE, UNENROLLED, ENROLLED) to minimize setup/teardown overhead.
  - Single-Test Isolation: Use --subtest / -t to execute an individual sub-test.
  - Natural Failure Verification: Use --skip-prereqs / -s to omit credential
    setup, verifying that tests fail naturally when prerequisites are unmet.
"""

import argparse
import os
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(SCRIPT_DIR)

from cts_common import (
    adb,
    setup,
    navigate_to,
    screenshot,
    set_screenshot_dir,
    ui_dump,
    find_node,
    find_node_containing,
    tap,
    tap_pass,
    tap_fail,
    find_pass_button,
    find_fail_button,
    is_pass_button_enabled,
    scroll_to_subtest,
    export_and_verify,
)
from security_common import (
    ensure_security_prerequisites,
    is_pin_prompt_present as _is_pin_prompt_present,
    enter_pin_on_keypad,
    wait_for_auth_prompt,
    is_fingerprint_prompt_present,
)

TEST_NAME = "Biometric Tests"
FAILED_SUBTESTS = []

# Sub-tests grouped by prerequisite state to minimize setup/teardown overhead
SUBTEST_GROUPS = [
    {
        "prereq": "PIN_ONLY_NO_BIOMETRIC",
        "tests": [
            "1a: Credential Crypto",
        ],
    },
    {
        "prereq": "PIN_ONLY_NO_BIOMETRIC",
        "tests": [
            "2a: Strong Biometrics + Crypto",
        ],
    },
    {
        "prereq": "PIN_ONLY_NO_BIOMETRIC",
        "tests": [
            "3a: Weak Biometrics",
        ],
    },
    {
        "prereq": "PIN_AND_BIOMETRIC_ENROLLED",
        "tests": [
            "4a: Cipher, Credential",
            "4b: Cipher, Biometric",
            "4c: Cipher, Biometric|Credential",
            "4d: Signature, Credential",
            "4e: Signature, Biometric",
            "4f: Signature, Biometric|Credential",
            "4g: MAC, Credential",
            "4h: MAC, Biometric",
            "4i: MAC, Biometric|Credential",
            "4j: Aead Cipher, Credential",
            "4k: Aead Cipher, Biometric",
            "4l: Aead Cipher, Biometric or Credential",
            "4m: Key Agreement, Credential",
            "4n: Key Agreement, Biometric",
            "4o: Key Agreement, Biometric or Credential",
            "4p: Credential Timed Key",
            "4q: Biometric Timed Key",
            "4r: Biometric|Credential Timed Key",
        ],
    },
]


def ensure_prerequisite_state(prereq_state, skip_prereqs=False):
    """Ensure required credentials are set up or wiped once per group."""
    ensure_security_prerequisites(prereq_state, skip_prereqs=skip_prereqs)
    # Re-launch CtsVerifier after settings changes
    adb("shell", "am", "start", "-n", "com.android.cts.verifier/.CtsVerifierActivity")
    time.sleep(5)
    navigate_to(TEST_NAME)
    time.sleep(2)


# ── Individual Sub-test Functions ─────────────────────────────────────────────


def test_1a_credential_crypto(subtest_title):
    """
    Handler for 1a: Credential Crypto.
    Taps:
      1. 'Create and unlock timed key'
      2. 'Create and unlock timed key (StrongBox)' (if supported)
    Handles PIN entry prompt ('1111') if it appears.
    Then checks if Pass button is enabled (when skip_prereqs=False) or taps Fail (when skip_prereqs=True).
    """
    print("  [1a] Executing Credential Crypto...")
    buttons_to_tap = [
        "Create and unlock timed key",
        "Create and unlock timed key (StrongBox)",
    ]
    for btn_text in buttons_to_tap:
        root = ui_dump()
        node, _ = find_node_containing(root, btn_text)
        if node is not None:
            print(f"  [1a] Tapping button: {btn_text!r}...")
            tap(node)
            time.sleep(1)

            # Wait up to 5 seconds for PIN/authentication prompt to appear
            for _ in range(5):
                new_root = ui_dump()
                if _is_pin_prompt_present(new_root):
                    print(
                        "  [1a] Authentication prompt ('Please authenticate') detected, entering '1111' on keypad..."
                    )
                    enter_pin_on_keypad("1111")
                    time.sleep(3)
                    break
                time.sleep(1)
        else:
            print(f"  [1a] Note: Button containing {btn_text!r} not present on screen.")

    # Wait up to 10 seconds for Pass button to become enabled
    root = None
    for _ in range(10):
        root = ui_dump()
        if is_pass_button_enabled(root):
            break
        time.sleep(1)

    if is_pass_button_enabled(root):
        print("  [1a] Checks succeeded -> Pass button enabled.")
        tap_pass(find_pass_button(root))
        return True
    else:
        print("  [1a] Pass button not enabled after checks -> tapping Fail.")
        fail_btn = find_fail_button(root)
        if fail_btn is not None:
            tap_fail(fail_btn)
        else:
            adb("shell", "input", "keyevent", "KEYCODE_BACK")
        return False


def enroll_fingerprint_in_current_screen(finger_id=1, max_touches=15):
    """Enrolls a fingerprint on whichever enrollment activity is currently displayed."""
    print(f"  Simulating fingerprint touches for finger ID {finger_id}...")
    for _ in range(max_touches):
        root = ui_dump()
        if _is_pin_prompt_present(root):
            print(
                "  PIN prompt detected during enrollment ('PIN is required to recover biometrics...'). Entering '1111'..."
            )
            enter_pin_on_keypad("1111")
            time.sleep(2)
            continue

        # Check for DONE button
        done_btn = find_node(root, text="DONE")
        if done_btn is not None:
            print("  Tapping DONE...")
            tap(done_btn)
            time.sleep(2)
            return True

        # Check for I AGREE / MORE / Add
        for dlg_text in ["I AGREE", "MORE", "Add", "Add fingerprint"]:
            btn = find_node(root, text=dlg_text)
            if btn is not None:
                tap(btn)
                time.sleep(1.5)
                break

        # Simulate finger touch
        adb("emu", "finger", "touch", str(finger_id), timeout=10, check=False)
        time.sleep(1.2)
    return False


def authenticate_with_biometric_or_pin(
    finger_id=1, pin="1111", expected_btn_text=None, max_attempts=6
):
    """
    Simulate fingerprint touch while checking for PIN recovery prompts
    ('PIN is required to recover biometrics after too many failed attempts').
    If expected_btn_text is given, returns True as soon as that button becomes enabled.
    """
    print(
        f"  Simulating biometric authentication (finger ID {finger_id}) with PIN recovery check..."
    )
    for _ in range(max_attempts):
        root = ui_dump()
        if expected_btn_text:
            btn, _ = find_node_containing(root, expected_btn_text)
            if btn is not None and btn.attrib.get("enabled") == "true":
                return True

        if _is_pin_prompt_present(root):
            print(
                f"  PIN recovery prompt detected ('PIN is required to recover biometrics...'). Entering PIN {pin!r}..."
            )
            enter_pin_on_keypad(pin)
            time.sleep(2)
            continue

        adb("emu", "finger", "touch", str(finger_id), timeout=10, check=False)
        time.sleep(1.2)

    if expected_btn_text:
        root = ui_dump()
        btn, _ = find_node_containing(root, expected_btn_text)
        return btn is not None and btn.attrib.get("enabled") == "true"
    return True


def run_start_enrollment_step(test_label="2a"):
    """
    Common helper for tests starting with 'Start enrollment' (e.g. 2a and 3a).
    Clicks 'Start enrollment', enters PIN if prompted, and enrolls finger 1.
    Returns True on success, or False if enrollment flow fails to open.
    """
    root = ui_dump()
    btn1, _ = find_node_containing(root, "Start enrollment")
    if btn1 is None:
        print(f"  [{test_label}] Warning: 'Start enrollment' button not found.")
        return False

    print(f"  [{test_label}] Step 1: Tapping 'Start enrollment'...")
    tap(btn1)
    time.sleep(1.5)

    # Wait up to 3 seconds for either PIN prompt or Touch sensor screen to appear
    flow_started = False
    for _ in range(3):
        new_root = ui_dump()
        if _is_pin_prompt_present(new_root):
            print(f"  [{test_label}] PIN/authentication prompt detected.")
            enter_pin_on_keypad("1111")
            time.sleep(2)
            flow_started = True
            break
        text_nodes = [n.attrib.get("text", "").lower() for n in new_root.iter("node")]
        if any(
            w in t
            for t in text_nodes
            for w in [
                "touch the sensor",
                "touch sensor",
                "fingerprint setup",
                "fingerprint",
            ]
        ):
            flow_started = True
            break
        time.sleep(1)

    if not flow_started:
        print(
            f"  [{test_label}] Failure: Enrollment flow did not open after tapping 'Start enrollment'. A fingerprint may be enrolled already."
        )
        fail_btn = find_fail_button(new_root)
        if fail_btn is not None:
            tap_fail(fail_btn)
        else:
            adb("shell", "input", "keyevent", "KEYCODE_BACK")
        return False

    # Complete Pixel imprint enrollment with finger 1
    return enroll_fingerprint_in_current_screen(finger_id=1)


def test_2a_strong_biometrics_crypto(subtest_title):
    """
    Handler for 2a: Strong Biometrics + Crypto.
    4-part flow:
      1. Click 'Start enrollment'.
         - If skip_prereqs=True (or finger already enrolled), button 2 does not enable -> fail.
         - Otherwise, prompts for PIN -> enters Pixel imprint -> enrolls finger 1 -> returns with button 2 enabled.
      2. Click button 2 ('Authenticate Crypto (without StrongBox)').
         - Prompts for finger 1 -> simulate touch -> button 3 becomes enabled.
      3. Click button 3 ('Authenticate Key Invalidated') - Part 1.
         - Instruction dialog -> click 'Continue'.
         - Go to Android Settings -> enroll finger 2 (which invalidates Keystore keys) -> return to 2a.
      4. Click button 3 ('Authenticate Key Invalidated') - Part 2.
         - Instruction dialog -> click 'Continue'.
         - Pass button becomes enabled -> tap Pass.
    """
    print("  [2a] Executing Strong Biometrics + Crypto...")

    # ── Step 1: Start enrollment (common helper) ──────────────────────────────
    if not run_start_enrollment_step(test_label="2a"):
        return False

    time.sleep(2)
    root = ui_dump()
    btn2, _ = find_node_containing(root, "Authenticate Crypto")

    if btn2 is None or btn2.attrib.get("enabled") != "true":
        print(
            "  [2a] Failure: Button 2 ('Authenticate Crypto') not enabled. A fingerprint may be enrolled already."
        )
        fail_btn = find_fail_button(root)
        if fail_btn is not None:
            tap_fail(fail_btn)
        else:
            adb("shell", "input", "keyevent", "KEYCODE_BACK")
        return False

    # ── Step 2: Authenticate Crypto (without StrongBox) ───────────────────────
    print(
        "  [2a] Step 2: Tapping button 2 ('Authenticate Crypto (without StrongBox)')..."
    )
    tap(btn2)
    time.sleep(1.5)
    if not authenticate_with_biometric_or_pin(
        finger_id=1, expected_btn_text="Authenticate Key Invalidated"
    ):
        print(
            "  [2a] Failure: Button 3 ('Authenticate Key Invalidated') not enabled after finger 1."
        )
        fail_btn = find_fail_button(root)
        if fail_btn is not None:
            tap_fail(fail_btn)
        return False

    # ── Step 3: Authenticate Key Invalidated (Part 1 - Invalidate Keys) ───────
    print("  [2a] Enrolling finger 2 in Settings to invalidate cryptographic keys...")
    os.system(f"{sys.executable} {os.path.join(SCRIPT_DIR, 'enroll_fingerprint.py')} 2")

    # Return to CtsVerifier and check if we are already inside 2a: Strong Biometrics + Crypto
    adb("shell", "am", "start", "-n", "com.android.cts.verifier/.CtsVerifierActivity")
    time.sleep(4)
    root = ui_dump()
    btn3, _ = find_node_containing(root, "Authenticate Key Invalidated")
    if btn3 is None:
        print("  [2a] Re-navigating to 2a: Strong Biometrics + Crypto...")
        node_main, _ = find_node_containing(root, TEST_NAME)
        if node_main is not None:
            tap(node_main)
            time.sleep(2)
        scroll_to_subtest("2a: Strong Biometrics + Crypto")
        root = ui_dump()
        node_2a, _ = find_node_containing(root, "2a: Strong Biometrics + Crypto")
        if node_2a is not None:
            tap(node_2a)
            time.sleep(2)
    else:
        print(
            "  [2a] CTS Verifier restored directly to 2a: Strong Biometrics + Crypto screen."
        )

    print(
        "  [2a] Step 3: Tapping button 3 ('Authenticate Key Invalidated') first time..."
    )
    tap(btn3)
    time.sleep(1.5)
    # Dismiss instructions dialog with 'Continue'
    root = ui_dump()
    cont_btn = find_node(root, text="Continue")
    if cont_btn is None:
        cont_btn = find_node(root, text="CONTINUE")
    if cont_btn is not None:
        print("  [2a] Tapping 'Continue' on instructions dialog...")
        tap(cont_btn)
        time.sleep(1.5)

    # ── Step 4: Authenticate Key Invalidated (Part 2 - Verify Pass) ───────────
    print(
        "  [2a] Step 4: Tapping button 3 ('Authenticate Key Invalidated') second time..."
    )
    root = ui_dump()
    btn3, _ = find_node_containing(root, "Authenticate Key Invalidated")
    if btn3 is not None:
        tap(btn3)
        time.sleep(1.5)

    root = ui_dump()
    cont_btn = find_node(root, text="Continue")
    if cont_btn is None:
        cont_btn = find_node(root, text="CONTINUE")
    if cont_btn is not None:
        print("  [2a] Tapping 'Continue' on instructions dialog...")
        tap(cont_btn)
        time.sleep(2)

    root = ui_dump()
    if is_pass_button_enabled(root):
        print("  [2a] All 4 steps succeeded -> Pass button enabled!")
        tap_pass(find_pass_button(root))
        return True
    else:
        print("  [2a] Pass button not enabled after Step 4 -> tapping Fail.")
        tap_fail(find_fail_button(root))
        return False


def test_3a_weak_biometrics(subtest_title):
    """
    Handler for 3a: Weak Biometrics.
    1. Click 'Start enrollment' -> prompts for PIN -> enters Pixel imprint -> enrolls finger 1.
    2. Once finger is enrolled, returns to 3a screen and Pass button is available.
    """
    print("  [3a] Executing Weak Biometrics...")
    if not run_start_enrollment_step(test_label="3a"):
        return False

    time.sleep(2)
    root = ui_dump()
    if is_pass_button_enabled(root):
        print("  [3a] Enrollment step succeeded -> Pass button enabled!")
        tap_pass(find_pass_button(root))
        return True
    else:
        print("  [3a] Pass button not enabled after enrollment -> tapping Fail.")
        tap_fail(find_fail_button(root))
        return False


SECTION4_BUTTON_TEXTS = [
    "auth-per-use key with credential",
    "auth-per-use key with credential (strongbox)",
    "auth-per-use key with biometric",
    "auth-per-use key with biometric (strongbox)",
    "time-based key with credential",
    "time-based key with credential (strongbox)",
    "time-based key with biometric",
    "time-based key with biometric (strongbox)",
]


def test_section4_user_authentication(subtest_title):
    """
    Universal automated handler for Section 4 tests (4a through 4r).
    Iteratively finds and taps any visible test button, handling PIN and/or Biometric
    authentication prompts until the Pass button becomes enabled.
    """
    print(f"  [{subtest_title}] Executing universal User Authentication test...")
    max_iterations = 40
    for _ in range(max_iterations):
        root = ui_dump()

        # Check if Pass button is already enabled -> all test buttons completed!
        if is_pass_button_enabled(root):
            print(
                f"  [{subtest_title}] All test buttons completed -> Pass button enabled!"
            )
            tap_pass(find_pass_button(root))
            return True

        # Find the first visible test button that is enabled
        target_node = None
        disabled_button_present = False
        for b_text in SECTION4_BUTTON_TEXTS:
            node, _ = find_node_containing(root, b_text)
            if node is not None:
                if node.attrib.get("enabled", "true") == "true":
                    target_node = node
                    break
                else:
                    disabled_button_present = True

        if target_node is None:
            # Maybe an authentication prompt is already visible from a previous tap?
            if _is_pin_prompt_present(root):
                print(f"  [{subtest_title}] PIN prompt detected.")
                enter_pin_on_keypad("1111")
                time.sleep(2)
                continue
            text_nodes = [n.attrib.get("text", "").lower() for n in root.iter("node")]
            if any(
                w in t
                for t in text_nodes
                for w in [
                    "touch the sensor",
                    "touch the fingerprint sensor",
                    "fingerprint sensor",
                    "touch sensor",
                ]
            ):
                print(
                    f"  [{subtest_title}] Biometric prompt detected, simulating finger 1..."
                )
                adb("emu", "finger", "touch", "1", timeout=10, check=False)
                time.sleep(2)
                continue

            if disabled_button_present:
                print(
                    f"  [{subtest_title}] Test button(s) present but temporarily disabled, waiting..."
                )
                time.sleep(2)
                continue

            print(
                f"  [{subtest_title}] No more test buttons found and Pass not enabled. Tapping Fail."
            )
            tap_fail(find_fail_button(root))
            return False

        print(
            f"  [{subtest_title}] Tapping button: {target_node.attrib.get('text', '')!r}..."
        )
        tap(target_node)
        time.sleep(1.5)

        # Handle any authentication prompt (PIN or Biometric) that appeared after tapping
        prompt_type, new_root = wait_for_auth_prompt(timeout=10.0)
        if prompt_type == "pin":
            print(f"  [{subtest_title}] PIN prompt detected after tapping button.")
            enter_pin_on_keypad("1111")
            time.sleep(2)
            # After entering PIN, also check if BiometricPrompt is still waiting
            after_pin_root = ui_dump()
            if is_fingerprint_prompt_present(after_pin_root):
                print(
                    f"  [{subtest_title}] Biometric prompt also detected after PIN entry, simulating finger 1..."
                )
                adb("emu", "finger", "touch", "1", timeout=10, check=False)
                time.sleep(2)
        elif prompt_type == "biometric":
            print(
                f"  [{subtest_title}] Biometric prompt detected after tapping button, simulating finger 1..."
            )
            adb("emu", "finger", "touch", "1", timeout=10, check=False)
            time.sleep(2)
        else:
            print(
                f"  [{subtest_title}] No prompt detected after tapping button within 10s."
            )

        time.sleep(1)

    print(
        f"  [{subtest_title}] Timed out after {max_iterations} iterations without Pass enabling."
    )
    tap_fail(find_fail_button(root))
    return False


# Dispatcher mapping sub-test prefixes to their dedicated functions
SUBTEST_HANDLERS = {
    "1a": test_1a_credential_crypto,
    "2a": test_2a_strong_biometrics_crypto,
    "3a": test_3a_weak_biometrics,
    "4a": test_section4_user_authentication,
    "4b": test_section4_user_authentication,
    "4c": test_section4_user_authentication,
    "4d": test_section4_user_authentication,
    "4e": test_section4_user_authentication,
    "4f": test_section4_user_authentication,
    "4g": test_section4_user_authentication,
    "4h": test_section4_user_authentication,
    "4i": test_section4_user_authentication,
    "4j": test_section4_user_authentication,
    "4k": test_section4_user_authentication,
    "4l": test_section4_user_authentication,
    "4m": test_section4_user_authentication,
    "4n": test_section4_user_authentication,
    "4o": test_section4_user_authentication,
    "4p": test_section4_user_authentication,
    "4q": test_section4_user_authentication,
    "4r": test_section4_user_authentication,
}


def run_subtest(subtest_title, skip_prereqs=False):
    """Navigate to and execute a single biometric sub-test using its dedicated function."""
    print(f"\n=======================================================")
    print(f"[SUBTEST] Starting: {subtest_title} (skip_prereqs={skip_prereqs})")
    print(f"=======================================================")
    time.sleep(2)
    screenshot(f"open_{subtest_title}")

    prefix = subtest_title.split(":")[0].strip().lower()
    handler = SUBTEST_HANDLERS.get(prefix)
    if handler is None:
        raise NotImplementedError(
            f"No handler implemented for subtest: {subtest_title}"
        )

    try:
        res = handler(subtest_title)
        if res is False:
            FAILED_SUBTESTS.append(subtest_title)
            return False
        return True
    except Exception as e:
        print(f"  [ERROR] Sub-test {subtest_title!r} failed: {e}")
        screenshot(f"fail_{subtest_title}")
        root = ui_dump()
        fail_btn = find_fail_button(root)
        if fail_btn is not None:
            tap_fail(fail_btn)
        else:
            adb("shell", "input", "keyevent", "KEYCODE_BACK")
        FAILED_SUBTESTS.append(subtest_title)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="CTS Verifier Biometric Tests Automation"
    )
    parser.add_argument(
        "--skip-prereqs",
        "--skip_prereqs",
        "-s",
        action="store_true",
        default=bool(
            os.environ.get("BIOMETRIC_SKIP_PREREQS", "0") == "1"
            or os.environ.get("CTS_SECURITY_SKIP_PREREQS")
        ),
        help="Skip prerequisite credential setup to verify tests naturally fail.",
    )
    parser.add_argument(
        "--subtest",
        "-t",
        action="append",
        default=None,
        help="Optional: Run specific sub-test(s) by prefix or title (e.g. '-t 1a' or '-t 1a,2a,3a'). Can be repeated.",
    )
    args = parser.parse_args()

    set_screenshot_dir("biometric_tests")
    setup()

    navigate_to(TEST_NAME)
    time.sleep(3)
    screenshot("01_biometric_test_list_opened")

    requested_patterns = []
    if args.subtest:
        for entry in args.subtest:
            for part in entry.split(","):
                part = part.strip().lower()
                if part:
                    requested_patterns.append(part)
    elif os.environ.get("BIOMETRIC_SUBTEST"):
        for part in os.environ.get("BIOMETRIC_SUBTEST").split(","):
            part = part.strip().lower()
            if part:
                requested_patterns.append(part)

    groups_to_run = SUBTEST_GROUPS
    if requested_patterns:
        filtered = []
        for g in SUBTEST_GROUPS:
            matches = [
                t
                for t in g["tests"]
                if any(pat in t.lower() for pat in requested_patterns)
            ]
            if matches:
                filtered.append({"prereq": g["prereq"], "tests": matches})
        groups_to_run = filtered
        if not groups_to_run:
            print(
                f"Error: No sub-tests matched requested patterns: {requested_patterns}"
            )
            sys.exit(1)

    for group in groups_to_run:
        prereq_ensured = False
        for subtest in group["tests"]:
            # Check if test is present on UI before triggering prerequisite setup or entering
            node = scroll_to_subtest(subtest)
            if node is None:
                print(f"  [SKIP] Sub-test not present on UI: {subtest!r}")
                continue

            # Ensure prerequisites once before the first present test in this group
            if not prereq_ensured:
                ensure_prerequisite_state(
                    group["prereq"], skip_prereqs=args.skip_prereqs
                )
                prereq_ensured = True
                node = scroll_to_subtest(subtest)
                if node is None:
                    print(
                        f"  [SKIP] Sub-test {subtest!r} no longer present after prerequisite setup."
                    )
                    continue

            print(
                f"  Found sub-test {subtest!r} at {node.attrib['bounds']}, tapping..."
            )
            tap(node)
            run_subtest(subtest, skip_prereqs=args.skip_prereqs)

    print("\nAll sub-test iterations completed.")
    screenshot("02_final_biometric_test_list")

    if FAILED_SUBTESTS:
        print(
            f"\n>>> FAILED: {len(FAILED_SUBTESTS)} sub-test(s) failed: {', '.join(FAILED_SUBTESTS)}"
        )
        sys.exit(1)

    if not requested_patterns and not args.skip_prereqs:
        root = ui_dump()
        if is_pass_button_enabled(root):
            print("\nAll sub-tests passed! Tapping parent Pass and verifying report...")
            tap_pass(find_pass_button(root))
            export_and_verify(TEST_NAME)
            sys.exit(0)
        else:
            print(
                "\n[WARN] Parent Pass button is not enabled. Check sub-test failures above."
            )
            sys.exit(1)

    print("\n>>> PASSED: All executed sub-test(s) completed successfully.")
    sys.exit(0)


if __name__ == "__main__":
    main()
