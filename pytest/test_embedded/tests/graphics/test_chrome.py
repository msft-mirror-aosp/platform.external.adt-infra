# Copyright 2023 The Android Open Source Project
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
import logging
from aemu.proto.emulator_controller_pb2 import ImageFormat
from aemu.proto.emulator_controller_pb2_grpc import EmulatorControllerStub

from emu.timing import eventually, wait_until
from tests.test_utils import decode_qrcodes


chrome_pkg = "com.android.chrome"
chrome_cmp = f"{chrome_pkg}/com.google.android.apps.chrome.Main"

purple_html = """
<!DOCTYPE html>
<html>
  <head>
    <style>
      body {
        background-color:rgb(255, 0, 255);
      }
    </style>
  </head>
</html>
"""
purple_path = f"/sdcard/Android/data/{chrome_pkg}/files/Download"


async def prepare_chrome(avd):
    """
    Pytest fixture that launches Chrome and configures it
    to skip the welcome page.

    This fixture prepares the Chrome application on an
    Android Virtual Device (AVD) for testing.
    """
    await avd.adb.shell("pm clear com.android.chrome")
    # Put purple.html on the device.
    await avd.adb.shell(f"mkdir -p {purple_path}")
    await avd.adb.shell(f'echo "{purple_html}" > {purple_path}/purple.html')

    await avd.adb.shell(
        "pm grant com.android.chrome android.permission.POST_NOTIFICATIONS"
    )
    api = await avd.api_level()
    if api < 33:
        PERMISSION = "READ_EXTERNAL_STORAGE"
    else:
        PERMISSION = "READ_MEDIA_IMAGES"
    await avd.adb.shell(
        f"pm grant com.android.chrome android.permission.{PERMISSION}"
    )

    # Configure to skip welcome page
    await avd.adb.shell(
        'echo "chrome --disable-fre --no-default-browser-check --no-first-run --skip_first_run_ui" > /data/local/tmp/chrome-command-line'
    )
    await avd.adb.shell("am set-debug-app --persistent com.android.chrome")

    await avd.adb.shell(
        f"am start -a android.intent.action.VIEW -d http://www.google.com -n {chrome_cmp}"
    )
    await avd.stop_activity(chrome_pkg)


async def request_page_in_chrome(avd):
    await prepare_chrome(avd)

    # SystemUI and launcher crash/ANR dialogs get in the way of screenshots, attempt to close them
    await avd.adb.shell(
        "am start -a android.intent.action.MAIN -c android.intent.category.HOME"
    )

    await avd.adb.shell(
        f"am start -S -a android.intent.action.VIEW -d 'file:///{purple_path}/purple.html' -t text/html -n {chrome_cmp}"
    )


@pytest.mark.graphics
@pytest.mark.xfail
@pytest.mark.async_timeout(1080)
async def test_launch_chrome_google(avd, get_screenshot):
    """
    This test launches Chrome on an Android device, opens a html snippet,
    captures a screenshot, and verifies that at least 40% of the image pixels are purple.
    """

    async def at_least_40_percent_of_image_is_purple():
        """
        Helper function to check if at least 40% of the image pixels are purple.

        Returns:
            bool: True if at least 40% of the image pixels are blue, False otherwise.
        """
        _, rgb_image = await get_screenshot(ImageFormat())
        rgb_image = rgb_image.convert("RGB")

        percent_purple = 40
        purple_count = 0

        # Iterate over each pixel in the image
        for x in range(rgb_image.width):
            for y in range(rgb_image.height):
                # Get the RGB values of the pixel at (x, y)
                r, g, b = rgb_image.getpixel((x, y))

                # Check if the pixel corresponds to the desired shade of purple
                if r > 245 and g < 10 and b > 245:
                    purple_count += 1
        return purple_count > (
            rgb_image.width * rgb_image.height * percent_purple / 100
        )

    saw_purple = False
    # Weird that the file access permissions are not granted on the first try.
    # But it is ok to retry since that is not the focus of this test.
    max_retries = 3
    for _ in range(0, max_retries):
        await request_page_in_chrome(avd)
        if await wait_until(at_least_40_percent_of_image_is_purple, timeout=20):
            saw_purple = True
            break

    assert saw_purple, f"Did not see a screenshot with 40% purple pixels"
    await avd.stop_activity(chrome_pkg)


@pytest.mark.sanity
@pytest.mark.graphics
@pytest.mark.screen_recorder
@pytest.mark.parametrize(
    "gpu_mode", ["auto", "host", "swiftshader_indirect", "angle_indirect", "swangle"]
)
async def test_page_loads_with_different_gpu_modes(emulator, gpu_mode, qrcode_png):
    """Verify AVD has no issues with loading web content with different gpu modes.

    Args:
        emulator (BaseEmulator): Fixture that gives access to the running emulator.
        gpu_mode (str): gpu mode.
        qrcode_png (Qrcode): Fixture that provides a PNG image with a pre-encoded QR code.

    Test Steps:
        1. Launch an AVD with the option "-gpu auto".
        2. Open the PNG image with the pre-encoded QR code in Chrome (Verify).
        3. Repeat the process with other gpu modes:
           - host, swiftshader_indirect, angle_indirect (Windows), swangle.

    Verification:
        Chrome should load the image without any graphic issues, observed by
        the decoding of the embedded QR code through a series of screenshots.
    """
    if gpu_mode == "angle_indirect" and pytest.system != "Windows":
        pytest.skip(f"gpu mode {gpu_mode} is only available on Windows.")

    logging.info(f"Launching the emulator with the gpu mode '{gpu_mode}'.")
    await emulator.launch(
        emulator.launch_flags + ["-no-snapshot-save", "-gpu", f"{gpu_mode}"]
    )
    await emulator.wait_for_boot()

    await prepare_chrome(emulator)
    logging.info(f"Opening file '{qrcode_png.path}' in Google Chrome ..")
    await emulator.start_activity(
        chrome_cmp,
        params=f"-d file://{qrcode_png.path}"
    )

    emulator_controller = EmulatorControllerStub(emulator.channel)
    logging.info(f"Attempting to decode the QR code ..")
    assert await decode_qrcodes(
        [qrcode_png.payload],
        emulator_controller=emulator_controller
    ), f"Unable to idetify the QR code payload for gpu '{gpu_mode}'."
