# -*- coding: utf-8 -*-
# Copyright 2024 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Marker definitions."""
import pytest


def register_markers(config):
    markers = [
        "adb: Exercises adb functionality",
        "android_tv: Runs on Android TV",
        "atv: Runs on an android tv image",
        "boot: Validates behavior immediately after boot",
        "chrome: Chrome tests",
        "console: Relates to the emulator console",
        "e2e: Tests the entire flow of a feature, spanning multiple components or systems, from start to finish.",
        "embedded_new_resizable: New resizable embedded emulator API since 34",
        "embedded_newresizable: Uses new resizable emulator API since 34, in embedded mode",
        "embedded: Runs only on an embedded emulator",
        "fast: Emulator fast suite tests. These are P1 tests, and should always succeed.",
        "flaky: Set a test as flaky, and exclude it from test failures on the dashboard.",
        "foldable: Operates on a foldable emulator",
        "graphics: Relates to graphics operations",
        "guestperf: Guest-side performance test",
        "hardware: Low-level hardware test",
        "hostperf: Host-side performance test",
        "multi: Uses multiple emulator at the same time.",
        "multidisplay: Relates to multi-display",
        "netsim: Netsim emulator tests",  # Duplicate, kept for consistency
        "netsim: Verifies netsim functionality",
        "newfoldable: Uses new foldable emulator API since 34",
        "newresizable: Uses new resizable emulator API since 34",
        "oldapiboot: Validates behavior immediately after boot for older apis",
        "resizable: Runs on a resizable emulator",
        "sanity: Emulator sanity tests. These are P0 tests, and should always succeed.",
        "skipos(platform, reason=None): skip the given test for the given platform. Valid platform values and systems are: 'win' (Windows), 'linux' (Linux), 'mac' (macOS), 'm1' (macOS aarch64). Multiple OS values are accepted, such as 'win, linux'. To skip the test in all platforms, use the 'all' option.",
        "slow: A slow test that can take more than 60s to run",
        "snapshot: Relates to snapshot operations",
        "standard: Tests independent of an emulator",
        "std: Standard test that does not need an emulator",
        "tablet: Runs on a tablet image",
        "test_infra: Test infrastructure (fixtures, helper functions, etc) test"
        "uiautomator: Performs UI actions",
        "wear: Runs on Wear OS",
        "wifi_perf: WiFi performance test",
        "windows: Runs only on Windows",
    ]
    for marker in markers:
        config.addinivalue_line("markers", marker)
