import asyncio
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


@pytest.mark.boot
@pytest.mark.netsim
@pytest.mark.async_timeout(1080)
async def test_netsimd_is_launched(avd):
    """Test case to verify that the 'netsimd' process is launched."""
    assert await eventually(netsim_is_alive)


@pytest.mark.boot
@pytest.mark.netsim
@pytest.mark.async_timeout(1080)
async def test_netsimd_shutdown(avd):
    await avd.stop(timeout=60)
    assert await eventually(lambda: not netsim_is_alive())
