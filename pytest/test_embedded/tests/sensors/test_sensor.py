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
from aemu.proto.emulator_controller_pb2 import PhysicalModelValue
from aemu.proto.emulator_controller_pb2_grpc import EmulatorControllerStub

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
    assert await wait_until(
        get_sensor_equals_set_sensor, timeout=3
    ), f"Data for sensor doesn't match {sensor_value} != {retrieved}"


@pytest.mark.hardware
@pytest.mark.sanity
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
        ("Acceleration", SensorValue.ACCELERATION, 10, 0, 0),
        ("Acceleration_Uncalibrated", SensorValue.ACCELERATION_UNCALIBRATED, 25, 0, 0),
        # BUG: b/326662659 HEART_RATE and RGBC_LIGHT sensor values not available for phone AVD
        # ("Heart_Rate", SensorValue.HEART_RATE, 60, 0, 10),
        # ("RGBC_Light", SensorValue.RGBC_LIGHT, 255, 0, 0),
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


@pytest.mark.hardware
@pytest.mark.fast
async def test_accelerometer_updates_with_model_change(avd):
    """Ensure the accelerometer values change when the 3D (rotation) model changes.

    Args:
        avd (BaseEmulator): Fixture that gives access to the running emulator.

    Test steps:
        1. Launch an emulator AVD.
        2. Store current acceleration sensor data.
        3. Changing the device's 3D model by applying a rotation (Verify).

    Verify:
        Acceleration data changes.
    """
    # Store initial orientation and acceleration data.
    emulator_controller = EmulatorControllerStub(avd.channel)
    initial_orientation = await emulator_controller.getSensor(
        SensorValue(target=SensorValue.ORIENTATION)
    )
    initial_acceleration = await emulator_controller.getSensor(
        SensorValue(target=SensorValue.ACCELERATION)
    )

    # Rotate the emulator (will propagate to the the extended controls ui).
    await emulator_controller.setPhysicalModel(
        PhysicalModelValue(
            target=PhysicalModelValue.ROTATION,
            value=ParameterValue(data=[-45, -45, -45]),
        )
    )

    # Check new orientation data.
    orientation = await emulator_controller.getSensor(
        SensorValue(target=SensorValue.ORIENTATION)
    )
    assert initial_orientation.value.data != pytest.approx(
        orientation.value.data
    ), "Orientation sensor data wasn't updated"

    # Check new acceleration data.
    acceleration = await emulator_controller.getSensor(
        SensorValue(target=SensorValue.ACCELERATION)
    )

    assert initial_acceleration.value.data != pytest.approx(
        acceleration.value.data
    ), "Acceleration sensor data didn't change after rotation"
