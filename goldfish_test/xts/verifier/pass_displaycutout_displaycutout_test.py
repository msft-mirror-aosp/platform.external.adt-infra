#!/usr/bin/env python3
"""
DisplayCutout Test
Shows numbered buttons (0-15) placed around the display cutout safe-inset area.
After tapping all of them (verifying they are clickable), the Pass button
becomes enabled.
"""

import time
from cts_common import screenshot, set_screenshot_dir

from cts_common import (
    ACTIVITY, adb, setup, navigate_to, export_and_verify,
    find_node, ui_dump, tap, tap_pass,
)

TEST_NAME = "DisplayCutout Test"
set_screenshot_dir("displaycutout_test")


setup()
print("Navigating to test...")
screenshot("navigating_to_test")
navigate_to(TEST_NAME)
time.sleep(2)

# Dismiss the "Got it" intro overlay
root = ui_dump()
got_it = find_node(root, text="Got it")
if got_it is not None:
    print("  Dismissing 'Got it' overlay...")
    tap(got_it)
    time.sleep(2)

# Tap each of the 16 numbered region buttons (0-15)
print("Tapping all numbered region buttons...")
screenshot("tapping_all_numbered_region_buttons")
for attempt in range(3):
    root = ui_dump()
    buttons_tapped = 0
    for label in [str(i) for i in range(16)]:
        btn = find_node(root, text=label)
        if btn is not None and btn.attrib.get("clickable") == "true":
            tap(btn)
            buttons_tapped += 1
    print(f"  Attempt {attempt+1}: tapped {buttons_tapped} buttons")
    time.sleep(1)
    # Check if Pass is now enabled
    root = ui_dump()
    pass_btn = find_node(root, content_desc="Pass")
    if pass_btn is not None and pass_btn.attrib.get("enabled") == "true":
        break

print("Tapping Pass...")
screenshot("tapping_pass")
tap_pass()
export_and_verify(TEST_NAME)
