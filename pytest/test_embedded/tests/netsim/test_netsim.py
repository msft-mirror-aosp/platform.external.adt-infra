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
# See the License for the specific
import asyncio
import logging
import platform
import psutil
import pytest

from emu.timing import eventually

EXE_SUFFIX = '.exe' if platform.system() == 'Windows' else ''
NETSIMD_BINARY = f'netsimd{EXE_SUFFIX}'
NETSIMDX_BINARY = f'netsimdx{EXE_SUFFIX}'
NETSIM_BINARIES = (NETSIMD_BINARY, NETSIMDX_BINARY)


class NetsimProcessNotFoundException(Exception):
    """Unable to find netsimd process."""

    pass


def netsim_is_alive():
    for process in psutil.process_iter(["name"]):
        try:
            if any(b in process.name() for b in NETSIM_BINARIES):
                return True
        except:
            pass
    return False


async def get_netsimd_cpu_usage():
    """Utility function for getting netsimd CPU usage"""
    netsimd_cpu_usage = [
        process.info["cpu_percent"]
        for process in psutil.process_iter(["name", "cpu_percent"])
        if process.info["name"] in NETSIM_BINARIES
    ]
    if len(netsimd_cpu_usage) > 1:
        raise AssertionError("Multiple netsimd processes found")
    elif len(netsimd_cpu_usage) == 0:
        raise NetsimProcessNotFoundException("Process netsimd not found")
    else:
        return netsimd_cpu_usage[0]


@pytest.mark.boot
@pytest.mark.netsim
@pytest.mark.async_timeout(1080)
async def test_netsimd_is_launched(avd):
    """Test case to verify that the 'netsimd' process is launched."""
    assert await eventually(netsim_is_alive)


@pytest.mark.boot
@pytest.mark.netsim
@pytest.mark.async_timeout(1080)
@pytest.mark.flaky(reruns=2, only_rerun=["NetsimProcessNotFoundException"])
async def test_netsimd_cpu_usage(avd):
    """Test case to verify CPU usage of 'netsimd' process."""
    # Setting up parameters
    threshold = 10
    checks = 5
    timeout = 300

    # Check netsimd CPU usage is below 'threshold' for 'checks' time consecutively.
    # This test will check if the CPU usage stabilizes below 10% within the first
    # 300 seconds of launching Emulator.
    passed = 0
    for i in range(timeout + 1):
        # Obtain cpu_usage of netsimd
        cpu_usage = await get_netsimd_cpu_usage()

        # The first time called with interval = None returns 0.0
        # Source: https://psutil.readthedocs.io/en/latest/#psutil.cpu_percent
        if i == 0:
            # Providing recommended 0.1 second wait time for accuracy
            await asyncio.sleep(0.1)
            continue

        # Log the netsimd CPU usage
        logging.info(f"Check {i}: CPU usage of netsimd: {cpu_usage}%")

        # Set passed accordignly based on cpu_usage
        passed = passed + 1 if cpu_usage <= threshold else 0

        # Passed test if it's below 'threshold' for 'checks' time.
        if passed >= checks:
            return

        # Sleep for 1 second
        await asyncio.sleep(1)

    # Raise error after 1 minute of attempts
    raise AssertionError(f"CPU usage of netsimd exceeds threshold ({threshold}%)")


@pytest.mark.boot
@pytest.mark.netsim
@pytest.mark.async_timeout(1080)
async def test_netsimd_shutdown(avd):
    await avd.stop(timeout=60)
    assert await eventually(lambda: not netsim_is_alive())
