#!/usr/bin/env python3
"""
6DoF Test automation script.
On Goldfish emulator, Sensor.TYPE_POSE_6DOF is not advertised, so StartActivity
calls setTestResultAndFinish(true) in onCreate() and passes trivially.
"""

import time
from cts_common import (
    PACKAGE,
    adb,
    export_and_verify,
    find_node,
    get_focused_activity,
    navigate_to,
    screenshot,
    set_screenshot_dir,
    setup,
    tap,
    ui_dump,
)

TEST_NAME = "6DoF Test"
set_screenshot_dir("sensors_6dof_test")

setup()
screenshot("launched")

root = ui_dump()
close_btn = find_node(root, text="Close")
if close_btn is not None:
    tap(close_btn)
    time.sleep(2)

navigate_to(TEST_NAME)
time.sleep(2)
screenshot("test_opened")

# StartActivity auto-finishes via setTestResultAndFinish(true) when TYPE_POSE_6DOF is null.
# If still inside StartActivity, tap Pass if enabled.
for _ in range(10):
    focused = get_focused_activity()
    if "CtsVerifierActivity" in focused or "TestListActivity" in focused:
        print("StartActivity auto-passed and returned to main list.")
        break
    root = ui_dump()
    ok = find_node(root, text="OK")
    if ok is not None and ok.get("enabled") == "true":
        tap(ok)
        time.sleep(1)
        continue
    pass_btn = find_node(root, content_desc="Pass") or find_node(root, text="Pass")
    if pass_btn is not None and pass_btn.get("enabled") == "true":
        tap(pass_btn)
        time.sleep(2)
        break
    time.sleep(1)

export_and_verify(TEST_NAME)
screenshot("export_done")
