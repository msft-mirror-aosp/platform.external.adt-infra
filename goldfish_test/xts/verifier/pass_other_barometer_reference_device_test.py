#!/usr/bin/env python3
"""
Barometer Reference Device Test
The Pass button (text='Pass') is immediately enabled when this test opens.
The test auto-runs and reports whether the device has a high-quality barometer.
"""

import time
import sys
import os
import os
import sys
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(SCRIPT_DIR)
from cts_common import screenshot, set_screenshot_dir

from cts_common import (
    ACTIVITY, adb, setup, navigate_to, export_and_verify,
    wait_for, tap_pass,
)

TEST_NAME = "Barometer Reference Device"
set_screenshot_dir("barometer_reference_device")


setup()
print("Navigating to test...")
screenshot("navigating_to_test")
navigate_to(TEST_NAME)
time.sleep(3)
print("Waiting for Pass button (text)...")
screenshot("waiting_for_pass_button_text")
pass_btn = wait_for(text="Pass", timeout=20)
tap_pass(pass_btn)
export_and_verify(TEST_NAME)
