import pytest
from netsim import netsim


@pytest.mark.e2e
@pytest.mark.timeout(timeout=20, func_only=True)
def test_device_attaches_to_netsimd(avd):
    """Test case to verify that a device is attached to netsimd."""
    assert len(netsim.NetsimClient().get_devices()) != 0
