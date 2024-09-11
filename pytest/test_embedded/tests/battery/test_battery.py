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
from aemu.proto.emulator_controller_pb2 import BatteryState
from google.protobuf import empty_pb2

_EMPTY_ = empty_pb2.Empty()


async def set_and_get_battery(emu_controller, battery_state):
    """Executes set and get battery rpc call
    Args:
      emu_controller : emulator controller
      battery_state: battery state of emulator
    """
    await emu_controller.setBattery(battery_state)
    retrieved = await emu_controller.getBattery(_EMPTY_)

    assert retrieved.status == battery_state.status, "Battery status doesn't match"
    assert retrieved.health == battery_state.health, "Battery health doesn't match"
    assert (
        retrieved.hasBattery == battery_state.hasBattery
    ), "Battery hasBattery doesn't match"
    assert (
        retrieved.isPresent == battery_state.isPresent
    ), "Battery isPresent doesn't match"
    assert (
        retrieved.chargeLevel == battery_state.chargeLevel
    ), "Battery chargeLevel doesn't match"


@pytest.mark.hardware
@pytest.mark.parametrize(
    "test_name, battery_status, battery_health",
    [
        ("StatusUnknown_HealthFailed", BatteryState.UNKNOWN, BatteryState.FAILED),
        ("StatusDischarging_HealthDead", BatteryState.DISCHARGING, BatteryState.DEAD),
        (
            "StatusNotCharging_HealthOverVoltage",
            BatteryState.NOT_CHARGING,
            BatteryState.OVERVOLTAGE,
        ),
        (
            "StatusDisCharging_HealthOverHeated",
            BatteryState.DISCHARGING,
            BatteryState.OVERHEATED,
        ),
        ("StatusCharging_HealthGood", BatteryState.CHARGING, BatteryState.GOOD),
    ],
)
async def test_battery_status_health(
    emulator_controller, test_name, battery_status, battery_health
):
    """Sends battery state to the emulator.

    Test steps:
      1. Launch an emulator AVD
      2. Send battery state to be set to emulator

    Verify:
      Battery state is set correctly on the emulator.
    """
    await set_and_get_battery(
        emulator_controller,
        BatteryState(
            status=battery_status,
            health=battery_health,
            hasBattery=True,
            isPresent=False,
            chargeLevel=12,
        ),
    )
