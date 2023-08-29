# Copyright 2020 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pytest

from google.protobuf.empty_pb2 import Empty

from aemu.proto.emulator_controller_pb2 import GpsState


@pytest.mark.timeout(timeout=10, func_only=True)
@pytest.mark.parametrize(
    "latitude,longitude,speed,bearing,altitude,satellites",
    [(37.0, -122.0, 0.0, 0.0, 0.0, 1), (100.0, 200.0, 0.0, 0.0, 100.0, 1)],
)
def test_gps(
    emulator_controller, latitude, longitude, speed, bearing, altitude, satellites
):
    """Set emulator gps state to specified parameters

    Verifies gps state is set as expected

    Args:
      latitude: latitude of gps coordinates
      longitude: longitude of gps coordinates
      speed: speed at which the device is travelling
      bearing: direction of travel
      altitude: altitude of gps coordinates
      satellites: specifies number of satellites from which coordinated are "derived"
    """
    expected_gps_state = GpsState(
        latitude=latitude,
        longitude=longitude,
        speed=speed,
        bearing=bearing,
        altitude=altitude,
        satellites=satellites,
    )

    emulator_controller.setGps(expected_gps_state)
    actual_gps_state = emulator_controller.getGps(Empty())

    assert actual_gps_state.latitude == latitude
    assert actual_gps_state.longitude == longitude
    assert actual_gps_state.speed == speed
    assert actual_gps_state.bearing == bearing
    assert actual_gps_state.altitude == altitude
    assert actual_gps_state.satellites == satellites
