import psutil
import pytest

from emu.timing import eventually


@pytest.mark.e2e
@pytest.mark.boot
@pytest.mark.netsim
@pytest.mark.async_timeout(200)
async def test_netsimd_is_launched(avd):
    """Test case to verify that the 'netsimd' process is launched."""

    def netsim_is_alive():
        for process in psutil.process_iter(["name"]):
            try:
                if "netsimd" in process.name():
                    return True
            except:
                pass
        return False

    assert await eventually(netsim_is_alive)
