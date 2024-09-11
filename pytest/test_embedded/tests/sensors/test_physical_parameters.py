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

import logging
from enum import Enum

import pytest
from aemu.proto.emulator_controller_pb2 import (
    ParameterValue,
    PhysicalModelValue,
    Posture,
)

from emu.timing import wait_until


def is_equal(model_value, other, consider_equal={}) -> bool:
    """
    Checks whether the two PhysicalModelValues are approximately equal.

    Args:
        model_value (PhysicalModelValue): The first PhysicalModelValue for comparison.
        other (PhysicalModelValue): The second PhysicalModelValue for comparison.
        consider_equal (dict): Dictionary of values to consider as equal.

    Returns:
        bool: True if the two PhysicalModelValues are approximately equal, False otherwise.
    """
    for x, y in zip(other.value.data, model_value.value.data):
        if not (
            pytest.approx(x, rel=0.1) == y
            or (int(x) in consider_equal and consider_equal[int(x)] == pytest.approx(y))
        ):
            return False
    return True


async def set_and_get_model(emu_controller, model_value):
    """Executes set and get physical model rpc call
    Args:
      emu_controller : emulator controller
      model_value: physical model value of emulator
    """
    await emu_controller.setPhysicalModel(model_value)
    retrieved = await emu_controller.getPhysicalModel(
        PhysicalModelValue(target=model_value.target)
    )

    assert (
        retrieved.target == model_value.target
    ), "Target value for physical model  doesn't match"

    assert is_equal(model_value, retrieved), f"{model_value} != {retrieved}"


class Axis(Enum):
    X = 0
    Y = 1
    Z = 2


@pytest.mark.hardware
@pytest.mark.skip("Very flaky, the physical model appears non-deterministic")
@pytest.mark.parametrize("axis", [Axis.X, Axis.Y, Axis.Z])
async def test_physical_rotation_around_axis_will_update_magneto_meter(
    emulator_controller, mobly, at_home, axis
):
    """Test that setting the physical model is observable through the magneto meter.

    Note the physical model is not straightforwards, i.e. setting the physical model
    can result in unexpected changes (to see this in action look at the UI in the
    extended controls, device pose window, set all values to 0 and slide the Y axis around,
    can you get the Z & and X axis to 180 without modifying them?)

    This test merely validates that the magneto sensor will change and stabilizes.
    """
    physics = mobly("animation")

    async def reset_state():
        model_value = PhysicalModelValue(
            target=PhysicalModelValue.ROTATION,
            value=ParameterValue(data=[0, 0, 0]),
        )
        await emulator_controller.setPhysicalModel(model_value)
        assert await wait_until(physical_model_stabilized, timeout=2)

    def guest_magnetic_field():
        return physics.getMagnetometerReading()

    async def host_magnetic_field():
        state = await emulator_controller.getPhysicalModel(
            PhysicalModelValue(
                target=PhysicalModelValue.MAGNETIC_FIELD,
            )
        )
        return state.value.data

    async def physical_model_stabilized():
        host = await host_magnetic_field()
        guest = guest_magnetic_field()
        logging.info("Check if %s = %s", host, guest)
        return pytest.approx(host, abs=1) == guest

    for rotation in range(-179, 179, 5):
        await reset_state()
        data = [0, 0, 0]
        data[axis.value] = rotation
        model_value = PhysicalModelValue(
            target=PhysicalModelValue.ROTATION,
            value=ParameterValue(data=data),
        )
        await emulator_controller.setPhysicalModel(model_value)

        assert await wait_until(
            physical_model_stabilized, timeout=2, hz=2
        ), f"{pytest.approx(host_magnetic_field(), abs=1)} != {guest_magnetic_field()} ({model_value.value.data}) in a timely fashion."



@pytest.mark.hardware
@pytest.mark.parametrize(
    "test_name, physical_type_value, x, y, z",
    [
        ("Position", PhysicalModelValue.POSITION, 1, 1, 1),
        ("Magnetic_Field", PhysicalModelValue.MAGNETIC_FIELD, 21, 1, 40),
        ("Temperature", PhysicalModelValue.TEMPERATURE, 25, 0, 0),
        ("Proximity", PhysicalModelValue.PROXIMITY, 5, 0, 0),
        ("Light", PhysicalModelValue.LIGHT, 10000, 0, 0),
        ("Pressure", PhysicalModelValue.PRESSURE, 100, 0, 0),
        ("Humidity", PhysicalModelValue.HUMIDITY, 50, 0, 0),
        ("Velocity", PhysicalModelValue.VELOCITY, 20, 0, 0),
        ("HeartRate", PhysicalModelValue.HEART_RATE, 15, 0, 0),
        ("Wrist_Tilt", PhysicalModelValue.WRIST_TILT, 16, 0, 0),
    ],
)
def test_physical_model_value(
    emulator_controller, test_name, physical_type_value, x, y, z
):
    """Sends physical model value to the emulator.
    Test steps:
      1. Launch an emulator AVD
      2. Send physical model value to be set to emulator

    Verify:
      Physical model value is set correctly on the emulator.
    """
    set_and_get_model(
        emulator_controller,
        PhysicalModelValue(
            target=physical_type_value,
            value=ParameterValue(data=[x, y, z]),
        ),
    )



@pytest.mark.hardware
@pytest.mark.parametrize(
    "test_name, posture",
    [
        ("Posture_Unknown", Posture.POSTURE_UNKNOWN),
        ("Posture_Closed", Posture.POSTURE_CLOSED),
        ("Posture_Half_Opened", Posture.POSTURE_HALF_OPENED),
        ("Posture_Opened", Posture.POSTURE_OPENED),
        ("Posture_Flipped", Posture.POSTURE_FLIPPED),
        ("Posture_Tent", Posture.POSTURE_TENT),
        ("Posture_Max", Posture.POSTURE_MAX),
    ],
)
def test_physical_model_type_posture(emulator_controller, test_name, posture):
    """Sends physical type posture value to the emulator.

    Test steps:
      1. Launch an emulator AVD
      2. Send physical type posture value to be set to emulator

    Verify:
      Physical type posture is set correctly on the emulator.
    """
    set_and_get_model(
        emulator_controller,
        PhysicalModelValue(
            target=PhysicalModelValue.POSTURE,
            value=ParameterValue(data=[posture]),
        ),
    )
