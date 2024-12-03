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
import logging

from emu.timing import wait_until, eventually
from functools import partial

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


@pytest.mark.fast
@pytest.mark.async_timeout(500)
async def test_wifi_internet_protocols(avd, mbs):
    """Verify that both IPv4 and IPv6 protocols are supported over WiFi.

    Args:
        avd (BaseEmulator): Fixture that provides access to the running emulator.
        mbs (SnippetClientV2): Fixture that provides access to the MBS snippet controller.

    Test Steps:
        1. Enable WiFi and connect to the Android WiFi network.
        2. Run commands 'ip -4 addr wlan0' and 'ip -6 addr wlan0' (Verify 1).
        3. Use ping and nc to test IPv4 and IPv6 connectivity to Google DNS (Verify 2).

    Verify:
        1. There should be IPs assigned to both IPv4 and IPv6 protocols.
        2. Internet connectivity to Google's public DNS should succeed.
    """
    # Test Wifi only
    await avd.adb.shell("svc data disable")

    # Connect to AndroidWifi
    mbs.wifiConnectSimple(WIFI_SSID, None)

    # Verify if both IPv4 and IPv6 addresses are assigned
    ip_addr = ""
    async def has_ip(type: str):
        nonlocal ip_addr
        ip_cmd = "ip -{} addr show wlan0 | grep -s scope"
        exit_code, ip_addr = await avd.adb.run(["shell", ip_cmd.format(type)])
        return True if exit_code == 0 else None

    logging.info("Checking IPv4 and IPv6 addresses ...")
    assert await eventually(
        partial(has_ip, '4'), timeout=60
    ), "No Wi-Fi IPv4 address assigned."
    logging.info("IPv4 addresses assigned to the WI-Fi connection:")
    [logging.info(ip.strip()) for ip in ip_addr]

    assert await eventually(
        partial(has_ip, '6'), timeout=60
    ), "No Wi-Fi IPv6 address assigned."
    logging.info("IPv6 addresses assigned to the WI-Fi connection:")
    [logging.info(ip.strip()) for ip in ip_addr]

    # Verify if both IPv4 and IPv6 have network connectivity
    async def has_ipv4_connectivity():
        exit_code, _ = await avd.adb.run(
            ["shell", "ping -W 60 -I wlan0 -c 3 8.8.8.8"])
        return True if exit_code == 0 else None

    async def has_ipv6_connectivity():
        exit_code, _ = await avd.adb.run(
            ["shell", "nc -w 60 -6 2001:4860:4860::8888 53"])
        return True if exit_code == 0 else None

    logging.info("Checking IPv4 and IPv6 connectivity ...")
    assert await eventually(
        has_ipv4_connectivity, timeout=60
    ), "Emulator has not Wifi IPv4 connectivity"
    assert await eventually(
        has_ipv6_connectivity, timeout=60
    ), "Emulator has not Wifi IPv6 connectivity"

    # Re-enable data connectivity
    await avd.adb.shell("svc data enable")
