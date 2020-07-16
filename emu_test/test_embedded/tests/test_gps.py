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
from aemu.proto.emulator_controller_pb2 import GpsState

from google.protobuf import empty_pb2

_EMPTY_ = empty_pb2.Empty()


@pytest.fixture
def gps_location():
    emu = pytest.emulator.get_emulator_controller()
    location = GpsState(latitude=39.237256, longitude=-123.150032, satellites=4)
    emu.setGps(location)
    return location


def set_and_get_gps(state):
    emu = pytest.emulator.get_emulator_controller()
    emu.setGps(state)
    retrieved = emu.getGps(_EMPTY_)
    assert pytest.approx(retrieved.latitude) == state.latitude
    assert pytest.approx(retrieved.longitude) == state.longitude
    assert pytest.approx(retrieved.speed) == state.speed
    assert pytest.approx(retrieved.bearing) == state.bearing
    assert pytest.approx(retrieved.altitude) == state.altitude
    assert pytest.approx(retrieved.satellites) == state.satellites


@pytest.mark.e2e
def test_gps_latitude_is_observable(gps_location):
    """Test observe latitude."""
    location = gps_location
    for inc in range(1, 100):
        location.latitude = location.latitude + 0.001
        set_and_get_gps(location)


@pytest.mark.e2e
def test_gps_longitude_is_observable(gps_location):
    """Test observe longitude."""
    location = gps_location
    for inc in range(1, 100):
        location.longitude = location.longitude + 0.001
        set_and_get_gps(location)


@pytest.mark.e2e
def test_gps_rotation_is_observable(gps_location):
    """Test observe rotation."""
    location = gps_location
    for direction in range(0, 360):
        location.bearing = direction
        set_and_get_gps(location)


@pytest.mark.e2e
def test_gps_speed_is_observable(gps_location):
    """Test observe speed."""
    location = gps_location
    for speed in range(0, 100):
        location.speed = speed
        set_and_get_gps(location)


@pytest.mark.e2e
def test_gps_altitude_is_observable(gps_location):
    """Test observe altitude."""
    location = gps_location
    for altitude in range(0, 100):
        location.altitude = altitude
        set_and_get_gps(location)
