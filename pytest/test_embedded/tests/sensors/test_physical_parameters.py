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

from aemu.proto.emulator_controller_pb2 import (
    PhysicalModelValue,
    ParameterValue,
    Posture,
)


def set_and_get_model(emu_controller, model_value):
    """Executes set and get physical model rpc call
    Args:
      emu_controller : emulator controller
      model_value: physical model value of emulator
    """
    emu_controller.setPhysicalModel(model_value)
    retrieved = emu_controller.getPhysicalModel(
        PhysicalModelValue(target=model_value.target)
    )

    assert (
        retrieved.target == model_value.target
    ), "Target value for physical model  doesn't match"

    for i in range(len(retrieved.value.data)):
        assert pytest.approx(retrieved.value.data[i]) == pytest.approx(
            model_value.value.data[i]
        ), "Data for physical model  doesn't match"


@pytest.mark.e2e
@pytest.mark.hardware
@pytest.mark.timeout(timeout=20, func_only=True)
@pytest.mark.skipos('all', 'getPhysicalModel and SetPhysicalModel for PhysicalModelValue.ROTATION does not match b/254898806')
def test_physical_rotation(emulator_controller):
    """Test that setting the physical model is observable."""
    for x in [-180, 90, 0, 180]:
        for y in [-180, 90, 0, 180]:
            for z in [-180, 90, 0, 180]:
                set_and_get_model(
                    emulator_controller,
                    PhysicalModelValue(
                        target=PhysicalModelValue.ROTATION,
                        value=ParameterValue(data=[x, y, z]),
                    ),
                )


@pytest.mark.e2e
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
@pytest.mark.timeout(timeout=20, func_only=True)
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


@pytest.mark.e2e
@pytest.mark.hardware
@pytest.mark.timeout(timeout=20, func_only=True)
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
