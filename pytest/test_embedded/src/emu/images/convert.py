# Copyright 2023 - The Android Open Source Project
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
import io
import logging
import time

from aemu.proto.emulator_controller_pb2 import Image, ImageFormat
from PIL import Image as PillowImage


def proto_to_pillow(image: Image) -> PillowImage:
    """Converts an emulator protobuf image to a Pillow Image

    Args:
        image (Image): An image obtained from the screenShot api.

    Returns:
        PillowImage: A Pillow Image
    """
    EMU_TO_PIL_IMAGE_FORMATS = {
        ImageFormat.RGB888: "RGB",
        ImageFormat.RGBA8888: "RGBA",
        ImageFormat.PNG: "PNG",
    }

    if image.format.format == ImageFormat.PNG:
        return PillowImage.open(io.BytesIO(image.image))
    return PillowImage.frombytes(
        EMU_TO_PIL_IMAGE_FORMATS[image.format.format],
        (image.format.width, image.format.height),
        image.image,
    )


def save_image(received_image, image_dir, test_name):
    """Saves an image to a file in the specified directory.

    Args:
        received_image (Image): The image to save.
        image_dir (Path): The directory where the image should be saved.
        test_name (str): The name of the test that the image was captured from.

    Returns:
        PillowImage: The saved image if successful, None otherwise.
    """
    try:
        img = proto_to_pillow(received_image)
        epoch_time_ms = int(time.time() * 1000)
        if not image_dir.exists():
            image_dir.mkdir(parents=True)
        image_file = image_dir / f"screenshot-{test_name}-{epoch_time_ms}.png"
        logging.info(
            "Received %sx%s, saving screenshot to %s",
            img.width,
            img.height,
            image_file.absolute(),
        )
        img.save(image_file, "PNG")
        img.filename = image_file  # needed, otherwise this field will be empty
        return img
    except Exception as e:
        logging.warning("An error occurred while saving the image: %s", str(e))
        return None
