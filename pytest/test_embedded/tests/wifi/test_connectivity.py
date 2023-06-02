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
from emu.timing import wait_until

@pytest.mark.e2e
@pytest.mark.timeout(timeout=60, func_only=True)
def test_wifi_has_connectivity(emulator):

    def has_connectivity():
    # Check that AVD can connect to Google Public DNS 8.8.8.8.
        result = emulator.adb.run(["shell","dumpsys", "connectivity", "--diag"]).rstrip()
        for line in result.splitlines():
            if "DNS UDP dst{8.8.8.8}" in line and "SUCCEEDED" in line:
                return True
        return False
    assert wait_until(has_connectivity), "Unable to connect to dns 8.8.8.8"
