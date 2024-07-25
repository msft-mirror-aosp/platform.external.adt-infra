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
from aemu.proto.emulator_controller_pb2 import SmsMessage
from emu.timing import eventually
import time


@pytest.mark.e2e
@pytest.mark.hardware
@pytest.mark.fast
@pytest.mark.parametrize("phone_number,text_message", [("987654321", "Hello There")])
async def test_send_inbound_sms_text_message(
    emulator_controller, phone_number, text_message
):
    """Send inbound phone number and text message.

    Verify text message is received from phone number.

    Args:
      phone_number: phone number text message is sent from.
      text_message: contents of text message.
    """

    message = SmsMessage(srcAddress=phone_number, text=text_message)
    response = await emulator_controller.sendSms(message)
    assert response.response == response.OK


@pytest.fixture
async def allow_sms_messages(emulator):
    """
    This fixture grants necessary SMS permissions to mobly snippet.
    """
    await emulator.adb.shell(
        "pm grant com.google.android.mobly.snippet.bundled android.permission.READ_SMS"
    )
    await emulator.adb.shell(
        "pm grant com.google.android.mobly.snippet.bundled android.permission.RECEIVE_SMS"
    )


@pytest.mark.e2e
@pytest.mark.hardware
@pytest.mark.fast
@pytest.mark.parametrize("phone_number,text_message", [("987654321", "Hello There")])
async def test_send_inbound_sms_text_message_received_by_mobly(
    emulator_controller, mbs, allow_sms_messages, phone_number, text_message
):
    """
    This test verifies that an inbound SMS text message is received by Mobly.

    Args:
        emulator_controller: A controller for interacting with the emulator.
        mbs: An object for interacting with the Mobly Snippet Binder.
        allow_sms_messages: A fixture to grant SMS permissions (automatically applied).
        phone_number: The phone number from which the SMS will be sent.
        text_message: The text content of the SMS.
    """

    message = SmsMessage(srcAddress=phone_number, text=text_message)
    response = await emulator_controller.sendSms(message)
    assert response.response == response.OK

    # We expect the message with a few 5 seconds, this will raise an exception
    # in case of failure.
    message = mbs.waitForSms(5000)["data"]
    assert message["OriginatingAddress"] == phone_number
    assert message["MessageBody"] == text_message
