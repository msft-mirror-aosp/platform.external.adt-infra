import pytest
from netsim_grpc import netsim_client

# TODO: Add this test to pre/postsubmit suites once stable.
@pytest.mark.netsim
@pytest.mark.multi
@pytest.mark.async_timeout(1080)
def test_two_devices_attach_to_netsimd(avds):
    """Test case to verify that a device is attached to netsimd."""
    assert len(netsim_client.NetsimClient().get_devices()) == 2
