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
import re
import time

import google.protobuf.text_format

from emu.timing import eventually, wait_until
from functools import partial
from PIL import ImageGrab
import deqr
import logging
import asyncio

def fmt_proto(msg):
    """Formats a protobuf message as a single line."""
    return google.protobuf.text_format.MessageToString(msg, as_one_line=True)


def time_to_str(epoch_in_seconds):
    """Formats an epoch time in seconds into a human readable string."""
    s, ms = divmod(epoch_in_seconds * 1000, 1000)
    return "{}.{:03d}".format(
        time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(epoch_in_seconds)), int(ms)
    )


def wait_for_regex(stream, regex, max_wait):
    """Waits for the given regex to appear on the logcat stream,
    or until max_wait time has passed.

    Returns the match, or None in case of timeout.
    """
    compiled = re.compile(regex)
    return eventually(compiled.match, stream, timeout=max_wait)


async def decode_qrcodes(payloads: list[str]):
    """Return True if all QR codes with <payloads> appear in the series of screenshots.
    """
    decoder = deqr.QuircDecoder()
    async def detect_qrcode(payload: str):
        """Take a screenshot and return True if a QR code with <payload> is detected.
        """
        screenshot = ImageGrab.grab()
        data = decoder.decode(screenshot)
        if data is None or len(data) == 0:
            return False
        qrcode = data[0]
        data_payload = qrcode.data_entries[0].data
        return payload == data_payload

    logging.info(f"Starting the QR codes detection.")
    for payload in payloads:
        timeout = False
        detected = False
        try:
            detected = await wait_until(partial(detect_qrcode, payload), timeout=15)
        except asyncio.TimeoutError:
            timeout = True
        if not detected or timeout:
            logging.info(f"Couldn't detect payload {payload}.")
            return False
        logging.info(f"Detected payload {payload}.")
    return True
