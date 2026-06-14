#!/usr/bin/env python3
"""
Screen Pinning Test
"""

import time
import sys
import os
import os
import sys
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(SCRIPT_DIR)
from cts_common import screenshot, set_screenshot_dir
from cts_common import ACTIVITY, adb, setup, navigate_to, ui_dump, find_node, tap, export_and_verify, screenshot, set_screenshot_dir

TEST_NAME = "Screen Pinning Test"

set_screenshot_dir("screen_pinning")

setup()
screenshot("app_launched")

# Enable screen pinning feature via settings
adb("shell", "settings", "put", "system", "lock_to_app_enabled", "1")
time.sleep(1)

navigate_to(TEST_NAME)
time.sleep(2)
screenshot("test_detail_view")

def handle_system_dialogs(root):
    # Handle system prompts that might appear when pinning is initiated
    for btn_text in ["OK", "Got it", "Start", "Pin"]:
        btn = find_node(root, text=btn_text)
        if btn is not None and btn.get("enabled") == "true":
            print(f"Found system dialog button '{btn_text}', tapping it...")
            screenshot(f"dialog_{btn_text}_found")
            tap(btn)
            time.sleep(2)
            screenshot(f"dialog_{btn_text}_tapped")
            return True
    return False

def get_screen_text(root):
    # Extracts all text from the UI to determine if the screen has changed
    texts = []
    for node in root.iter("node"):
        t = node.attrib.get("text", "").strip()
        c = node.attrib.get("content-desc", "").strip()
        if t: texts.append(t)
        if c: texts.append(c)
    return " ".join(texts)

def find_button_case_insensitive(root, label):
    label = label.lower()
    for node in root.iter("node"):
        if node.attrib.get("text", "").lower() == label:
            return node
        if node.attrib.get("content-desc", "").lower() == label:
            return node
    return None

for i in range(60):
    print(f"--- Loop iteration {i} ---")
    root = ui_dump()
    
    if handle_system_dialogs(root):
        continue
        
    pass_btn = find_node(root, content_desc="Pass")
    if pass_btn is None:
        pass_btn = find_node(root, text="Pass")
    if pass_btn is not None and pass_btn.get("enabled") == "true":
        print("Found Pass button, tapping it...")
        screenshot("found_pass_button_tapping_it")
        screenshot("pass_button_enabled")
        tap(pass_btn)
        break

    curr_text = get_screen_text(root)
    next_btn = find_button_case_insensitive(root, "Next")
    
    if "Screen was not unpinned" in curr_text:
        print("Found 'Screen was not unpinned'. Attempting to unpin...")
        screenshot("found_screen_was_not_unpinned_attempting_to_unpin")
        screenshot("screen_was_not_unpinned")
        adb("shell", "am", "task", "lock", "stop", check=False)
        time.sleep(2)
        
        if next_btn is not None:
            print("Tapping Next after unpin...")
            screenshot("tapping_next_after_unpin")
            screenshot("tapping_next_after_unpin")
            tap(next_btn)
    else:
        if next_btn is not None:
            print("Tapping Next...")
            screenshot("tapping_next")
            screenshot("tapping_next")
            tap(next_btn)
            
    time.sleep(3)
else:
    screenshot("pass_button_never_became_available")
    raise RuntimeError("Pass button never became available within max iterations")

screenshot("before_export")
export_and_verify(TEST_NAME)
