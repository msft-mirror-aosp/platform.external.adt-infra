#!/usr/bin/env python3
"""
Projection Cube Test
The Pass button is enabled immediately after the intro OK dialog is dismissed.
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
    dismiss_dialogs_and_wait_for_pass, tap_pass,
)

TEST_NAME = "Projection Cube Test"
set_screenshot_dir("projection_cube_test")


setup()
print("Navigating to test...")
screenshot("navigating_to_test")
navigate_to(TEST_NAME)
time.sleep(2)
print("Dismissing OK dialog and tapping Pass...")
pass_btn = dismiss_dialogs_and_wait_for_pass()
tap_pass(pass_btn)
export_and_verify(TEST_NAME)
