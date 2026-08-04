#!/usr/bin/env python3
"""
Ignore Battery Optimizations Test
Navigate to the test, handle the setup sequence, and tap Pass when available.
"""

import time
import sys
import os
import xml.etree.ElementTree as ET
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(SCRIPT_DIR)
from cts_common import screenshot, set_screenshot_dir
from cts_common import ACTIVITY, adb, setup, navigate_to, ui_dump, find_node, tap, export_and_verify

TEST_NAME = "Ignore Battery Optimizations Test"
set_screenshot_dir("ignore_battery_optimizations_test")

setup()
time.sleep(1)

navigate_to(TEST_NAME)
time.sleep(3)

for _ in range(40):
    root = ui_dump()

    # Dismiss crash dialogs
    crashed = False
    for dismiss_text in ["Close app", "Cancel"]:
        btn = find_node(root, text=dismiss_text)
        if btn is not None:
            print(f"  Dismissing dialog: {dismiss_text}")
            tap(btn)
            crashed = True
            break
    if crashed:
        time.sleep(2)
        continue

    pass_btn = find_node(root, content_desc="Pass")
    if pass_btn is None:
        pass_btn = find_node(root, text="Pass")
    if pass_btn is not None and pass_btn.get("enabled") == "true":
        print("Tapping Pass...")
        screenshot("tapping_pass")
        tap(pass_btn)
        break

    ok_btn = find_node(root, text="OK")
    if ok_btn is not None:
        print("Tapping OK...")
        screenshot("tapping_ok")
        tap(ok_btn)
        time.sleep(2)
        continue

    allow_btn = find_node(root, text="Allow")
    if allow_btn is not None:
        print("Tapping Allow...")
        screenshot("tapping_allow")
        tap(allow_btn)
        time.sleep(2)
        continue

    # Check if Settings app is open
    if find_node(root, text="App battery usage") is not None or find_node(root, text="All apps") is not None:
        print("Settings is open, pressing BACK...")
        screenshot("settings_is_open")
        adb("shell", "input", "keyevent", "4")
        time.sleep(2)
        continue

    # Extract text from the instruction node, not the whole tree
    instruction_node = None
    for node in root.iter('node'):
        if node.get('resource-id') == "com.android.cts.verifier:id/txt_instruction":
            instruction_node = node
            break

    instruction = instruction_node.get("text") if instruction_node is not None else ""
    if not instruction:
        instruction = ET.tostring(root).decode('utf-8')

    if "exempt it." in instruction:
        print("  Executing adb whitelist +")
        screenshot("executing_whitelist_add")
        adb("shell", "cmd", "deviceidle", "whitelist", "+com.android.cts.verifier")
    elif "Remove the test app from the ignore battery optimizations list" in instruction:
        print("  Executing adb whitelist -")
        screenshot("executing_whitelist_remove")
        adb("shell", "cmd", "deviceidle", "whitelist", "-com.android.cts.verifier")
    elif "remove the app" in instruction and "exemption" in instruction:
        print("  Executing adb whitelist -")
        screenshot("executing_whitelist_remove")
        adb("shell", "cmd", "deviceidle", "whitelist", "-com.android.cts.verifier")

    next_btn = find_node(root, text="Next")
    if next_btn is not None:
        # Don't tap next if it is disabled
        if next_btn.get("enabled") == "false":
            time.sleep(2)
            continue
        short_inst = instruction[:50] + "..." if instruction else "No instruction"
        print(f"Tapping Next (instruction: {short_inst})")
        screenshot("tapping_next")
        tap(next_btn)
        time.sleep(2)
        continue

    time.sleep(3)
else:
    raise RuntimeError("Pass button never became available")

export_and_verify(TEST_NAME)
