# Copyright 2021 The Android Open Source Project
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
from aemu.proto.emulator_controller_pb2 import Touch, TouchEvent


@pytest.mark.hardware
async def test_touch_event_identifier_ranges(emulator_controller):
    """Tests that we properly handle identifiers."""
    await emulator_controller.sendTouch(
        TouchEvent(touches=[Touch(x=661, y=1133, pressure=12, identifier=-23122)])
    )
    await emulator_controller.sendTouch(
        TouchEvent(touches=[Touch(x=661, y=1133, pressure=1)])
    )
    await emulator_controller.sendTouch(
        TouchEvent(touches=[Touch(x=335, y=940, identifier=-124543, pressure=1)])
    )
    await emulator_controller.sendTouch(
        TouchEvent(touches=[Touch(x=203, y=823, identifier=0)])
    )
    await emulator_controller.sendTouch(
        TouchEvent(touches=[Touch(x=203, y=823, identifier=-124543)])
    )
    await emulator_controller.sendTouch(
        TouchEvent(touches=[Touch(x=801, y=1281, identifier=-23122)])
    )


@pytest.mark.hardware
async def test_touch_event_identifier_to_many(emulator_controller):
    """Tests that we properly handle too many registered identifiers."""
    x = 1
    for j in range(20):
        for i in range(10):
            await emulator_controller.sendTouch(
                TouchEvent(
                    touches=[
                        Touch(x=i * 10, y=i * 10, pressure=12, identifier=j * 10 + i)
                    ]
                )
            )

        for i in range(10):
            await emulator_controller.sendTouch(
                TouchEvent(
                    touches=[
                        Touch(x=i * 10, y=i * 10, pressure=0, identifier=j * 10 + i)
                    ]
                )
            )
