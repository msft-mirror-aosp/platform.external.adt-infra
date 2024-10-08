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

import lxml.etree as ET
from emu.timing import eventually, wait_until
from functools import partial
from PIL import ImageGrab
from emu.emulator import BaseEmulator
from emu.images.convert import proto_to_pillow
from aemu.proto.emulator_controller_pb2 import ImageFormat
from pathlib import Path
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


async def decode_qrcodes(payloads: list[str], emulator_controller=None):
    """Return True if all QR codes with <payloads> appear in the series of screenshots.

    Notes:
        If 'emulator controller' is None (default), screnshots of the entire screen
        are taken (using PIL).
    """
    decoder = deqr.QuircDecoder()

    async def detect_qrcode(payload: str):
        """Take a screenshot and return True if a QR code with <payload> is detected."""
        if emulator_controller is not None:
            img = await emulator_controller.getScreenshot(ImageFormat())
            screenshot = proto_to_pillow(img)
        else:
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


async def get_window_dump(avd: BaseEmulator) -> str:
    # Use uiautomator to return an XML dump of current UI hierarchy
    window_dump = await avd.adb.exec_out(f"uiautomator dump /dev/tty > /dev/null")
    assert (
        "uiautomator: inaccessible or not found" not in window_dump
    ), "Uiautomator binary not found!"
    return window_dump


def get_center_coords(bounds: str) -> tuple:
    # Return the center coordinates (x, y) from element bounds string '[x0y0][x1 y1]'
    coords = list(map(int, bounds[1:-1].replace("][", ",").split(",")))
    return ((coords[0] + coords[2]) / 2, (coords[1] + coords[3]) / 2)


async def click_button(
    avd,
    resource_id=None,
    text=None,
    parent_resource_id=None,
    content_desc=None,
    display_id=-1,
    long_click=False,
):
    """Locate a UI button and tap its center

    Args:
        avd (BaseEmulator): the running emulator.
        resource_id (str, optional): Resource ID of the button. Defaults to None.
        text (str, optional): Button text. Defaults to None.
        parent_resource_id (str, optional): Resource ID of parent node.
                                            Defaults to None.
        content_desc (str, optional): Content descritpion. Defaults to None.
        display_id (str, optional): the ID of the display to be tapped.
                                    Defaults to -1.
        long_click (bool, optional): True to long-click the button.
                                     Defaults to False.
    Returns:
        True: If the button with the given properties is located and clicked.
              False otherwise.
    """
    node_list = []

    async def _locate_button():
        """Locate the button and return True if a clickable bound is found"""
        window_dump = await get_window_dump(avd)
        try:
            xml = ET.fromstring(window_dump.encode("UTF-8"))
        except ET.XMLSyntaxError:
            logging.error("Unable to parse: %s", window_dump)
            return False

        # Construct a xpath expression to locate the button node
        xpath_expression = ""
        properties = []
        if parent_resource_id is not None:
            xpath_expression += f"//node[@resource-id='{parent_resource_id}']"
        if resource_id is not None:
            properties.append(f"@resource-id='{resource_id}'")
        if text is not None:
            properties.append(f"@text='{text}'")
        if content_desc is not None:
            properties.append(f"@content-desc='{content_desc}'")
        xpath_expression += f"//node[{' and '.join(properties)}]"
        node = xml.xpath(xpath_expression)
        # Find a clickable bound (iterate back to the parent node if needed)
        clickable = "clickable" if not long_click else "long-clickable"
        while node is not None and len(node) == 1 and node[0].get(clickable) == "false":
            node[0] = node[0].getparent()
        if node is not None and len(node) == 1:
            node_list.append(node[0])
            return True

    button_located = await eventually(_locate_button, timeout=20)
    if not button_located:
        logging.error("Couldn't locate button.")
        return False
    logging.info("The button node was located.")

    bounds = node_list[0].get("bounds")
    if bounds is None:
        logging.error("Didn't find a clickable bound.")
        return False

    logging.info("Attempting to tap the button ...")
    center_coords = get_center_coords(bounds)
    if not long_click:
        cmd = ["input", "-d", display_id, "tap"] + list(center_coords)
    else:
        cmd = ["input", "-d", display_id, "swipe"] + list(center_coords) * 2 + ["2000"]

    await avd.adb.shell(" ".join([*map(str, cmd)]))
    logging.info(f"Sent the adb shell command '{' '.join(map(str, cmd))}'")
    return True


def check_boot_from_snapshot(avdpath) -> bool:
    mypath = Path(avdpath, "snapshot.trace")
    with open(mypath) as fp:
        for line in fp:
            line.rstrip()
            logging.info("reading line '%s'", line)
            if "load_succeeded" in line:
                return True

    return False
