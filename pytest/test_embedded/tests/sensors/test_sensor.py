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
from aemu.proto.emulator_controller_pb2 import ParameterValue, SensorValue

from emu.timing import wait_until


async def set_and_get_sensor(emu_controller, sensor_value):
    """Executes set and get sensor Rpc call
    Args:
      emu_controller : Emulator Controller
      sensor_value: SensorValue to emulator
    """
    await emu_controller.setSensor(sensor_value)
    retrieved = None

    async def get_sensor_equals_set_sensor():
        """
        Checks if the retrieved SensorValue object matches the provided SensorValue object.

        Returns:
            bool: True if the retrieved SensorValue object matches the provided SensorValue object, False otherwise.
        """
        nonlocal retrieved
        retrieved = await emu_controller.getSensor(
            SensorValue(target=sensor_value.target)
        )
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
        ("Gyroscope", SensorValue.GYROSCOPE, 1, 1, 1),
        ("Magnetic_Field", SensorValue.MAGNETIC_FIELD, 21, 1, 40),
        ("Orientation", SensorValue.ORIENTATION, 90, 0, 0),
        ("Temperature", SensorValue.TEMPERATURE, 25, 0, 0),
        ("Proximity", SensorValue.PROXIMITY, 5, 0, 0),
        ("Light", SensorValue.LIGHT, 10000, 0, 0),
        ("Pressure", SensorValue.PRESSURE, 100, 0, 0),
        ("Humidity", SensorValue.HUMIDITY, 50, 0, 0),
        (
            "Magnetic_Field_Uncalibrated",
            SensorValue.MAGNETIC_FIELD_UNCALIBRATED,
            20,
            5,
            40,
        ),
        ("Gyroscope_Uncalibrated", SensorValue.GYROSCOPE_UNCALIBRATED, 2, 2, 2),
    ],
)
async def test_sensor_value(emulator_controller, test_name, sensor_value, x, y, z):
    """Sends sensor value to the emulator.
    Test steps:
      1. Launch an emulator AVD
      2. Send sensor value to be set to emulator

    Verify:
      Sensor value is set correctly on the emulator.
    """
    await set_and_get_sensor(
        emulator_controller,
        SensorValue(
            target=sensor_value,
            value=ParameterValue(data=[x, y, z]),
        ),
    )
