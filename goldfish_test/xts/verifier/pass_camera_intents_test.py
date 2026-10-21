#!/usr/bin/env python3
"""
Camera Intents Test (CAMERA section)

UI Flow across all 8 stages of CameraIntentsActivity:
- Before launching Camera Intents:
  Grant camera/location permissions to `com.android.camera2`, enable device-wide location, and
  revoke location permissions from `com.android.cts.verifier` (per Stage 0 instructions).
- Stage 0 (1 of 8 - Application Picture):
  Tap Start Test, launch STILL_IMAGE_CAMERA intent, capture photo, press Back to return to
  existing CameraIntentsActivity instance, tap Pass.
- Stage 1 (2 of 8 - Application Video):
  Tap Start Test, launch VIDEO_CAMERA intent, record video, press Back to return to
  existing CameraIntentsActivity instance, tap Pass.
- Stage 2 (3 of 8 - Intent Picture):
  Tap Start Test, capture & confirm photo in camera intent activity, tap Pass.
- Stage 3 (4 of 8 - Intent Picture Secure):
  Tap Start Test, capture & confirm photo in secure camera intent activity, tap Pass.
- Stage 4 (5 of 8 - Intent Motion Photo):
  If Pass is already enabled (intent unsupported), tap Pass; otherwise capture & confirm motion photo.
- Stage 5 (6 of 8 - Intent Motion Photo Secure):
  If Pass is already enabled (intent unsupported), tap Pass; otherwise capture & confirm motion photo.
- Stage 6 (7 of 8 - Intent Picture Location Attack):
  Tap Start Test -> Settings App Info -> tap 'Storage & cache' -> tap 'Clear storage' (invokes
  ManageSpaceActivity -> ACTION_IMAGE_CAPTURE) -> capture & confirm photo -> navigate back to CTS
  Verifier with Back button -> tap Pass.
- Stage 7 (8 of 8 - Intent Video):
  Tap Start Test -> record & confirm video -> grant location permissions back to CTS Verifier and
  trigger onResume -> tap Pass.
"""

import os
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.append(SCRIPT_DIR)

from cts_common import (
    ACTIVITY,
    adb,
    export_and_verify,
    find_node,
    navigate_to,
    screenshot,
    set_screenshot_dir,
    setup,
    tap,
    ui_dump,
)

TEST_NAME = "Camera Intents"
set_screenshot_dir("camera_intents_test")


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


def configure_initial_permissions():
    """Follow Stage 0 instructions: enable camera location, revoke CTS Verifier location."""
    print("  Configuring permissions per Stage 0 instructions...")
    adb("shell", "settings", "put", "secure", "location_mode", "3", check=False)
    adb("emu", "geo", "fix", "-122.084", "37.422", check=False)
    for perm in (
        "android.permission.CAMERA",
        "android.permission.RECORD_AUDIO",
        "android.permission.ACCESS_FINE_LOCATION",
        "android.permission.ACCESS_COARSE_LOCATION",
    ):
        adb("shell", "pm", "grant", "com.android.camera2", perm, check=False)
    for perm in (
        "android.permission.ACCESS_FINE_LOCATION",
        "android.permission.ACCESS_COARSE_LOCATION",
    ):
        adb("shell", "pm", "revoke", "com.android.cts.verifier", perm, check=False)
    time.sleep(2)
    adb("shell", "am", "start", "-n", ACTIVITY, check=False)
    time.sleep(2)


def tap_camera_shutter():
    """Tap shutter button in com.android.camera2, dismissing any first-run prompts."""
    for _ in range(15):
        root = ui_dump()
        confirm_btn = find_node(
            root, resource_id="com.android.camera2:id/confirm_button"
        )
        if confirm_btn is not None:
            tap(confirm_btn)
            time.sleep(1)
            root = ui_dump()
        for btn_text in ("NEXT", "Next", "OK", "Got it", "While using the app"):
            btn = find_node(root, text=btn_text)
            if btn is not None:
                tap(btn)
                time.sleep(1)
                root = ui_dump()
        shutter = find_node(root, resource_id="com.android.camera2:id/shutter_button")
        if shutter is not None:
            tap(shutter)
            return True
        time.sleep(1)
    adb("shell", "input", "keyevent", "27")
    return True


def tap_camera_done():
    """Tap confirmation checkmark/done button in camera intent UI."""
    for _ in range(12):
        root = ui_dump()
        done_btn = find_node(root, resource_id="com.android.camera2:id/done_button")
        if done_btn is None:
            done_btn = find_node(root, content_desc="Done")
        if done_btn is not None:
            tap(done_btn)
            time.sleep(2)
            return True
        time.sleep(1)
    return False


def return_to_camera_intents_activity():
    """Navigate back to existing CameraIntentsActivity instance via KEYCODE_BACK."""
    for _ in range(6):
        r = ui_dump()
        if (
            find_node(r, resource_id="com.android.cts.verifier:id/intents_text")
            is not None
        ):
            return
        adb("shell", "input", "keyevent", "4")
        time.sleep(1.5)


