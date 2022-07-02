import pytest
from google.protobuf import empty_pb2


@pytest.mark.e2e
@pytest.mark.timeout(timeout=180, func_only=True)
def test_booted(emulator_controller):
    """Make sure the emulator status is set to booted."""
    response = emu_controller.getStatus(empty_pb2.Empty())
    assert response.booted
