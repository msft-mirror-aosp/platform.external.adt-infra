#!/usr/bin/env python3
"""
Camera Flashlight Test (CAMERA section)

UI Flow (CameraFlashlightActivity.java):
1. Launch CtsVerifier and navigate to 'Camera Flashlight'.
2. Dismiss any initial Info dialog ("OK" button) if shown.
3. For each camera with `FLASH_INFO_AVAILABLE`:
   - State `NOT_STARTED` / `RESPONDED_OFF_CORRECTLY`: `flash_instruction_button` is enabled.
     Tap `flash_instruction_button` to turn torch ON for the next camera (or transition to
     `ALL_PASSED` when all cameras are tested).
   - State `TESTING_ON`: `flash_on_button` and `flash_off_button` are enabled.
     Tap `flash_on_button` ("On") to confirm the torch is on -> transitions to
     `RESPONDED_ON_CORRECTLY`.
   - State `RESPONDED_ON_CORRECTLY`: `flash_instruction_button` is enabled.
     Tap `flash_instruction_button` to turn torch OFF -> transitions to `TESTING_OFF`.
   - State `TESTING_OFF`: `flash_on_button` and `flash_off_button` are enabled.
     Tap `flash_off_button` ("Off") to confirm the torch is off -> transitions to
     `RESPONDED_OFF_CORRECTLY`.
4. Once `ALL_PASSED` is reached, `pass_button` becomes enabled.
5. Tap Pass and export/verify the test results.
"""

import os
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.append(SCRIPT_DIR)

from cts_common import (
    export_and_verify,
    find_node,
    navigate_to,
    screenshot,
    set_screenshot_dir,
    setup,
    tap,
    tap_pass,
    ui_dump,
)

TEST_NAME = "Camera Flashlight"
set_screenshot_dir("camera_flashlight_test")


def dismiss_initial_dialogs():
    """Dismiss any initial OK info dialog if present."""
    for _ in range(3):
        root = ui_dump()
        ok_btn = find_node(root, text="OK")
        if ok_btn is not None:
            print("  Dismissing dialog via 'OK' button...")
            tap(ok_btn)
            time.sleep(1)
        else:
            break


def run_flashlight_state_machine(max_steps=30):
    """Drive the CameraFlashlightActivity state machine until Pass button is enabled."""
    expect_on = True  # First query for each camera is TESTING_ON, second is TESTING_OFF

    for step in range(max_steps):
        root = ui_dump()

        # Check if Pass button is enabled
        pass_btn = find_node(root, content_desc="Pass")
        if pass_btn is None:
            pass_btn = find_node(
                root, resource_id="com.android.cts.verifier:id/pass_button"
            )
        if pass_btn is not None and pass_btn.attrib.get("enabled") == "true":
            print("  Pass button is enabled!")
            return pass_btn

        instr_btn = find_node(
            root, resource_id="com.android.cts.verifier:id/flash_instruction_button"
        )
        on_btn = find_node(
            root, resource_id="com.android.cts.verifier:id/flash_on_button"
        )
        off_btn = find_node(
            root, resource_id="com.android.cts.verifier:id/flash_off_button"
        )

        if instr_btn is not None and instr_btn.attrib.get("enabled") == "true":
            print(
                f"  Step {step}: tapping flash_instruction_button ({instr_btn.attrib.get('text')!r})..."
            )
            tap(instr_btn)
            time.sleep(1.5)
            continue

        if (
            on_btn is not None
            and off_btn is not None
            and on_btn.attrib.get("enabled") == "true"
            and off_btn.attrib.get("enabled") == "true"
        ):
            if expect_on:
                print(f"  Step {step}: tapping flash_on_button ('On')...")
                tap(on_btn)
                expect_on = False
            else:
                print(f"  Step {step}: tapping flash_off_button ('Off')...")
                tap(off_btn)
                expect_on = True
            time.sleep(1.5)
            continue

        time.sleep(1)

    raise TimeoutError(
        "Timed out waiting for enabled Pass button in Camera Flashlight test"
    )


def main():
    setup()
    print("Navigating to test...")
    screenshot("navigating_to_test")
    navigate_to(TEST_NAME)
    time.sleep(2)
    screenshot("activity_launched")

    dismiss_initial_dialogs()
    screenshot("dialogs_dismissed")

    print("Running Camera Flashlight state machine...")
    pass_btn = run_flashlight_state_machine()
    screenshot("pass_enabled")

    print("Tapping Pass...")
    tap_pass(pass_btn)
    screenshot("pass_tapped")

    export_and_verify(TEST_NAME)
    screenshot("export_done")


if __name__ == "__main__":
    main()
