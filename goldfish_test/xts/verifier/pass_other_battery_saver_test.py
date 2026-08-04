#!/usr/bin/env python3
"""Battery Saver Test - toggle battery saver via adb, then navigate and pass."""

import time
import sys
import os
import os
import sys
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(SCRIPT_DIR)
from cts_common import screenshot, set_screenshot_dir
from cts_common import adb, setup, navigate_to, ui_dump, find_node, tap, export_and_verify

TEST_NAME = "Battery Saver Test"
set_screenshot_dir("battery_saver_test")


setup()
# Enable then disable Battery Saver to satisfy the test's toggle requirement
adb("shell", "settings", "put", "global", "low_power", "1")
time.sleep(1)
adb("shell", "settings", "put", "global", "low_power", "0")
time.sleep(1)

navigate_to(TEST_NAME)
time.sleep(2)

# This is a multi-step instructional flow (OrderedTestActivity): each screen
# asks to turn Battery Saver on or off, then tap Next. Read the instruction
# text to know which way to set it before advancing.
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

    next_btn = find_node(root, text="Next")
    if next_btn is not None and next_btn.get("enabled") == "true":
        instruction = ""
        for node in root.iter("node"):
            t = node.attrib.get("text", "")
            if "Battery Saver" in t and "turn" in t.lower():
                instruction = t
                break
        if "turn battery saver off" in instruction.lower():
            print("Setting low_power=0 (instruction says turn off)...")
            screenshot("setting_low_power_0_instruction_says_turn_off")
            adb("shell", "settings", "put", "global", "low_power", "0")
        else:
            print("Setting low_power=1 (instruction says turn on)...")
            screenshot("setting_low_power_1_instruction_says_turn_on")
            adb("shell", "settings", "put", "global", "low_power", "1")
        time.sleep(2)
        print("Tapping Next...")
        screenshot("tapping_next")
        tap(next_btn)
        time.sleep(2)
        continue

    time.sleep(3)
else:
    raise RuntimeError("Pass button never became available")

export_and_verify(TEST_NAME)
