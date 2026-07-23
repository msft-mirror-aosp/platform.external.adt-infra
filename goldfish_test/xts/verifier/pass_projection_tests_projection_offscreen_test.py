#!/usr/bin/env python3
"""Projection Offscreen - uses UI navigation."""

import sys
import os
import os
import sys
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(SCRIPT_DIR)
from cts_common import setup, navigate_to, dismiss_dialogs_and_wait_for_pass, tap_pass, export_and_verify, screenshot, set_screenshot_dir

TEST_NAME = "Projection Offscreen Activity"
set_screenshot_dir("projection_offscreen_activity")


setup()
navigate_to(TEST_NAME)
pass_btn = dismiss_dialogs_and_wait_for_pass()
tap_pass(pass_btn)
export_and_verify(TEST_NAME)
