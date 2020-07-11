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
from aemu.proto.emulator_controller_pb2 import PhysicalModelValue, ParameterValue


def set_and_get_model(emu, model_value):
    emu.setPhysicalModel(model_value)
    retrieved = emu.getPhysicalModel(PhysicalModelValue(target=model_value.target))
    assert retrieved.target == model_value.target
    assert len(model_value.value.data) == len(retrieved.value.data)
    for i in range(len(model_value.value.data)):
        assert pytest.approx(retrieved.value.data[i]) == retrieved.value.data[i]


@pytest.mark.e2e
def test_physical_rotation():
    """Test that setting the physical model is observable."""
    emu = pytest.emulator.get_emulator_controller()
    for x in [-180, 90, 0, 180]:
        for y in [-180, 90, 0, 180]:
            for z in [-180, 90, 0, 180]:
                set_and_get_model(
                    emu,
                    PhysicalModelValue(
                        target=PhysicalModelValue.ROTATION,
                        value=ParameterValue(data=[x, y, z]),
                    ),
                )
