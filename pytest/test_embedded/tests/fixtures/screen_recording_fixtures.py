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
"""Fixtures for recording the desktop, and image streams."""
import logging
import re
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator, Tuple

import pytest
from aemu.proto.emulator_controller_pb2 import ImageFormat, ImageTransport
from tests.test_utils import fmt_proto
from PIL import Image

from emu.images.convert import proto_to_pillow, save_image
from emu.recording.screen_recorder import AsyncScreenRecorder, AsyncVideoWriter


@pytest.fixture
def screen_recorder_file(request, log_directory):
    """
    Pytest fixture that provides a unique file path for storing screen recordings.

    The fixture creates a directory for screen recordings within the specified log directory
    and generates a unique file name based on the test name. It ensures that any existing
    file with the same name is deleted before returning the file path.

    Args:
        request: The pytest request object, providing information about the current test.
        log_directory (str | Path): The path to the directory for storing logs and screen recordings.

    Returns:
        Path: The path to the output video file for screen recording.
    """
    screenrecorder_dir = Path(log_directory) / "screenrecording"
    screenrecorder_dir.mkdir(parents=True, exist_ok=True)
    test_name = request.node.nodeid.split("::")[-1]
    file_name = re.sub(r"[\\/\{\}:]", "_", test_name)

    output_filename = screenrecorder_dir / f"{file_name}.mp4"
    if output_filename.exists():
        output_filename.unlink()

    return output_filename


@pytest.fixture
async def get_screenshot(emulator_controller, log_directory, request):
    """
    Pytest fixture that provides a function for capturing and saving screenshots from an emulator.

    The fixture sets up the necessary components for capturing a screenshot from the emulator,
    saving it to a file, and returning both the raw image data and a Pillow image object.

    Args:
        emulator_controller: The emulator controller object for interacting with the emulator.
        log_directory (str | Path): The path to the directory for storing logs and screenshots.
        request: The pytest request object, providing information about the current test.

    Returns:
        An async function that captures and saves a screenshot, returning the raw image and Pillow image.
    """

    async def do_get_screenshot(
        image_format: ImageFormat = None, screenshot_dir: str = ""
    ):
        """
        Captures a screenshot from the emulator and saves it to a file.

        Args:
            image_format: The format of the screenshot image. Defaults to 'ImageFormat()'.
            screenshot_dir: The directory to save the screenshot. Defaults to '<log_directory>/screenshots'.

        Returns:
            A tuple containing the raw screenshot image data and the Pillow image object.
        """
        image_format = image_format or ImageFormat()
        if screenshot_dir:
            screenshot_dir = Path(screenshot_dir)
        else:
            screenshot_dir = Path(log_directory) / "screenshots"
        img = await emulator_controller.getScreenshot(image_format)
        test_name = request.node.nodeid.split("::")[-1]
        file_name = re.sub(r"[\\/\{\}:]", "_", test_name)
        pillow_image = save_image(img, screenshot_dir.absolute(), file_name)
        return img, pillow_image

    return do_get_screenshot


class ScreenshotStreamManager:
    """
    Manages streaming screenshots from an emulator and optionally records them to a video file.

    This class provides a context manager interface for easy resource management.
    It establishes a screenshot stream from the emulator and can optionally record
    the stream to a video file.

    Args:
        emulator_controller: The emulator controller object for interacting with the emulator.
        image_format (ImageFormat): The desired image format for the screenshots.
        screen_recorder_file (str | Path): The path to the output video file (optional).

    Example:
        ```python
            async with ScreenshotStreamManager(
                emulator_controller, ImageFormat(width=360, height=640), "output.mp4"
            ) as manager:
                async for img in manager.stream_with_recording():
                  # Process the screenshot image (img)
                  ...
        ```
    """

    def __init__(self, emulator_controller, image_format, screen_recorder_file):
        """
        Initializes the ScreenshotStreamManager with the provided parameters.
        """
        self.emulator_controller = emulator_controller
        self.image_format = image_format
        self.screen_recorder_file = screen_recorder_file
        self.stream = None

    async def __aenter__(self):
        """
        Asynchronous context manager entry point. Establishes the screenshot stream.
        """
        self.stream = self.emulator_controller.streamScreenshot(self.image_format)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Asynchronous context manager exit point. Cancels the screenshot stream.
        """
        if self.stream:
            self.stream.cancel()

    def write_image(self, writer: AsyncVideoWriter, img):
        """
        Writes a screenshot image to the video writer.

        Args:
            writer (AsyncVideoWriter): The video writer object.
            img: The screenshot image to write.
        """
        try:
            writer.write_pillow(proto_to_pillow(img), realtime=True)
        except ValueError as e:
            logging.warning(
                "Ignoring first frame: can't decode frame: %s, format: %s, skipping due to: %s",
                img.seq,
                fmt_proto(img.format),
                e,
            )

    async def stream_with_recording(self) -> AsyncGenerator:
        """
        Streams screenshots from the emulator and optionally records them to a video file.

        Yields:
            Screenshot images as they become available.
        """
        try:
            # Get the first image
            first_img = None
            async for img in self.stream:
                first_img = img
                yield img
                break

            if not first_img:
                raise RuntimeError("Failed to get first screenshot")

            screen_size = (first_img.format.width, first_img.format.height)
            with AsyncVideoWriter(
                self.screen_recorder_file, "mp4v", 60, screen_size
            ) as writer:
                self.write_image(writer, first_img)
                async for img in self.stream:
                    self.write_image(writer, img)
                    yield img

        except Exception as e:
            logging.error("Error in screenshot stream: %s", e)
            raise


@pytest.fixture
async def stream_screenshot(emulator_controller, screen_recorder_file):
    """
    Pytest fixture that provides a function for streaming screenshots from an emulator.

    The fixture sets up the necessary components for streaming screenshots and
    optionally recording them to a video file.

    Args:
        emulator_controller: The emulator controller object for interacting with the emulator (fixture).
        screen_recorder_file (str | Path): The path to the output video file (fixture).

    Returns:
        An async function that takes an ImageFormat argument and streams screenshots.
    """

    async def streaming_img_call(image_format: ImageFormat):
        async with ScreenshotStreamManager(
            emulator_controller, image_format, screen_recorder_file
        ) as manager:
            async for img in manager.stream_with_recording():
                yield img

    return streaming_img_call


@pytest.fixture(autouse=True)
async def screen_recorder(screen_recorder_file):
    """
    Pytest fixture that provides an initialized and running AsyncScreenRecorder.

    The recorder will capture screen 0 (the default display). Ensure your
    system configuration and user permissions allow for screen recording.

    This fixture simplifies the process of setting up and tearing down an
    AsyncScreenRecorder instance for testing purposes. It creates an instance
    of the AsyncScreenRecorder, starts the recording process, yields the recorder
    to the test function, and automatically stops the recording after the test
    completes.


    Args:
        screen_recorder_file (Path): The path to the output video file,
                                      provided by the `screen_recorder_file` fixture.

    Yields:
        AsyncScreenRecorder: An initialized and running instance of AsyncScreenRecorder.
    """
    recorder = AsyncScreenRecorder(output_filename=screen_recorder_file)
    await recorder.start_recording()
    yield recorder
    await recorder.stop_recording()
