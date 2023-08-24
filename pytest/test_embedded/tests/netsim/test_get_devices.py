import pytest
from netsim_grpc import netsim_client


@pytest.mark.e2e
@pytest.mark.boot
@pytest.mark.timeout(timeout=20, func_only=True)
def test_device_attaches_to_netsimd(avd):
    """Test case to verify that a device is attached to netsimd."""
    assert len(netsim_client.NetsimClient().get_devices()) != 0
