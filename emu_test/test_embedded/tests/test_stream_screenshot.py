# Copyright 2020 The Android Open Source Project
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
import logging
import time

import pytest

from aemu.proto.emulator_controller_pb2 import ImageFormat
from tests.benchmark_event_fixtures import benchmark_stat
from tests.test_utils import StreamingCall


@pytest.mark.e2e
@pytest.mark.timeout(timeout=10, func_only=True)
@pytest.mark.parametrize("w,h", [(270, 480), (360, 640), (1080, 1920)])
def test_stream_screenshot_receives_frames(animation_app, w, h):
    """Test that streaming screenshot receives a series of frames.
    """
    emu = pytest.emulator.get_emulator_controller()
    stream = emu.streamScreenshot(ImageFormat(width=w, height=h, format=ImageFormat.RGBA8888))
    count = 0
    dropped = 0
    seq = None

    # We enter some text, which should bring up the search bar.
    with StreamingCall(stream) as stream:
        # We should get a continous sequence of frames..
        for img in iter(stream.get, None):
            if seq and seq + 1 < img.seq:
                dropped += (img.seq - seq + 1)
            seq = img.seq

            count += 1
            if count > 10:
                break

    logging.warning("Received %d frames and dropped %d frames", count, dropped)
    assert True


@pytest.mark.perf
@pytest.mark.timeout(timeout=30, func_only=True)
@pytest.mark.benchmark(group="animation")
@pytest.mark.parametrize(
    "w,h", [(270, 480), (360, 640), (720, 1280), (810, 1440), (1080, 1920)]
)
def test_stream_screenshot_perf(animation_app, benchmark_stat, w, h):
    """Test the performance of streaming frames.

    """
    # This test can only run if we launched the emulator
    emu = pytest.emulator.get_emulator_controller()
    stream = emu.streamScreenshot(ImageFormat(width=w, height=h, format=ImageFormat.RGBA8888))
    count = 0
    dropped = 0

    seq = None
    # We enter some text, which should bring up the search bar.
    with StreamingCall(stream) as stream:
        # We should get a continous sequence of frames..
        start_time = time.time()
        for img in iter(stream.get, None):
            receive_time = time.time()
            benchmark_stat.update(receive_time - start_time)\

            if seq and seq + 1 < img.seq:
                dropped += (img.seq - seq + 1)
            seq = img.seq
            count += 1
            if count > 120:
                break
            start_time = receive_time

    logging.warning("Received %d frames and dropped %d frames", count, dropped)
    assert True
