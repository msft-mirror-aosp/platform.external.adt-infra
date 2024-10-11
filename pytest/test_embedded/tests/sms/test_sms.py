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
import asyncio
import logging
import threading
import time


@pytest.mark.hardware
@pytest.mark.fast
@pytest.mark.parametrize("phone_number,text_message", [("987654321", "Hello There")])
async def test_send_inbound_sms_text_message(
    emulator_controller,
    logcat,
    phone_number,
    text_message,
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


@pytest.mark.hardware
@pytest.mark.fast
# @pytest.mark.skipos("mac", "reason: timeout on mac.")
# @pytest.mark.skipos("m1", "reason: timeout on m1.")
@pytest.mark.parametrize("phone_number,text_message", [("987654321", "Hello There")])
async def test_send_inbound_sms_text_message_received_by_mobly(
    emulator_controller, logcat, mbs, allow_sms_messages, phone_number, text_message
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

    # Function to execute mbs.waitForSms in a separate thread
    message = {}
    sms_received = False
    running = False
    wait_time = None

    def wait_for_sms():
        nonlocal message, sms_received, wait_time
        wait_time = time.time()
        logging.info("Waiting for sms.")
        message = mbs.waitForSms(5000)["data"]
        sms_received = True

    thread = threading.Thread(target=wait_for_sms)
    thread.start()

    # Make sure we are listening for messages before we send them
    # TODO: Figure out how to do this with condition variables?
    await asyncio.sleep(0.5)

    # Now send the actual message.
    logging.info("Sending sms.")
    sms = SmsMessage(srcAddress=phone_number, text=text_message)
    response = await emulator_controller.sendSms(sms)
    assert response.response == response.OK

    # We will wait at most 5 secs.
    thread.join()

    assert sms_received
    assert message["OriginatingAddress"] == phone_number
    assert message["MessageBody"] == text_message
