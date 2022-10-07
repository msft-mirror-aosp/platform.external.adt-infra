import pytest
from google.protobuf import empty_pb2


# This will run the tests in this module using this
# user configuration. This will fetch an image with api 33 and
# tag.id "google_apis"
#
# On M1 this will resolve to:  system-images;android-33;google_apis;arm64-v8a                                           | 5            | Google APIs ARM 64 v8a System Image
# On X64 this will resolve to: system-images;android-33;google_apis;x86_64
# avd_config = {"api": "33", "tag.id": "google_apis"}

@pytest.mark.e2e
@pytest.mark.timeout(timeout=180, func_only=True)
def test_booted(emulator_controller):
    """Make sure the emulator status is set to booted."""
    response = emulator_controller.getStatus(empty_pb2.Empty())
    assert response.booted
