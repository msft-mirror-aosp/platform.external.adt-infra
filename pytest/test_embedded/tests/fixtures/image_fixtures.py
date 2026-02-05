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
import pytest
from PIL import ImageChops, ImageStat, Image
import logging
import math

@pytest.fixture
def fuzzy_image_compare():
    """
    Compares two images and returns a similarity score between 0.0 and 1.0.
    1.0 means identical, 0.0 means completely different.
    """
    def compare(img1_data, img2_data):
        # Handle cases where input might be raw bytes or PIL Image objects
        if isinstance(img1_data, bytes):
            # Assuming raw bytes might need conversion if not already PIL, 
            # but usually get_screenshot returns (raw, PIL). 
            # If we get raw bytes, we might need more info to convert, 
            # so we expect PIL images here or tuples from get_screenshot.
            pass

        # If tuple from get_screenshot, extract PIL image (index 1)
        if isinstance(img1_data, tuple):
            img1 = img1_data[1]
        else:
            img1 = img1_data

        if isinstance(img2_data, tuple):
            img2 = img2_data[1]
        else:
            img2 = img2_data

        # Ensure both are PIL Images
        if not isinstance(img1, Image.Image) or not isinstance(img2, Image.Image):
            logging.error("fuzzy_image_compare: Inputs must be PIL Images or (raw, PIL) tuples.")
            return 0.0

        if img1.size != img2.size:
            logging.warning(f"fuzzy_image_compare: Image sizes differ: {img1.size} vs {img2.size}")
            return 0.0

        if img1.mode != img2.mode:
            img2 = img2.convert(img1.mode)

        # Calculate difference
        diff = ImageChops.difference(img1, img2)
        stat = ImageStat.Stat(diff)

        # Calculate RMS (Root Mean Square) difference
        # sum of squares / num_pixels / num_channels
        # We can approximate similarity based on RMS.
        # Max possible RMS is sqrt(255^2) = 255.

        sum_of_squares = sum(stat.sum2)
        num_pixels = img1.width * img1.height * len(img1.getbands())

        rms = math.sqrt(sum_of_squares / num_pixels)

        # Normalize to 0.0 - 1.0 similarity
        # 0 diff -> 1.0 similarity
        # 255 diff -> 0.0 similarity
        similarity = 1.0 - (rms / 255.0)

        logging.info(f"fuzzy_image_compare: RMS={rms}, Similarity={similarity}")
        return max(0.0, min(1.0, similarity))

    return compare
