# Copyright 2022 The Android Open Source Project
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
from aemu.proto.emulator_controller_pb2 import BrightnessValue


async def set_and_get_brightness(emu_controller, brightness_value):
    """Executes set and get brightness Rpc call
    Args:
      emu_controller : Emulator Controller
      brightness_value: brightness_value to emulator
    """
    await emu_controller.setBrightness(brightness_value)
    retrieved = await emu_controller.getBrightness(
        BrightnessValue(target=brightness_value.target)
    )

    assert (
        retrieved.target == brightness_value.target
    ), "Target value for Brightness doesn't match"


@pytest.mark.hardware
@pytest.mark.parametrize(
    "test_name, brightness_value",
    [
        ("Lcd", BrightnessValue.LCD),
        ("Keyboard", BrightnessValue.KEYBOARD),
        ("Button", BrightnessValue.BUTTON),
    ],
)
async def test_brightness_value(emulator_controller, test_name, brightness_value):
    """Sends brightness value to the emulator.

    Test steps:
      1. Launch an emulator AVD
      2. Send brightness value to be set to emulator

    Verify:
      Brightness value is set correctly on the emulator.
    """
    set_and_get_brightness(
        emulator_controller,
        BrightnessValue(target=brightness_value, value=101),
    )
