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

import logging
from functools import partial

import pytest
import platform

from emu.process.command import Command
from emu.timing import eventually, wait_until

WIFI_SSID = "AndroidWifi"


@pytest.mark.boot
@pytest.mark.async_timeout(500)
# Consider adding separate test suites with launch flags, instead of test parameters,
@pytest.mark.parametrize(
    "launch_flags",
    [["-no-snapshot"], ["-no-snapshot", "-feature", "WiFiPacketStream"]],
)
@pytest.mark.flaky(reruns=0)
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
@pytest.mark.flaky(reruns=0)  # b/346612104
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


@pytest.fixture
async def enable_wifi_only(avd, mbs):
    """Enables Wi-Fi and disables mobile data on the emulator.

    Args:
        avd: The emulator instance.
        mbs: The Mobly Snippet library instance.

    Yields:
        None.  This fixture primarily sets up a state and cleans up afterwards.

    This fixture disables mobile data and connects the emulator to a predefined
    Wi-Fi network (AndroidWifi).  After the test using this fixture completes,
    mobile data is re-enabled.
    """
    # Disable data
    await avd.adb.shell("svc data disable")
    mbs.wifiConnectSimple(WIFI_SSID, None)

    yield

    # Enable data
    await avd.adb.shell("svc data enable")


@pytest.fixture
async def has_ip(avd):
    """Provides a function to check for assigned IP addresses.

    Args:
        avd: The emulator instance.

    Returns:
        A function that takes an IP version ("4" or "6") as a string and returns
        True if an IP of that version is assigned to wlan0, False otherwise.
    """

    async def _has_ip(type: str):
        """Checks if an IP address of the given type is assigned to wlan0.

        Args:
            type: The IP version ("4" or "6").

        Returns:
            True if an IP of the given type is assigned, False otherwise.
        """
        ip_cmd = f"ip -{type} addr show wlan0 | grep -s scope"
        exit_code, _ = await avd.adb.run(["shell", ip_cmd])
        return exit_code == 0

    return _has_ip


@pytest.mark.fast
@pytest.mark.async_timeout(40)
async def test_wlan0_can_connect_ipv4(enable_wifi_only, avd):
    """Tests IPv4 connectivity over wlan0.

    Args:
        enable_wifi_only: Fixture to enable Wi-Fi and disable mobile data.
        avd: The emulator instance.
    """

    async def has_ipv4_connectivity():
        exit_code, _ = await avd.adb.run(["shell", "ping -W 60 -I wlan0 -c 3 8.8.8.8"])
        return True if exit_code == 0 else None

    assert await eventually(
        has_ipv4_connectivity, timeout=20
    ), "Emulator has not Wifi IPv4 connectivity"


@pytest.mark.fast
@pytest.mark.async_timeout(40)
async def test_wlan0_ip6_address_assigned(enable_wifi_only, has_ip):
    """Tests that an IPv6 address is assigned to wlan0.

    Args:
        enable_wifi_only: Fixture to enable Wi-Fi and disable mobile data.
        has_ip: Fixture providing a function to check IP address assignment.
    """
    assert await eventually(
        partial(has_ip, "6"), timeout=20
    ), f"No Wi-Fi IPv6 address assigned"


@pytest.mark.fast
@pytest.mark.async_timeout(40)
@pytest.mark.skip("IPv6 tests are not yet supported. b/386238377")
async def test_wlan0_can_connect_ipv6(enable_wifi_only, avd):
    """Tests IPv6 connectivity over wlan0.

    Args:
        enable_wifi_only: Fixture to enable Wi-Fi and disable mobile data.
        avd: The emulator instance.
    """

    async def host_can_ping_ipv6():
        ping_count_option = "-n" if platform.system() == "Windows" else "-c"
        command = ["ping6", ping_count_option, "3", "ipv6.google.com"]
        exit_code, _ = await Command(command).run_until_finished()
        return exit_code == 0

    async def has_ipv6_connectivity():
        exit_code, _ = await avd.adb.run(
            ["shell", "ping6 -W 60 -I wlan0 -c 3 2001:4860:4860::8888"]
        )
        return exit_code == 0

    if not await host_can_ping_ipv6():
        pytest.skip("Host cannot ping ipv6, so guest won't be able to either")

    assert await eventually(
        has_ipv6_connectivity, timeout=20
    ), "Emulator has no Wifi IPv6 connectivity"
