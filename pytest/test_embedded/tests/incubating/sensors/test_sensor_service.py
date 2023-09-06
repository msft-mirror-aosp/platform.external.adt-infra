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
import logging
from aemu.proto.sensor_service_pb2 import ParameterValue, SensorValue
from aemu.proto.sensor_service_pb2_grpc import SensorServiceStub

from emu.timing import eventually, wait_until
from tests.test_utils import StreamingCall


def set_and_get_sensor(sensor_service, sensor_value):
    """Executes set and get sensor Rpc call
    Args:
      sensor_service : Emulator Controller
      sensor_value: SensorValue to emulator
    """
    sensor_service.setSensor(sensor_value)
    retrieved = None

    def get_sensor_equals_set_sensor():
        """
        Checks if the retrieved SensorValue object matches the provided SensorValue object.

        Returns:
            bool: True if the retrieved SensorValue object matches the provided SensorValue object, False otherwise.
        """
        nonlocal retrieved
        retrieved = sensor_service.getSensor(SensorValue(target=sensor_value.target))
        assert (
            retrieved.target == sensor_value.target
        ), "Target value for sensor doesn't match"

        for i in range(len(retrieved.value.data)):
            if pytest.approx(retrieved.value.data[i]) != sensor_value.value.data[i]:
                return False

        return True

    # We will try the request a few times, if the sensor value does not stabilize in
    # a seconds we will just give up.
    assert wait_until(
        get_sensor_equals_set_sensor, timeout=3
    ), f"Data for sensor doesn't match {sensor_value} != {retrieved}"


@pytest.mark.e2e
@pytest.mark.hardware
@pytest.mark.parametrize(
    "test_name, sensor_value, x, y, z",
    [
        ("Gyroscope", SensorValue.SENSOR_SENSOR_TYPE_GYROSCOPE, 1, 1, 1),
        ("Magnetic_Field", SensorValue.SENSOR_SENSOR_TYPE_MAGNETIC_FIELD, 21, 1, 40),
        ("Orientation", SensorValue.SENSOR_SENSOR_TYPE_ORIENTATION, 90, 0, 0),
        ("Temperature", SensorValue.SENSOR_SENSOR_TYPE_TEMPERATURE, 25, 0, 0),
        ("Proximity", SensorValue.SENSOR_SENSOR_TYPE_PROXIMITY, 5, 0, 0),
        ("Light", SensorValue.SENSOR_SENSOR_TYPE_LIGHT, 10000, 0, 0),
        ("Pressure", SensorValue.SENSOR_SENSOR_TYPE_PRESSURE, 100, 0, 0),
        ("Humidity", SensorValue.SENSOR_SENSOR_TYPE_HUMIDITY, 50, 0, 0),
        (
            "Magnetic_Field_Uncalibrated",
            SensorValue.SENSOR_SENSOR_TYPE_MAGNETIC_FIELD_UNCALIBRATED,
            20,
            5,
            40,
        ),
        (
            "Gyroscope_Uncalibrated",
            SensorValue.SENSOR_SENSOR_TYPE_GYROSCOPE_UNCALIBRATED,
            2,
            2,
            2,
        ),
    ],
)
@pytest.mark.timeout(timeout=20, func_only=True)
def test_sensor_value(service, test_name, sensor_value, x, y, z):
    """Sends sensor value to the emulator.
    Test steps:
      1. Launch an emulator AVD
      2. Send sensor value to be set to emulator

    Verify:
      Sensor value is set correctly on the emulator.
    """
    set_and_get_sensor(
        service(SensorServiceStub),
        SensorValue(
            target=sensor_value,
            value=ParameterValue(data=[x, y, z]),
        ),
    )


@pytest.mark.e2e
@pytest.mark.hardware
@pytest.mark.parametrize(
    "test_name, sensor_value, x, y, z",
    [
        ("Gyroscope", SensorValue.SENSOR_SENSOR_TYPE_GYROSCOPE, 1, 1, 1),
        ("Magnetic_Field", SensorValue.SENSOR_SENSOR_TYPE_MAGNETIC_FIELD, 21, 1, 40),
        ("Orientation", SensorValue.SENSOR_SENSOR_TYPE_ORIENTATION, 90, 0, 0),
        ("Temperature", SensorValue.SENSOR_SENSOR_TYPE_TEMPERATURE, 25, 0, 0),
        ("Proximity", SensorValue.SENSOR_SENSOR_TYPE_PROXIMITY, 5, 0, 0),
        ("Light", SensorValue.SENSOR_SENSOR_TYPE_LIGHT, 10000, 0, 0),
        ("Pressure", SensorValue.SENSOR_SENSOR_TYPE_PRESSURE, 100, 0, 0),
        ("Humidity", SensorValue.SENSOR_SENSOR_TYPE_HUMIDITY, 50, 0, 0),
        (
            "Magnetic_Field_Uncalibrated",
            SensorValue.SENSOR_SENSOR_TYPE_MAGNETIC_FIELD_UNCALIBRATED,
            20,
            5,
            40,
        ),
        (
            "Gyroscope_Uncalibrated",
            SensorValue.SENSOR_SENSOR_TYPE_GYROSCOPE_UNCALIBRATED,
            2,
            2,
            2,
        ),
    ],
)
@pytest.mark.timeout(timeout=20, func_only=True)
@pytest.mark.hardware
def test_sensor_value_events(service, test_name, sensor_value, x, y, z):
    expected = SensorValue(
        target=sensor_value,
        value=ParameterValue(data=[x, y, z]),
    )

    sensor_service: SensorServiceStub = service(SensorServiceStub)
    stream = sensor_service.receiveSensorEvents(SensorValue(target=sensor_value))

    def receives_an_update_event(sensor_event):
        logging.info("Received event %s", sensor_event)

        if sensor_event.target != expected.target:
            assert False, "This should never happen! Wronge event received!"

        for i in range(len(sensor_event.value.data)):
            if pytest.approx(sensor_event.value.data[i]) != expected.value.data[i]:
                return False

        return True

    with StreamingCall(stream) as stream:
        sensor_service.setSensor(expected)
        assert eventually(
            receives_an_update_event, stream
        ), "Did not receive an update notification, even though I registered."
