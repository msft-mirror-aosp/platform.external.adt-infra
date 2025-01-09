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
from emu.recording.screen_grab import ScreenGrabStrategyFactory
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
        self.logger = logging.getLogger(name="AsyncVideoWriter")

    def _write_frames(self):
        """Worker thread function to continuously write frames from the queue."""
        count = 0
        start_time = time.time()
        last_fps_log_time = start_time

        while not self._stop_event.is_set():
            try:
                frame = self.queue.get(timeout=0.5)
                self._writer.write(frame)
                count += 1

                current_time = time.time()
                elapsed_time_since_last_log = current_time - last_fps_log_time
                if elapsed_time_since_last_log >= 10:
                    elapsed_time = current_time - start_time
                    fps = count / elapsed_time if elapsed_time > 0 else 0
                    self.logger.info("Current FPS: %.2f", fps)
                    last_fps_log_time = current_time

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
            self.logger.info("Frame dropped to maintain FPS for %s", self.filename)

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
    Asynchronously records the screen using a configurable screen capture strategy.

    This class provides a way to record screen activity asynchronously using
    different screen capture methods (MSS, PIL ImageGrab, or PyScreeze) and OpenCV
    for video encoding.

    The strategy selection order is:
    1. MSS (fastest and most reliable) <-- really you want this one.
    2. PIL ImageGrab (good balance of speed and reliability)
    3. PyScreeze (most compatible but slower)

    Example:
        ```python
        async def main():
            # The recorder will automatically use the best available strategy
            recorder = AsyncScreenRecorder(output_filename="recording.mp4")

            # Or specify a particular strategy
            recorder = AsyncScreenRecorder(
                output_filename="recording.mp4",
                strategy='pyscreeze'
            )

            await recorder.start_recording()
            # ... perform actions to be recorded ...
            await recorder.stop_recording()

        asyncio.run(main())
        ```
    """

    def __init__(
        self,
        output_filename: Path | str = "screen_recording.mp4",
        fps: int = 5,
        strategy: str = None,
    ):
        """
        Initializes the AsyncScreenRecorder.

        Args:
            output_filename (Path|str): The path to the output video file.
            fps (int): The frames per second for the recording.
            strategy (Optional[ScreenGrabStrategy]): The screen capture strategy to use.
                                                   If None, the best available strategy
                                                   will be automatically selected.
        """
        self.output_filename = Path(output_filename)
        self.fps = fps
        self.recording = False
        self.task = None
        self.logger = logging.getLogger(name="rec")
        self.strategy = ScreenGrabStrategyFactory.create_strategy(strategy)

    async def start_recording(self):
        """Starts the asynchronous screen recording process."""
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
            monitor (int): The monitor index (0-based). Defaults to 0.

        Returns:
            tuple[int, int]: A tuple containing the width and height of the
                            screen in pixels.
        """
        return self.strategy.get_screen_size(monitor)

    async def _record(self):
        """Internal asynchronous method that performs the screen recording."""
        screen_size = self.screen_size_in_raw_pixels()

        with self.strategy as grabber, AsyncVideoWriter(
            str(self.output_filename), "mp4v", self.fps, screen_size
        ) as out:
            frame_duration = 1 / self.fps
            next_frame_time = time.monotonic()
            frames_behind = 0
            frame = 0

            while self.recording:
                start_time = time.monotonic()

                img = grabber.grab_screen()
                out.write(img)
                frame += 1
                write_speed = time.monotonic() - start_time

                next_frame_time += frame_duration
                time_spent = time.monotonic() - start_time
                sleep_time = next_frame_time - time.monotonic()

                if sleep_time < 0:
                    frames_behind += int(abs(sleep_time) // frame_duration)

                while frames_behind > 0:
                    out.write(img)
                    frame += 1
                    next_frame_time += frame_duration
                    frames_behind -= 1

                sleep_time = next_frame_time - time.monotonic()
                sleep_time = max(0, sleep_time)
                await asyncio.sleep(sleep_time)
