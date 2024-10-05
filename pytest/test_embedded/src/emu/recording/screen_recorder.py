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
import asyncio
import os
import time
from pathlib import Path

import cv2
import numpy as np
import pytest
from mss import mss


class VideoWriter:
    """
    A wrapper around cv2.VideoWriter that supports the context manager protocol
    (with statement) for automatic resource management.
    """

    def __init__(self, filename, fourcc, fps, frameSize):
        self.filename = filename
        self.fourcc = fourcc
        self.fps = fps
        self.frameSize = frameSize
        self._writer = None

    def __enter__(self):
        self._writer = cv2.VideoWriter(
            self.filename, self.fourcc, self.fps, self.frameSize
        )
        return self._writer

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._writer:
            self._writer.release()


class AsyncScreenRecorder:
    """
    Asynchronously records the screen using OpenCV and mss.

    This class provides a way to record the screen activity asynchronously
    using the `mss` library for screen capture and `OpenCV` for video encoding.

    Attributes:
        output_filename (Path|str): The path to the output video file.
                                    Defaults to "screen_recording.mp4".
        fps (float): The frames per second for the recording.
                     Defaults to 30.0.
        recording (bool): Indicates whether the recording is currently active.
        task (asyncio.Task): The asyncio task responsible for the recording process.

    Example:
        ```python
        async def main():
            recorder = AsyncScreenRecorder(output_filename="my_recording.mp4")
            await recorder.start_recording()
            # ... perform actions to be recorded ...
            await recorder.stop_recording()

        asyncio.run(main())
        ```
    """

    def __init__(
        self, output_filename: Path | str = "screen_recording.mp4", fps: int = 30
    ):
        """
        Initializes the AsyncScreenRecorder.

        Args:
            output_filename (Path|str): The path to the output video file.
            fps (float): The frames per second for the recording.
        """
        self.output_filename = Path(output_filename)
        self.fps = fps
        self.recording = False
        self.task = None

    async def start_recording(self):
        """
        Starts the asynchronous screen recording process.
        """
        self.recording = True
        self.task = asyncio.create_task(self._record())

    async def stop_recording(self):
        """
        Stops the asynchronous screen recording process and waits for the
        recording task to complete.
        """
        self.recording = False
        if self.task:
            await self.task

    def screen_size_in_raw_pixels(self, monitor: int = 0) -> tuple[int, int]:
        """
        Gets the screen size in raw pixels for the specified monitor.

        Args:
            monitor (int): The monitor index (0-based). Defaults to 0
                           (primary monitor).

        Returns:
            tuple[int, int]: A tuple containing the width and height of the
                              screen in pixels.
        """
        with mss() as sct:
            screen = sct.monitors[monitor]
            img = sct.grab(screen)
            return img.size.width, img.size.height

    async def _record(self):
        """
        Internal asynchronous method that performs the screen recording.
        """
        screen_size = self.screen_size_in_raw_pixels()
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        with mss() as sct:
            with VideoWriter(
                str(self.output_filename), fourcc, self.fps, screen_size
            ) as out:
                while self.recording:
                    img = np.array(sct.grab(sct.monitors[0]))
                    img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                    out.write(img)
                    await asyncio.sleep(1 / self.fps)
