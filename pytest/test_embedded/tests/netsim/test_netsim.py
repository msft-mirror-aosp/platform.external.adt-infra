import psutil
import pytest

from emu.timing import eventually


@pytest.mark.e2e
@pytest.mark.boot
@pytest.mark.timeout(timeout=20, func_only=True)
def test_netsimd_is_launched(avd):
    """Test case to verify that the 'netsimd' process is launched."""
    assert eventually(
        lambda: any(
            "netsimd" in process.name() for process in psutil.process_iter(["name"])
        )
    )
