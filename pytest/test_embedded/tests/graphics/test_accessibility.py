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
import asyncio
import pytest
import logging

logger = logging.getLogger(__name__)

async def set_accessibility_display_inversion(avd, enabled: bool):
    """
    Helper to set accessibility display inversion.
    """
    val = "1" if enabled else "0"
    logger.info("Setting accessibility_display_inversion_enabled to %s", val)
    try:
        # Use --user 0 as 'current' might be problematic in some contexts
        # '0' is the system user/default user
        await avd.adb.shell(f"settings put --user 0 secure accessibility_display_inversion_enabled {val}")

        # Verify the setting was applied
        res = await avd.adb.shell("settings get --user 0 secure accessibility_display_inversion_enabled")
        logger.info("Read back accessibility_display_inversion_enabled: %s", res.strip())
    except Exception as e:
        logger.error("Failed to set/get setting: %s", e)
        raise

@pytest.mark.graphics
@pytest.mark.async_timeout(300)
async def test_accessibility_display_inversion(avd, get_screenshot, fuzzy_image_compare):
    """
    Test that enables accessibility display inversion and verifies it works using fuzzy comparison.
    """
    # Wait for boot to settle
    logger.info("Waiting 30 seconds for boot to settle...")
    await asyncio.sleep(30)

    # 1. Take initial screenshot (Screen A)
    logger.info("Taking initial screenshot (Screen A)...")
    _, screen_a = await get_screenshot()
    logger.info("Screen A taken.")

    # 2. Invert colors
    logger.info("Enabling display inversion...")
    await set_accessibility_display_inversion(avd, enabled=True)
    await asyncio.sleep(3)

    # 3. Take inverted screenshot (Screen B)
    logger.info("Taking inverted screenshot (Screen B)...")
    _, screen_b = await get_screenshot()
    logger.info("Screen B taken.")

    # 4. Invert again (restore) -> Disable!
    logger.info("Disabling display inversion (restoring)...")
    await set_accessibility_display_inversion(avd, enabled=False)
    await asyncio.sleep(3)

    # 5. Take restored screenshot (Screen C)
    logger.info("Taking restored screenshot (Screen C)...")
    _, screen_c = await get_screenshot()
    logger.info("Screen C taken.")

    # Comparable to Screen A vs Screen C (should be high similarity)
    # Using 0.95 as threshold for high similarity (allowing minor compression artifacts)
    similarity_a_c = fuzzy_image_compare(screen_a, screen_c)
    logger.info(f"Similarity A vs C (Restored): {similarity_a_c}")
    assert similarity_a_c > 0.95, f"Restored screen should be similar to original. Score: {similarity_a_c}"

    # Comparable to Screen A vs Screen B (should be low similarity)
    # Using 0.9 as threshold for distinct difference (inverted colors usually change most pixels)
    similarity_a_b = fuzzy_image_compare(screen_a, screen_b)
    logger.info(f"Similarity A vs B (Inverted): {similarity_a_b}")
    assert similarity_a_b < 0.9, f"Inverted screen should be different from original. Score: {similarity_a_b}"
