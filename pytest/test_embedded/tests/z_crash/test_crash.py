# Copyright 2020 The Android Open Source Project
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
from emu.emulator import BaseEmulator
import time


@pytest.mark.e2e
@pytest.mark.timeout(timeout=60, func_only=True)
def test_crash_the_emulator(emulator: BaseEmulator, crash_reporter):
    """Make sure the emulator can crash, and produces a report.

    Note, this test is placed in the z_crash directory to have it run last.
    """
    if not crash_reporter.available():
        pytest.skip("No crash reporter available, let's not crash the emulator")

    # Launch the emulator if needed.
    if not emulator.is_alive():
        emulator.launch()

    assert emulator.is_alive()

    old_crashes = crash_reporter.crashes()

    emulator.console().send("crash")

    # Give the reporter a chance to collect a report.
    while emulator.is_alive():
        time.sleep(1)

    # We should have new crashes..
    new_crashes = crash_reporter.crashes()
    assert len(old_crashes) < len(new_crashes)
