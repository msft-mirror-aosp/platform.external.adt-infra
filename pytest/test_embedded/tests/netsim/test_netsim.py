import asyncio
import logging
import psutil
import pytest

from emu.timing import eventually


def netsim_is_alive():
    for process in psutil.process_iter(["name"]):
        try:
            if "netsimd" in process.name():
                return True
        except:
            pass
    return False


async def get_netsimd_cpu_usage():
    """Utility function for getting netsimd CPU usage"""
    netsimd_cpu_usage = [
        process.info["cpu_percent"]
        for process in psutil.process_iter(["name", "cpu_percent"])
        if process.info["name"] == "netsimd"
    ]
    if len(netsimd_cpu_usage) > 1:
        raise AssertionError("Multiple netsimd processes found")
    elif len(netsimd_cpu_usage) == 0:
        raise AssertionError("Process netsimd not found")
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
async def test_netsimd_cpu_usage(avd):
    """Test case to verify CPU usage of 'netsimd' process"""
    # Setting up parameters
    threshold = 10
    checks = 5

    # Check netsimd CPU usage is below 'threshold' for 'checks' time consecutively.
    # This test will check if the CPU usage stabilizes below 10% within the first
    # 60 seconds of launching Emulator.
    passed = 0
    for i in range(61):
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
