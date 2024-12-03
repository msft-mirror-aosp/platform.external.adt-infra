# -*- coding: utf-8 -*-
# Copyright 2024 The Android Open Source Project
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
import logging
from pathlib import Path

import pytest

qrcode_html_fmt = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
    <style>
        body, html {{
            margin: 0;
            padding: 0;
            height: 100%;
            display: flex;
            justify-content: center;
            align-items: center;
            overflow: hidden;
        }}
        img {{
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
        }}
    </style>
    </head>
    <body>
    <img src="file://{}" alt="Image">
    </body>
    </html>
"""


@pytest.fixture
async def qrcode_png(emulator):
    """A fixture that access a PNG image with a pre-encoded QR code.

    Args:
        emulator (BaseEmulator): Fixture that gives access to the configured emulator.

    Returns:
        An instance of the Qrcode class. The class attributes are:
        src (str): The path of the source PNG image.
        path (str): Destination path of the PNG image on the emulator.
        payload (str): The pre-encoded payload of the QR code image.
        The 'show' method can be used to display the image on the display
        identified by the 'display_id' argument (by default, the primary display).

    Notes:
        1. If the emulator is not alive, the push method should be used later
           to push the QR code to the emulator.
        2. An html page that can be used to display the QR code in a centered
           resizable html container is stored in the path 'self.html'.
    """

    class Qrcode:
        """A class to push a PNG QRcode with a given payload to /sdcard/Download"""

        def __init__(self, src: str, payload: str):
            self.pushed = False
            self.src = src
            self.payload = payload
            self.path = Path("/sdcard/Download") / self.src.name
            self.html = (
                Path("/sdcard/Android/data/com.android.chrome/files/Download/")
                    / "qrcode.html"
            )
        async def _create_qrcode_html(self):
            await emulator.adb.shell(f"mkdir -p {self.html.parent}")
            qrcode_html= qrcode_html_fmt.format(self.path)
            await emulator.adb.shell(f'echo "{qrcode_html}" > {self.html}')
            await emulator.adb.shell(f'chmod +r {self.html}')

        async def push(self):
            logging.info(f"Pushing '{self.src}' to '{self.path}'")
            await emulator.adb.push(self.src, self.path)
            await self._create_qrcode_html()
            self.pushed = True

        async def show(self, display_id=0):
            """Show the PNG image on display with id <display_id>"""
            if not self.pushed:
                await self.push()
            await emulator.stop_activity("com.google.android.apps.photos")
            await emulator.start_activity(
                "com.google.android.apps.photos/.pager.HostPhotoPagerActivity",
                params=f'-a android.intent.action.VIEW -W -d file://{self.path} -t "image/PNG"'
                + (f" --display {display_id}" if display_id != 0 else ""),
            )
            logging.info(f"Launched the QR code PNG image on display '{display_id}'")

    src = (
        Path(__file__).parents[2]
        / "cfg"
        / "qrcode_uzNYdXGMb0kW7qXDejO0niE6liaPm1m0.png"
    )
    payload = "uzNYdXGMb0kW7qXDejO0niE6liaPm1m0"

    assert src.exists(), f"File '{src}' doesn't exist."
    qrcode = Qrcode(src, payload)
    if emulator.is_alive():
        await qrcode.push()
    return qrcode


@pytest.fixture
async def qrcodes_mp4(avd):
    """A fixture that gives access to a MP4 video containing a series of QR codes.

    The fixture pushes a 15-second MP4 video to /sdcard/Download, displaying a
    series of three images with QR codes, each one shown for 5 seconds.

    Args:
        avd (BaseEmulator): Fixture that gives access to the configured emulator.

    Returns:
        An instance of the Qrcodes class. The class attributes are:

        src (str): The path of the source video file.
        path (str): The path of the video on the emulator.
        payloads (list): The pre-encoded payloads of the QR codes displayed
                         in the video.

        The 'play' method can be used to play the mp4 video on the display
        identified by the 'display_id' argument (by default, the primary display).

    Notes:
        The deqr package along with pillow can be used to decode a screenshot
        containing a QR code.
    """

    class Qrcodes:
        """A class to handle a MP4 video with pre-encoded QRcodes"""

        def __init__(self, src: str, payloads: list):
            self.src = src
            self.payloads = payloads
            self.path = Path("/sdcard/Download") / self.src.name

        async def _push(self):
            logging.info(f"Pushing '{self.src}' to '{self.path}'")
            await avd.adb.push(self.src, self.path)

        async def play(self, display_id=0):
            await avd.stop_activity("com.google.android.apps.photos")
            await avd.start_activity(
                "com.google.android.apps.photos/.pager.HostPhotoPagerActivity",
                params=f'-a android.intent.action.VIEW -d file://{self.path} -t "video/*"'
                + (f" --display {display_id}" if display_id != 0 else ""),
            )
            logging.info(f"Started QR codes video on display '{display_id}'")

    src_video = Path(__file__).parents[2] / "cfg" / "qrcodes.mp4"
    payloads = [
        "uzNYdXGMb0kW7qXDejO0niE6liaPm1m0",
        "W6fEti4U7ImHU1mxBXkLpOehomty7mTM",
        "tAdFTEYPzbOw6qXBR1jyvzFohsx1gfdz",
    ]

    assert src_video.exists(), f"File '{src_video}' doesn't exist."
    qrcodes = Qrcodes(src_video, payloads)
    await qrcodes._push()
    return qrcodes
