#!/usr/bin/env python3
"""
Recent Task Removal Test
Requires CtsForceStopHelper.apk installed. Launches the helper app's activity,
opens Recents, swipes away its task, and returns to CtsVerifier for Pass.
"""

import os
import re
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(SCRIPT_DIR)

from cts_common import ACTIVITY, adb, export_and_verify, find_node, navigate_to, screenshot, set_screenshot_dir, setup, tap, ui_dump

TEST_NAME = "Recent Task Removal Test"
set_screenshot_dir("recent_task_removal_test")

cts_apk_path = os.environ.get("CTS_APK_PATH")
if cts_apk_path:
    HELPER_APK = os.path.join(os.path.dirname(cts_apk_path), "CtsForceStopHelper.apk")
else:
    HELPER_APK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "android-cts-verifier", "CtsForceStopHelper.apk")

if not os.path.exists(HELPER_APK):
    print(f"Error: HELPER_APK not found at {HELPER_APK}")
    raise FileNotFoundError(f"HELPER_APK not found: {HELPER_APK}")

setup()
# Uninstall helper APK if present to ensure clean state
print("Uninstalling existing CtsForceStopHelper...")
adb("uninstall", "com.android.cts.forcestophelper", check=False)
time.sleep(1)

# Install helper APK
print("Installing CtsForceStopHelper.apk...")
screenshot("installing_ctsforcestophelper_apk")
adb("install", "-g", "-r", HELPER_APK)
time.sleep(2)

navigate_to(TEST_NAME)
time.sleep(2)

# Tap "Launch test activity" to start the helper app's activity as its own task
# (retry: an intro dialog may need dismissing, and the screen may still be
# settling right after navigate_to)
launch_btn = None
for _ in range(10):
    root = ui_dump()
    ok = find_node(root, text="OK")
    if ok is not None:
        print("Dismissing intro dialog...")
        screenshot("dismissing_intro_dialog")
        tap(ok)
        time.sleep(1)
        continue
    launch_btn = find_node(root, text="Launch test activity")
    if launch_btn is not None:
        break
    time.sleep(1)

if launch_btn is None:
    raise RuntimeError("'Launch test activity' button never appeared")

print("Tapping 'Launch test activity'...")
screenshot("tapping_launch_test_activity")
tap(launch_btn)
time.sleep(2)

print("Opening Recents...")
screenshot("opening_recents")
adb("shell", "input", "keyevent", "KEYCODE_APP_SWITCH")
time.sleep(2.5)

print("Checking position of helper task in Recents...")
for attempt in range(5):
    root = ui_dump()
    helper_node = None
    for node in root.iter("node"):
        if node.attrib.get("content-desc") == "Force stop helper app":
            helper_node = node
            break

    if helper_node is None:
        if attempt == 0:
            print("Could not find helper app explicitly. Falling back to center swipe...")
            try:
                out = adb("shell", "wm", "size")
                m = re.search(r'(\d+)x(\d+)', out)
                if m:
                    w, h = int(m.group(1)), int(m.group(2))
                    cx, cy = w // 2, int(h * 0.75)
                    print(f"Swiping up from calculated center ({cx}, {cy})")
                    adb("shell", "input", "swipe", str(cx), str(cy), str(cx), "100", "100")
                else:
                    adb("shell", "input", "swipe", "540", "1500", "540", "100", "100")
            except Exception as e:
                print(f"Error getting screen size: {e}")
                adb("shell", "input", "swipe", "540", "1500", "540", "100", "100")
            time.sleep(2)
            continue
        else:
            print("Helper task no longer found in Recents, assuming it's swiped away.")
            break

    screenshot(f"swiping_away_helper_task_attempt_{attempt}")
    bounds = helper_node.attrib.get("bounds", "")
    print(f"Found helper app at {bounds}")
    match = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds)
    if match:
        x1, y1, x2, y2 = map(int, match.groups())

        # Center the app if it's off to the left or right
        if x1 < 100:
            print("Swiping left-to-right to center the app...")
            screenshot(f"centering_helper_task_left_to_right_{attempt}")
            adb("shell", "input", "swipe", "200", "1000", "800", "1000", "100")
            time.sleep(2)
            continue
        elif x1 > 600:
            print("Swiping right-to-left to center the app...")
            screenshot(f"centering_helper_task_right_to_left_{attempt}")
            adb("shell", "input", "swipe", "800", "1000", "200", "1000", "100")
            time.sleep(2)
            continue

        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2
        start_y = y2 - 200 if y2 > 400 else cy
        print(f"Swiping away helper task from {cx}, {start_y} to {cx}, 100...")
        adb("shell", "input", "swipe", str(cx), str(start_y), str(cx), "100", "300")
        time.sleep(2)
    else:
        print("Could not parse bounds, falling back to generic swipe.")
        adb("shell", "input", "swipe", "540", "1500", "540", "100", "300")
        time.sleep(2)
else:
    print("Warning: Exhausted 5 attempts to swipe away helper task. Proceeding anyway.")

# Dismiss any force-stop/kill permission dialog that may appear (deny it)
root = ui_dump()
for deny_text in ["Deny", "Cancel", "No"]:
    deny_btn = find_node(root, text=deny_text)
    if deny_btn is not None:
        print(f"Denying dialog: {deny_text!r}")
        screenshot("denying_permission_dialog")
        tap(deny_btn)
        break

print("Returning to CtsVerifier...")
screenshot("returning_to_ctsverifier")
adb("shell", "am", "start", "-n", ACTIVITY)
time.sleep(2)

for _ in range(30):
    root = ui_dump()
    pass_btn = find_node(root, content_desc="Pass")
    if pass_btn is None:
        pass_btn = find_node(root, text="Pass")
    if pass_btn is not None and pass_btn.get("enabled") == "true":
        print("Tapping Pass...")
        screenshot("tapping_pass")
        tap(pass_btn)
        break
    ok = find_node(root, text="OK")
    if ok is not None and ok.get("enabled") == "true":
        tap(ok)
        continue
    time.sleep(3)
else:
    raise RuntimeError("Pass button never became available")

export_and_verify(TEST_NAME)
