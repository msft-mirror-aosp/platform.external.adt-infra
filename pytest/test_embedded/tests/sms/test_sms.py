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

from aemu.proto.emulator_controller_pb2 import (
    SmsMessage
)

@pytest.mark.e2e
@pytest.mark.timeout(timeout=10, func_only=True)
@pytest.mark.parametrize(
    "phone_number,text_message", [('987654321', 'Hello There')]
)
def test_send_inbound_sms_text_message(emulator_controller, phone_number, text_message):
    """Send inbound phone number and text message.

    Verify text message is received from phone number.

    Args:
      phone_number: phone number text message is sent from.
      text_message: contents of text message.
    """

    message = SmsMessage(
        srcAddress = phone_number,
        text = text_message
    )
    response = emulator_controller.sendSms(message)
    assert response.response == response.OK
