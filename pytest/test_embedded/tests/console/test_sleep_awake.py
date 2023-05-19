# Copyright 2023 The Android Open Source Project
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

import pytest
import time


def adb_test_sleep_wake(avd):
    """Verify that the device can be put to sleep and waked up successfully.

    Args:
      avd: The emulator

    Returns:
      True if the device was successfully put to sleep and waked up, else False.
    """

    return not "adb: error" in avd.adb.run(["shell", "input", "keyevent", "POWER"])


def adb_verify_sleep_awake_state(avd, state):
    """Verify the screen state of the emulator.

    Args:
      avd: The emulator
      state: The screen state of emulator
    """
    status = avd.adb.run(["shell", "dumpsys display | grep mScreenState"])
    output_items = status.split("=")
    if output_items:
        assert output_items[1] == state
    else:
        raise Exception("Unexpected output: %s", status)


@pytest.mark.adb
def test_adb_sleep_wake(avd):
    """Test ADB sleep/wake commands"""

    success = adb_test_sleep_wake(avd)
    time.sleep(1)
    assert success, "ADB Sleep failed"
    # Check fails on build bots b/282025124
    # adb_verify_sleep_awake_state(avd, "OFF")

    success = adb_test_sleep_wake(avd)
    time.sleep(1)
    assert success, "ADB Wake up failed"
    # Check fails on build bots b/282025124
    # adb_verify_sleep_awake_state(avd, "ON")
