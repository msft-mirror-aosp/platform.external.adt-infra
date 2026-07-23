#!/usr/bin/env python3
"""Projection Video Playback Test - Pass enabled after OK dialog."""

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

TEST_NAME = "Projection Video Playback Test"
set_screenshot_dir("projection_video_playback_test")

setup()
navigate_to(TEST_NAME)
time.sleep(2)
pass_btn = dismiss_dialogs_and_wait_for_pass()
tap_pass(pass_btn)
export_and_verify(TEST_NAME)
