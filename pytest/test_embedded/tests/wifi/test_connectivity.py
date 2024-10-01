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



@pytest.mark.boot
@pytest.mark.async_timeout(500)
# Consider adding separate test suites with launch flags, instead of test parameters,
@pytest.mark.parametrize(
    "launch_flags", [["-no-snapshot"], ["-no-snapshot", "-feature", "WiFiPacketStream"]],
)
@pytest.mark.flaky
async def test_wifi_has_connectivity(avd, launch_flags):
    assert await avd.restart(avd.launch_flags + launch_flags)
    assert await avd.wait_for_boot()

    async def has_connectivity():
        # Check that AVD can connect to Google Public DNS 8.8.8.8.
        result = await avd.adb.shell("dumpsys connectivity --diag")
        for line in result.rstrip().splitlines():
            if "DNS UDP dst{8.8.8.8}" in line and "SUCCEEDED" in line:
                return True
        return False

    assert await wait_until(has_connectivity), "Unable to connect to dns 8.8.8.8"



@pytest.mark.boot
@pytest.mark.sanity
@pytest.mark.skipos("all", "reason: test is flaky b/346612104")
async def test_wifi_connectivity_without_mobile_data(avd):
    """Checks internet connectivity via the wifi stack
    Args:
        avd (BaseEmulator): Fixture that gives access to the running emulator.

    Test UUID: 1f6a0e5a-958a-4a01-86f1-d926c2c39931

    Test Steps:
        1. Disable the mobile data connectivity

    Verify:
        Test internet connectivity via a ping command to www.google.com
    """

    # Disable the mobile data connectivity
    await avd.adb.shell("svc data disable")

    async def has_internet_access():
        result = await avd.adb.shell("ping -c 3 www.google.com")
        for line in result.rstrip().splitlines():
            if "64 bytes from" in line and "icmp_seq" in line and "ttl" in line:
                return True
        return False

    assert await wait_until(has_internet_access), "Failed to ping www.google.com"

    # Enable the data connectivity, in case this avd is used for the next test
    await avd.adb.shell("svc data enable")
