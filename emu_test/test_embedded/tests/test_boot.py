import pytest
from google.protobuf import empty_pb2


@pytest.mark.e2e
def test_booted():
    """Make sure the emulator status is set to booted."""
    grpc = pytest.emulator.get_emulator_controller()
    response = grpc.getStatus(empty_pb2.Empty())
    assert response.booted
