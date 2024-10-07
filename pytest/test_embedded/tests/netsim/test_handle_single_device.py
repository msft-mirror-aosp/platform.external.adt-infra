import pytest
from netsim_grpc import netsim_client


@pytest.mark.boot
@pytest.mark.netsim
@pytest.mark.async_timeout(1080)
def test_device_attaches_to_netsimd(avd):
    """Test case to verify that a device is attached to netsimd."""
    assert len(netsim_client.NetsimClient().get_devices()) != 0


@pytest.mark.boot
@pytest.mark.netsim
@pytest.mark.async_timeout(1080)
def test_netsim_patch_and_reset(avd):
    """Test case to verify that patch and reset device in netsim"""
    netsim = netsim_client.NetsimClient()
    initial_devices = netsim.get_devices()
    assert len(initial_devices) != 0

    # Patch Device Position and Orientation
    device_name = list(initial_devices.keys())[0]
    patch_position = netsim_client.model.Position(x=1, y=2, z=3)
    patch_orientation = netsim_client.model.Orientation(yaw=30, pitch=60, roll=90)
    assert netsim.set_position(
        device_name, position=patch_position, orientation=patch_orientation
    )

    # Verfiy the new Position and Orientation
    post_patch_device = netsim.get_devices()[device_name]
    assert post_patch_device.position == patch_position
    assert post_patch_device.orientation == patch_orientation

    # Attempt Reset and Verify with Position and Orientation
    netsim.reset()
    post_reset_device = netsim.get_devices()[device_name]
    assert post_reset_device.position == netsim_client.model.Position(x=0, y=0, z=0)
    assert post_reset_device.orientation == netsim_client.model.Orientation(
        yaw=0, pitch=0, roll=0
    )


@pytest.mark.boot
@pytest.mark.netsim
@pytest.mark.async_timeout(1080)
def test_netsim_radio_state_toggle(avd):
    """Test case to verify patch radio in netsim"""
    netsim = netsim_client.NetsimClient()
    initial_devices = netsim.get_devices()
    assert len(initial_devices) != 0

    # Turn off Radio State (BLE) of Device and Verify
    device_name = list(initial_devices.keys())[0]
    patch_radio = netsim_client.model.PhyKind.BLUETOOTH_LOW_ENERGY
    patch_state = False
    netsim.set_radio(device_name, patch_radio, patch_state)
    post_patch_device = netsim.get_devices()[device_name]
    for chip in post_patch_device.chips:
        if chip.kind == netsim_client.common.ChipKind.BLUETOOTH:
            assert chip.bt.low_energy.state is False

    # Turn on Radio State (BLE) of Device and Verify
    patch_state = True
    netsim.set_radio(device_name, patch_radio, patch_state)
    post_patch_device = netsim.get_devices()[device_name]
    for chip in post_patch_device.chips:
        if chip.kind == netsim_client.common.ChipKind.BLUETOOTH:
            assert chip.bt.low_energy.state is True

    # Turn off Radio State (BLE) of Device, Reset and Verify if it's on
    patch_state = False
    netsim.set_radio(device_name, patch_radio, patch_state)
    netsim.reset()
    post_patch_reset_device = netsim.get_devices()[device_name]
    for chip in post_patch_reset_device.chips:
        if chip.kind == netsim_client.common.ChipKind.BLUETOOTH:
            assert chip.bt.low_energy.state is True
