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
import asyncio
import logging

import pytest
from aemu.proto.emulator_controller_pb2 import ImageFormat

from emu.timing import eventually


@pytest.mark.graphics
@pytest.mark.flaky
async def test_android_app_dialog_has_dimmed_background(
    avd, get_screenshot, log_adb_interactions
):
    """
    Test for b/315308358.

    This test launches com.google.emu.AnimateBox/.DialogDimActivity on an Android device, which has
    a blank blue (#0000ff) surface, with a app Dialog with no content over it. If dialog dimming
    works, then most of the pixels will have a darker shade of blue.

    Note: We need to keep the percentage of blue we check to not too high (60% should be okay),
    because of random system dialogs that can popup (e.g. Bluetooth keeps stopping).
    """

    async def get_blue_pixel_percent(min_blue, max_blue):
        """Helper function to get the percentage of blue pixels that meet the criteria
        `min_blue <= x <= max_blue`.

        Args:
            min_blue (int): the minimum blue value. Must be between 0 and 255.
            max_blue (int): the maximum blue value. Must be between 0 and 255.

        Returns:
            float: The percentage (0.0 to 1.0) of blue pixels that meet the above criteria.
        """
        _, rgb_image = await get_screenshot(ImageFormat())
        rgb_image = rgb_image.convert("RGB")

        blue_count = 0
        # Iterate over each pixel in the image
        for x in range(rgb_image.width):
            for y in range(rgb_image.height):
                # Get the RGB values of the pixel at (x, y)
                r, g, b = rgb_image.getpixel((x, y))

                # Check if the pixel corresponds to the desired shade of blue
                if r == 0 and g == 0 and b >= min_blue and b <= max_blue:
                    blue_count += 1
        logging.info(
            "blue pixel percent=%f",
            float(blue_count) / (rgb_image.width * rgb_image.height),
        )
        return float(blue_count) / (rgb_image.width * rgb_image.height)

    # Start DialogDimActivity with no dialog showing.
    await avd.stop_activity("com.google.AnimateBox")
    await avd.start_activity(
        "com.google.AnimateBox/com.google.emu.DialogDimActivity",
        '--es "hideDialog" "true"',
    )
    # Give the system some time to start the activity
    await asyncio.sleep(5)

    # Without the dialog, most of the display should be blue (>= 60%).
    async def at_least_60percent_blue():
        blue_percentage = await get_blue_pixel_percent(240, 255)
        return blue_percentage >= 0.6

    passed = await eventually(at_least_60percent_blue, timeout=5)
    assert passed, "Did not see a screenshot with at least 60% blue pixels"

    # Start DialogDimActivity with the dialog showing.
    await avd.stop_activity("com.google.AnimateBox")
    await avd.start_activity("com.google.AnimateBox/com.google.emu.DialogDimActivity")
    # Give the system some time to start the activity
    await asyncio.sleep(5)

    # With the dialog, the blue will now become a darker shade.
    async def at_least_60percent_dark_blue():
        dark_blue_percentage = await get_blue_pixel_percent(20, 100)
        return dark_blue_percentage >= 0.6

    passed = await eventually(at_least_60percent_dark_blue, timeout=5)
    assert passed, "Did not see a screenshot with at most 60% dark blue pixels"
