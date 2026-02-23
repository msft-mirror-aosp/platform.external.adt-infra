# Copyright 2026 The Android Open Source Project
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
import pytest
import logging
import datetime
from PIL import Image, ImageChops, ImageStat

logger = logging.getLogger(__name__)

async def run_camera_app(avd):
    """
    Helper to set accessibility display inversion.
    """
    logger.info("Running camera app")
    try:
        await avd.adb.shell("am start -a android.media.action.STILL_IMAGE_CAMERA")
    except Exception as e:
        logger.error("Failed running camera intent: %s", e)
        raise

@pytest.mark.graphics
@pytest.mark.async_timeout(300)
async def test_virtual_environment(avd, ad_ui, get_screenshot, fuzzy_image_compare):
    """
    Test that enables accessibility display inversion and verifies it works using fuzzy comparison.
    """
    # Wait for boot to settle
    logger.info("Waiting for 10 seconds for boot to settle...")
    await asyncio.sleep(10)

    # Launch camera
    logger.info("Launching camera...")
    await run_camera_app(avd)

    # Handle possible popups
    UI_WAIT_TIME = datetime.timedelta(seconds=10)
    logger.info("Clicking NEXT button...")
    ad_ui(text="NEXT").wait.click(UI_WAIT_TIME)
    logger.info("Clicking 'While using the app' button...")
    ad_ui(text="While using the app").wait.click(UI_WAIT_TIME)

    # Wait for launch animations and scene loading to complete,
    # this also tests the stability of camera rendering.
    await asyncio.sleep(15)

    # Take screenshot
    logger.info("Taking screenshot...")
    _, screen_captured_withcam = await get_screenshot()
    logger.info("Screenshot taken.")

    # Compare with golden screenshot image
    screen_camera_golden = Image.open("tests/camera/camera_golden.png").convert('RGB')
    similarity = fuzzy_image_compare(screen_captured_withcam, screen_camera_golden)
    logger.info(f"Similarity: {similarity}")
    assert similarity > 0.9, f"Image mismatch on camera capture. Score: {similarity}"

    logger.info("test_virtual_environment test completed.")
