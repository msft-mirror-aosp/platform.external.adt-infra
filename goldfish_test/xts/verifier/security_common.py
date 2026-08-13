#!/usr/bin/env python3
"""
Common helpers and state management for CTS Verifier Security tests.
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
    ui_dump,
    find_node,
    find_node_containing,
    tap,
    tap_pass,
    tap_fail,
    find_pass_button,
    find_fail_button,
    is_pass_button_enabled,
    screenshot,
    set_screenshot_dir,
    export_and_verify,
)


class PrereqState:
    """Standard credential prerequisite states for Security tests."""

    NONE = "NONE"
    UNENROLLED = "UNENROLLED"
    PIN_ONLY = "PIN_ONLY"
    PIN_ONLY_NO_BIOMETRIC = "PIN_ONLY_NO_BIOMETRIC"
    PIN_AND_FINGERPRINT = "PIN_AND_FINGERPRINT"
    PIN_AND_BIOMETRIC_ENROLLED = "PIN_AND_BIOMETRIC_ENROLLED"
    PIN_AND_TWO_FINGERPRINTS = "PIN_AND_TWO_FINGERPRINTS"


def parse_security_args(description="Run CTS Verifier Security Test.", env_var=None):
    """Standardized CLI argument parser for Security tests."""
    parser = argparse.ArgumentParser(description=description)

    default_val = False
    if env_var and os.environ.get(env_var) in ["1", "true", "True"]:
        default_val = True
    elif os.environ.get("CTS_SECURITY_SKIP_PREREQS") in ["1", "true", "True"]:
        default_val = True

    parser.add_argument(
        "--skip-prereqs",
        "--skip_prereqs",
        "-s",
        action="store_true",
        default=default_val,
        help="Skip prerequisite lockscreen and biometric setup to verify natural test failure.",
    )
    args, _ = parser.parse_known_args()
    return args


def clear_all_credentials():
    """Clear all lockscreen PINs, passwords, and enrolled fingerprints."""
    adb("shell", "am", "force-stop", "com.android.settings", check=False)
    delete_pin_script = os.path.join(SCRIPT_DIR, "delete_pin.py")
    res = os.system(f"{sys.executable} {delete_pin_script}")
    time.sleep(1)
    return res == 0


def ensure_security_prerequisites(prereq_state, skip_prereqs=False):
    """
    Ensure the device is set to the specified prerequisite credential state
    (e.g., NONE, PIN_ONLY, PIN_AND_FINGERPRINT).
    If skip_prereqs is True, setup is skipped to allow natural failure verification.
    """
    if skip_prereqs:
        print(
            f"  [PREREQ] --skip-prereqs set: Skipping prerequisite setup for state {prereq_state!r}."
        )
        return

    print(f"  [PREREQ] Configuring prerequisite state: {prereq_state}...")
    adb("shell", "am", "force-stop", "com.android.settings", check=False)
    clear_all_credentials()

    create_pin_script = os.path.join(SCRIPT_DIR, "create_pin.py")
    enroll_fp_script = os.path.join(SCRIPT_DIR, "enroll_fingerprint.py")

    if prereq_state in [PrereqState.NONE, PrereqState.UNENROLLED]:
        print("  [PREREQ] Clean slate (lockscreen None, zero fingerprints).")
    elif prereq_state in [PrereqState.PIN_ONLY, PrereqState.PIN_ONLY_NO_BIOMETRIC]:
        print("  [PREREQ] Setting up PIN '1111' (zero fingerprints)...")
        os.system(f"{sys.executable} {create_pin_script} 1111")
    elif prereq_state in [
        PrereqState.PIN_AND_FINGERPRINT,
        PrereqState.PIN_AND_BIOMETRIC_ENROLLED,
    ]:
        print("  [PREREQ] Setting up PIN '1111' and enrolling Fingerprint 1...")
        os.system(f"{sys.executable} {create_pin_script} 1111")
        os.system(f"{sys.executable} {enroll_fp_script} 1")
    elif prereq_state == PrereqState.PIN_AND_TWO_FINGERPRINTS:
        print("  [PREREQ] Setting up PIN '1111' and enrolling Fingerprints 1 & 2...")
        os.system(f"{sys.executable} {create_pin_script} 1111")
        os.system(f"{sys.executable} {enroll_fp_script} 1")
        os.system(f"{sys.executable} {enroll_fp_script} 2")

    time.sleep(2)


def setup_and_navigate(
    test_name, prereq_state=None, skip_prereqs=None, screenshot_subdir=None
):
    """Initialize app, optionally ensure prerequisites, and navigate to the specified test."""
    if screenshot_subdir:
        set_screenshot_dir(screenshot_subdir)
    if prereq_state is not None:
        if skip_prereqs is None:
            skip_prereqs = parse_security_args().skip_prereqs
        ensure_security_prerequisites(prereq_state, skip_prereqs=skip_prereqs)
    setup()
    screenshot("01_app_launched")
    navigate_to(test_name)
    time.sleep(2)
    screenshot("02_test_opened")


def dismiss_initial_dialog(timeout=3):
    """Dismiss initial info or instruction dialog ('OK' / 'Allow') if present."""
    root = ui_dump()
    ok_btn = find_node(root, text="OK")
    if ok_btn is not None:
        print("  Dismissing initial info dialog...")
        tap(ok_btn)
        time.sleep(1)
        return True
    return False


def is_pin_prompt_present(root):
    """
    Multi-layered PIN prompt detection across SystemUI Keyguard pads and Settings PIN entries.
    """
    # 1. Broad structural signals
    for node in root.iter("node"):
        res_id = node.attrib.get("resource-id", "").lower()
        desc = node.attrib.get("content-desc", "").lower()
        if any(
            w in res_id
            for w in [
                "cred_pin_pad",
                "compose_credential_view",
                "pin_entry",
                "password_entry",
                "lockpassword",
            ]
        ):
            return True
        if any(w in desc for w in ["pin area", "pin entry"]):
            return True

    # 2. Token-based matching on text
    auth_verbs = {
        "enter",
        "confirm",
        "re-enter",
        "reenter",
        "verify",
        "required",
        "use",
        "device",
        "verifies",
    }
    for node in root.iter("node"):
        text = node.attrib.get("text", "").lower()
        if not text:
            continue
        words = set(
            text.replace("'", " ")
            .replace("-", " ")
            .replace(".", " ")
            .replace(":", " ")
            .split()
        )
        if "pin" in words and (words & auth_verbs):
            return True

    # 3. Helper subtitle signals
    for node in root.iter("node"):
        text = node.attrib.get("text", "").lower()
        if "pin verifies" in text or "pin required" in text:
            return True

    return False


def enter_pin_on_keypad(pin="1111"):
    """Enter a PIN on the on-screen keypad and submit."""
    print(f"  Entering PIN {pin!r} on keypad...")
    root = ui_dump()
    for digit in pin:
        digit_node = find_node(root, text=digit)
        if digit_node is None:
            digit_node, _ = find_node_containing(root, digit)
        if digit_node is not None:
            tap(digit_node)
            time.sleep(0.3)
        else:
            adb("shell", "input", "text", digit)
            time.sleep(0.3)

    time.sleep(0.5)
    root = ui_dump()
    enter_btn = find_node(root, content_desc="Enter")
    if enter_btn is None:
        enter_btn = find_node(root, text="Enter")
    if enter_btn is not None:
        print("  Tapping keypad Enter button...")
        tap(enter_btn)
    else:
        adb("shell", "input", "keyevent", "KEYCODE_ENTER")
    time.sleep(2)


def is_fingerprint_prompt_present(root):
    """Check if a fingerprint or biometric authentication prompt is visible on screen."""
    keywords = [
        "touch the fingerprint sensor",
        "touch the sensor",
        "touch sensor",
        "fingerprint sensor",
        "confirm your fingerprint",
        "authenticate now with fingerprint",
        "fingerprint",
        "biometric_prompt",
        "biometric_icon",
    ]
    for node in root.iter("node"):
        text = node.attrib.get("text", "").lower()
        desc = node.attrib.get("content-desc", "").lower()
        res_id = node.attrib.get("resource-id", "").lower()
        if any(k in text or k in desc or k in res_id for k in keywords):
            return True
    return False


def wait_for_fingerprint_prompt_and_touch(finger_id=1, timeout=10):
    """
    Wait for a BiometricPrompt or fingerprint authentication request and simulate finger touch.
    """
    print("  Waiting for fingerprint authentication prompt...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        root = ui_dump()
        if is_fingerprint_prompt_present(root):
            print(
                f"  Fingerprint prompt detected. Simulating touch for Finger {finger_id}..."
            )
            screenshot("fingerprint_prompt_visible")
            adb("emu", "finger", "touch", str(finger_id), check=False)
            time.sleep(2)
            screenshot("fingerprint_touched")
            return True
        time.sleep(1)

    print(
        f"  [WARN] Fingerprint prompt text not detected within {timeout}s; attempting touch anyway..."
    )
    adb("emu", "finger", "touch", str(finger_id), check=False)
    time.sleep(2)
    return False


def tap_button_or_fail(button_text, resource_id=None, timeout=5):
    """Find a button by text or resource ID, tap it, or tap Fail on error."""
    print(f"  Finding button: {button_text!r}...")
    root = ui_dump()
    btn = find_node(root, text=button_text)
    if btn is None:
        btn, _ = find_node_containing(root, button_text)
    if btn is None and resource_id:
        for n in root.iter("node"):
            if resource_id in n.attrib.get("resource-id", ""):
                btn = n
                break

    if btn is None or btn.attrib.get("enabled", "true") != "true":
        print(
            f"  [ERROR] Button {button_text!r} not found or disabled. Tapping Fail..."
        )
        screenshot("button_missing_or_disabled")
        fail_btn = find_fail_button(ui_dump())
        if fail_btn is not None:
            tap_fail(fail_btn)
        sys.exit(1)

    print(f"  Tapping button {button_text!r} at {btn.attrib['bounds']}...")
    tap(btn)
    time.sleep(2)
    return btn


def wait_for_auth_prompt(timeout=10.0, poll_interval=0.5):
    """
    Polls the UI until either a Biometric Prompt (Fingerprint) or Device Credential Prompt (PIN) appears.

    Returns:
        (prompt_type, root): ('biometric' | 'pin' | None, root_element)
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        root = ui_dump()
        if is_fingerprint_prompt_present(root):
            return "biometric", root
        if is_pin_prompt_present(root):
            return "pin", root
        time.sleep(poll_interval)
    return None, None


def wait_for_pass_and_export(test_name, timeout=20, exit_on_complete=True):
    """
    Poll for the Pass button to become enabled, tap it, and export/verify the report.
    If the Pass button fails to enable within timeout, taps Fail and exits with code 1.
    """
    print(f"  Waiting for Pass button to become enabled (timeout {timeout}s)...")
    pass_btn = None
    deadline = time.time() + timeout
    while time.time() < deadline:
        root = ui_dump()
        if is_pass_button_enabled(root):
            pass_btn = find_pass_button(root)
            break
        time.sleep(1)

    screenshot("after_test_execution")
    if pass_btn is not None:
        print("  Pass button is enabled! Tapping Pass...")
        screenshot("tapping_pass")
        tap_pass(pass_btn)
        time.sleep(2)
    else:
        print(
            f"  [ERROR] Pass button did not become enabled within {timeout}s. Tapping Fail..."
        )
        screenshot("error_pass_not_enabled")
        fail_btn = find_fail_button(ui_dump())
        if fail_btn is not None:
            tap_fail(fail_btn)
        sys.exit(1)

    export_and_verify(test_name)
    screenshot("export_done")
    print(f"\n>>> PASSED: {test_name}")
    if exit_on_complete:
        sys.exit(0)
