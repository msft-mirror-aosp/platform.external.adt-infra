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

import json
import pytest

from emu.timing import wait_until


@pytest.mark.e2e
@pytest.mark.boot
@pytest.mark.async_timeout(500)
# Consider adding separate test suites with launch flags, instead of test parameters,
@pytest.mark.parametrize(
    "launch_flags", [["-no-snapshot"], ["-no-snapshot", "-feature", "WiFiPacketStream"]],
)
async def test_wifi_has_connectivity(avd, pytestconfig, launch_flags):
    all_flags = json.loads(pytestconfig.getoption("emulator_launch_flags"))
    all_flags += launch_flags
    assert await avd.restart(all_flags)
    assert await avd.wait_for_boot()

    async def has_connectivity():
        # Check that AVD can connect to Google Public DNS 8.8.8.8.
        result = await avd.adb.shell("dumpsys connectivity --diag")
        for line in result.rstrip().splitlines():
            if "DNS UDP dst{8.8.8.8}" in line and "SUCCEEDED" in line:
                return True
        return False

    assert await wait_until(has_connectivity), "Unable to connect to dns 8.8.8.8"
