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
import logging
import os
import queue
import threading
import time
from pathlib import Path

import cv2
import numpy as np
import pytest
from mss import mss
from PIL import Image as PillowImage


class AsyncVideoWriter:
    """
    Asynchronously writes video frames to a file using a separate thread and a queue.

    This class provides a context manager interface for easy resource management.
    Frames are queued for writing and processed in the background to avoid blocking
    the main thread.

    Args:
        filename (str | Path): The path to the output video file.
        fourcc (str): A four-character code specifying the video codec (e.g., 'mp4v').
        fps (int): The frames per second of the output video.
        frameSize (tuple(int, int)): The width and height of the video frames.
        queue_size (int, optional): The maximum number of frames to hold in the queue.
                                    Defaults to 100.

    Example:
        ```python
        with AsyncVideoWriter('output.mp4', 'mp4v', 30, (640, 480)) as writer:
            for frame in frames:
                writer.write(frame)
        ```
    """

    def __init__(
        self,
        filename: str | Path,
        fourcc: str,
        fps: int,
        frameSize: (int, int),
        queue_size: int = 100,
    ):
        """Initializes the AsyncVideoWriter with file details and queue settings."""
        self.filename = str(filename)
        self.fourcc = cv2.VideoWriter_fourcc(*fourcc)
        self.fps = fps
        self.frameSize = frameSize
        self.queue = queue.Queue(maxsize=queue_size)
        self._writer = None
        self._thread = None
        self._stop_event = threading.Event()
        self._last_write_time = time.time()

    def _write_frames(self):
        """Worker thread function to continuously write frames from the queue."""
        while not self._stop_event.is_set():
            try:
                frame = self.queue.get(timeout=0.5)
                self._writer.write(frame)
            except queue.Empty:
                continue

    def __enter__(self):
        """
        Context manager entry point.

        Opens the video writer and starts the worker thread.
        """
        self._writer = cv2.VideoWriter(
            self.filename, self.fourcc, self.fps, self.frameSize
        )
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._write_frames)
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager exit point.

        Stops the worker thread, writes any remaining frames, and releases the video writer.
        """
        self._stop_event.set()
        self._thread.join()

        while not self.queue.empty():
            frame = self.queue.get()
            self._writer.write(frame)

        if self._writer:
            self._writer.release()

    def _queue_frame(self, frame):
        """Adds a frame to the writing queue."""
        try:
            self.queue.put_nowait(frame)
        except queue.Full:
            logging.error("Frame queue is full for %s, dropping frame.", self.filename)

    def write(self, frame, realtime=False):
        """
        Adds a frame to the queue for asynchronous writing.

        Args:
            frame: The video frame to write.
            realtime (bool, optional): Whether to attempt real-time frame rate.
                                       Defaults to False.
        """
        if not realtime:
            return self._queue_frame(frame)

        frame_duration = 1.0 / self.fps
        current_time = time.time()
        elapsed_time = current_time - self._last_write_time
        expected_frames = elapsed_time / frame_duration

        if expected_frames >= 1:
            frames_to_write = int(expected_frames)
            for _ in range(frames_to_write):
                self._queue_frame(frame)
            self._last_write_time = current_time
        else:
            logging.info("Frame dropped to maintain FPS for %s", self.filename)

    def write_pillow(self, image: PillowImage, realtime=False):
        """
        Converts a Pillow Image to OpenCV format and adds it to the queue.

        Args:
            image (PillowImage): The PIL Image to write.
            realtime (bool, optional): Whether to attempt real-time frame rate.
                                       Defaults to False.
        """
        if (image.width, image.height) != self.frameSize:
            image = image.resize(self.frameSize, PillowImage.LANCZOS)

        if image.mode == "RGB":
            frame = np.array(image)
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        elif image.mode == "RGBA":
            frame = np.array(image)
            frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2RGB)
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        elif image.format == "PNG":
            image = image.convert("RGB")
            frame = np.array(image)
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        else:
            raise ValueError(f"Unsupported image mode: {image.mode}")

        self.write(frame, realtime)


class AsyncScreenRecorder:
    """
    Asynchronously records the screen using OpenCV and mss.

    This class provides a way to record the screen activity asynchronously
    using the `mss` library for screen capture and `OpenCV` for video encoding.

    Attributes:
        output_filename (Path|str): The path to the output video file.
                                    Defaults to "screen_recording.mp4".
        fps (int): The frames per second for the recording.
                     Defaults to 30
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

        Note: The higher the fps, the more cpu work and higher chance of missed
        frames.

        Args:
            output_filename (Path|str): The path to the output video file.
            fps (int): The frames per second for the recording.
        """
        self.output_filename = Path(output_filename)
        self.fps = fps
        self.recording = False
        self.task = None
        self.logger = logging.getLogger(name="rec")

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

        with mss() as sct:
            with AsyncVideoWriter(
                str(self.output_filename), "mp4v", self.fps, screen_size
            ) as out:
                frame_duration = 1 / self.fps
                next_frame_time = time.monotonic()  # Initialize next frame time
                frames_behind = 0  # Track how many frames behind we are
                frame = 0

                while self.recording:
                    start_time = time.monotonic()

                    # Capture screen and process frame
                    # This is not 0 cost time wise, and could be
                    # an expensive operation, this can cause drift
                    # which could cause us to fall behind in frames.
                    img = np.array(sct.grab(sct.monitors[0]))
                    img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                    out.write(img)
                    frame += 1
                    write_speed = time.monotonic() - start_time

                    # Increment next frame time, this is the time_stamp we should
                    # be writing the next frame.
                    next_frame_time += frame_duration

                    # Calculate time spent and drift
                    time_spent = time.monotonic() - start_time
                    sleep_time = next_frame_time - time.monotonic()

                    # Check if we're behind schedule
                    if sleep_time < 0:
                        # Calculate how many frames we're behind, we will basically
                        # rewrite the same frame to catch up and make sure our codec
                        # receives the proper fps.
                        frames_behind += int(abs(sleep_time) // frame_duration)

                    # Catch up by writing the same frame until we're back on track
                    while frames_behind > 0:
                        # Write the same frame to catch up, we assume this is fast, and will not
                        # make us fall behind even more.
                        out.write(img)
                        frame += 1

                        next_frame_time += frame_duration
                        frames_behind -= 1

                    # Calculate remaining sleep time after catching up
                    sleep_time = next_frame_time - time.monotonic()

                    # sleep_time in theory can be negative, if we fell behind a lot,
                    # and catching up took to much time. Since we are doing co-operative threading
                    # we should give up control to another task.
                    sleep_time = max(0, sleep_time)
                    # Note that we can sleep longer than sleep_time, which
                    # can cause us to drift.
                    self.logger.debug("Sleeping: %d", sleep_time)
                    await asyncio.sleep(sleep_time)