def wait_and_tap_pass(stage_num):
    """Wait for pass_button to become enabled in CameraIntentsActivity and tap it."""
    for _ in range(25):
        root = ui_dump()
        pass_btn = find_node(root, content_desc="Pass")
        if pass_btn is None:
            pass_btn = find_node(
                root, resource_id="com.android.cts.verifier:id/pass_button"
            )
        if pass_btn is not None and pass_btn.attrib.get("enabled") == "true":
            print(f"  Stage {stage_num}: Pass button enabled! Tapping Pass...")
            tap(pass_btn)
            time.sleep(2)
            return True
        time.sleep(1)
    raise TimeoutError(f"Pass button did not become enabled in Stage {stage_num}")


def handle_stage(stage_idx):
    """Execute one stage (0..7) of Camera Intents."""
    dismiss_initial_dialogs()
    root = ui_dump()
    pass_btn = find_node(root, content_desc="Pass")
    if pass_btn is None:
        pass_btn = find_node(
            root, resource_id="com.android.cts.verifier:id/pass_button"
        )
    if pass_btn is not None and pass_btn.attrib.get("enabled") == "true":
        print(
            f"  Stage {stage_idx + 1} of 8: Pass button already enabled! Tapping Pass..."
        )
        tap(pass_btn)
        time.sleep(2)
        return

    start_btn = find_node(
        root, resource_id="com.android.cts.verifier:id/start_test_button"
    )
    if start_btn is None:
        raise RuntimeError(f"start_test_button not found in stage {stage_idx + 1}")

    print(f"  Stage {stage_idx + 1} of 8: Tapping Start Test...")
    tap(start_btn)
    time.sleep(2)

    if stage_idx == 0:
        # Stage 0: Application Picture
        adb("shell", "am", "start", "-a", "android.media.action.STILL_IMAGE_CAMERA")
        time.sleep(4)
        tap_camera_shutter()
        time.sleep(3)
        return_to_camera_intents_activity()

    elif stage_idx == 1:
        # Stage 1: Application Video
        adb("shell", "am", "start", "-a", "android.media.action.VIDEO_CAMERA")
        time.sleep(4)
        tap_camera_shutter()  # Start recording
        time.sleep(3.5)
        tap_camera_shutter()  # Stop recording
        time.sleep(3)
        return_to_camera_intents_activity()

    elif stage_idx in (2, 3, 4, 5):
        # Intent Picture / Intent Picture Secure / Motion Photo
        time.sleep(2)
        tap_camera_shutter()
        time.sleep(2)
        tap_camera_done()

    elif stage_idx == 6:
        # Stage 6: Intent Picture (Location Attack)
        for _ in range(10):
            r = ui_dump()
            storage_node = find_node(r, text="Storage & cache")
            if storage_node is not None:
                tap(storage_node)
                time.sleep(1.5)
                break
            time.sleep(1)

        for _ in range(10):
            r = ui_dump()
            clear_node = find_node(r, resource_id="com.android.settings:id/button1")
            if clear_node is None:
                clear_node = find_node(r, content_desc="Clear storage")
            if clear_node is None:
                clear_node = find_node(r, text="Clear storage")
            if clear_node is not None:
                tap(clear_node)
                time.sleep(2.5)
                break
            time.sleep(1)

        tap_camera_shutter()
        time.sleep(2)
        tap_camera_done()
        return_to_camera_intents_activity()

    elif stage_idx == 7:
        # Stage 7: Intent Video
        time.sleep(2)
        tap_camera_shutter()  # Start recording
        time.sleep(3.5)
        tap_camera_shutter()  # Stop recording
        time.sleep(2)
        tap_camera_done()
        # Grant location permissions back to CTS Verifier per instructions & trigger onResume
        for perm in (
            "android.permission.ACCESS_FINE_LOCATION",
            "android.permission.ACCESS_COARSE_LOCATION",
        ):
            adb("shell", "pm", "grant", "com.android.cts.verifier", perm, check=False)
        r = ui_dump()
        settings_btn = find_node(
            r, resource_id="com.android.cts.verifier:id/settings_button"
        )
        if settings_btn is not None:
            tap(settings_btn)
            time.sleep(1.5)
            adb("shell", "input", "keyevent", "4")
            time.sleep(1.5)

    wait_and_tap_pass(stage_idx + 1)


def main():
    setup()
    configure_initial_permissions()
    print("Navigating to test...")
    screenshot("navigating_to_test")
    navigate_to(TEST_NAME)
    time.sleep(2)
    screenshot("activity_launched")

    for stage_idx in range(8):
        handle_stage(stage_idx)
        screenshot(f"stage_{stage_idx + 1}_completed")

    export_and_verify(TEST_NAME)
    screenshot("export_done")


if __name__ == "__main__":
    main()
