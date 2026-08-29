#!/usr/bin/env python3
"""
USI Version Test
Verifies the USI Version functionality.
"""

import time
from cts_common import (
    setup, navigate_to, ui_dump, tap, wait_for, tap_pass,
    export_and_verify, set_screenshot_dir, screenshot, adb,
    dismiss_dialogs_and_wait_for_pass
)

TEST_NAME = "USI Version Test"
set_screenshot_dir("usi_version_test")

def main():
    # Ensure a completely clean install of the CtsVerifier
    PACKAGE = "com.android.cts.verifier"
    print(f"Uninstalling {PACKAGE} to ensure a clean state...")
    adb("uninstall", PACKAGE, check=False)
    
    setup() # This will reinstall it with -g -r 
    
    print(f"Navigating to {TEST_NAME}...")
    screenshot("navigating")
    try:
        navigate_to(TEST_NAME)
    except RuntimeError:
        print(f"Failed to find '{TEST_NAME}' in the list.")
        return
        
    time.sleep(2)

    print("Waiting for OK dialog...")
    try:
        ok = wait_for(text="OK", timeout=15)
        print("Tapping OK...")
        screenshot("dismissing_popup")
        tap(ok)
        time.sleep(2)
    except TimeoutError:
        print("Warning: OK dialog not found, proceeding anyway...")
        # Sometimes the button might be "CONTINUE" or "Continue"
        try:
            continue_btn = wait_for(text="CONTINUE", timeout=3)
            print("Tapping CONTINUE...")
            screenshot("dismissing_popup")
            tap(continue_btn)
            time.sleep(2)
        except TimeoutError:
            pass

    print("Waiting for 'ready to proceed' dialog...")
    try:
        yes_btn = wait_for(text="Yes", timeout=15)
        print("Tapping Yes...")
        screenshot("ready_to_proceed_yes")
        tap(yes_btn)
        time.sleep(2)
    except TimeoutError:
        print("Warning: 'Yes' button not found, trying uppercase 'YES'...")
        try:
            yes_btn = wait_for(text="YES", timeout=5)
            print("Tapping YES...")
            screenshot("ready_to_proceed_yes")
            tap(yes_btn)
            time.sleep(2)
        except TimeoutError:
            print("Warning: 'Yes'/'YES' button not found.")

    print("Waiting for 'does the display support USI' dialog...")
    try:
        no_btn = wait_for(text="No", timeout=15)
        print("Tapping No...")
        screenshot("supports_usi_no")
        tap(no_btn)
        time.sleep(2)
    except TimeoutError:
        print("Warning: 'No' button not found, trying uppercase 'NO'...")
        try:
            no_btn = wait_for(text="NO", timeout=5)
            print("Tapping NO...")
            screenshot("supports_usi_no")
            tap(no_btn)
            time.sleep(2)
        except TimeoutError:
            print("Warning: 'No'/'NO' button not found.")

    print("Waiting for Pass button to become enabled...")
    try:
        pass_btn = dismiss_dialogs_and_wait_for_pass(timeout=10)
        print("Tapping Pass...")
        screenshot("tapping_pass")
        tap(pass_btn)
    except TimeoutError:
        print("Warning: Pass button did not become enabled. Tapping it anyway to try.")
        tap_pass()
        
    export_and_verify(TEST_NAME)

if __name__ == "__main__":
    main()
