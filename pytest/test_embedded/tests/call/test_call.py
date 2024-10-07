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
from aemu.proto.emulator_controller_pb2 import PhoneCall, PhoneResponse


async def send_phone_call(emu_controller, phone_call, expected_phone_response):
    """Executes sendPhone Rpc call
    Args:
      emu_controller : emulator controller
      phone_call: phone Call to emulator
      expected_phone_response: expected PhoneResponse.response.
    """
    phone_response = await emu_controller.sendPhone(phone_call)
    assert phone_response.response == expected_phone_response, (
        "Phone response is not %s " % expected_phone_response
        + "but was %s" % phone_response.response
    )


@pytest.mark.hardware
@pytest.mark.parametrize(
    "test_name, phone_call_operation",
    [
        ("InitCall", PhoneCall.InitCall),
        ("AcceptCall", PhoneCall.AcceptCall),
        ("RejectCallExplicit", PhoneCall.RejectCallExplicit),
        ("RejectCallBusy", PhoneCall.RejectCallBusy),
        ("DisconnectCall", PhoneCall.DisconnectCall),
        ("PlaceCallOnHold", PhoneCall.PlaceCallOnHold),
        ("TakeCallOffHold", PhoneCall.TakeCallOffHold),
    ],
)
@pytest.mark.hardware
@pytest.mark.sanity
@pytest.mark.skipos("win", "Phone response is InvalidAction instead of OK  b/254332148")
async def test_inbound_call(
    at_home, emulator_controller, test_name, phone_call_operation
):
    """Sends phone call to the emulator.

    Test steps:
      1. Launch an emulator AVD
      2. Send phone call to emulator

    Verify:
      Phone call operation is successful.
    """
    await send_phone_call(
        emulator_controller,
        PhoneCall(
            operation=phone_call_operation,
            number="1234567890",
        ),
        PhoneResponse.OK,
    )


@pytest.mark.hardware
@pytest.mark.async_timeout(1080)
async def test_inbound_call_bad_operation(at_home, emulator_controller):
    """Sends invalid phone call operation to the emulator.

    Test steps:
      1. Launch an emulator AVD
      2. Send invalid phone call operation to the emulator

    Verify:
      Phone Response has Bad Operation.
    """
    send_phone_call(
        emulator_controller,
        PhoneCall(
            operation=100,
            number="1234567890",
        ),
        PhoneResponse.BadOperation,
    )


@pytest.mark.hardware
@pytest.mark.skipos("win", "reason: b/305810509 - test timeout.")
def test_inbound_call_bad_number(at_home, emulator_controller):
    """Sends phone call from a bad number to the emulator.

    Test steps:
      1. Launch an emulator AVD
      2. Send phone call from a bad number to the emulator

    Verify:
      Phone Response has Bad Number.
    """
    send_phone_call(
        emulator_controller,
        PhoneCall(
            operation=PhoneCall.InitCall,
            number="aaa",
        ),
        PhoneResponse.BadNumber,
    )
