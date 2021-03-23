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
import mmap
import os
import time

import pytest
from aemu.proto.emulator_controller_pb2 import ImageFormat, ImageTransport

from tests.benchmark_event_fixtures import benchmark_stat
from tests.test_utils import StreamingCall


def read_pixel(width, height, pack, arr):
    # Reads a pixel
    return arr[(width - 1) * (height - 1) * pack]


@pytest.mark.e2e
@pytest.mark.timeout(timeout=10, func_only=True)
@pytest.mark.parametrize(
    "fmt,channel",
    [
        (ImageFormat.RGBA8888, ImageTransport.TRANSPORT_CHANNEL_UNSPECIFIED),
        (ImageFormat.RGB888, ImageTransport.TRANSPORT_CHANNEL_UNSPECIFIED),
        (ImageFormat.RGBA8888, ImageTransport.MMAP),
        (ImageFormat.RGB888, ImageTransport.MMAP),
    ],
)
def test_stream_screenshot_receives_frames(animation_app, tmpdir, fmt, channel):
    """Test that streaming screenshot receives a series of frames."""
    path = str(tmpdir.realpath())  # Needed for py2 compatibility
    tmp_file = os.path.join(path, "image_file.img")
    with open(tmp_file, "wb") as out:
        out.truncate(360 * 640 * 4 + 1024)

    emu = pytest.emulator.get_emulator_controller()
    stream = emu.streamScreenshot(
        ImageFormat(
            width=360,
            height=640,
            format=fmt,
            transport=ImageTransport(channel=channel, handle="file://" + tmp_file),
        )
    )
    count = 0
    dropped = 0
    seq = None

    # We enter some text, which should bring up the search bar.
    with StreamingCall(stream) as stream:
        # We should get a continous sequence of frames..
        for img in iter(stream.get, None):
            if seq and seq + 1 < img.seq:
                dropped += img.seq - seq + 1
            seq = img.seq

            count += 1
            if count > 10:
                break

    logging.warning("Received %d frames and dropped %d frames", count, dropped)
    assert True


@pytest.mark.perf
@pytest.mark.timeout(timeout=300, func_only=True)
@pytest.mark.benchmark(group="animation")
@pytest.mark.parametrize(
    "w,h",
    [(270, 480), (360, 640), (720, 1280), (810, 1440), (1080, 1920), (1440, 2880)],
)
def test_stream_screenshot_perf(animation_app, benchmark_stat, pytestconfig, w, h):
    """Test the performance of streaming frames."""
    # This test can only run if we launched the emulator
    emu = pytest.emulator.get_emulator_controller()
    stream = emu.streamScreenshot(
        ImageFormat(width=w, height=h, format=ImageFormat.RGB888)
    )
    count = 0
    dropped = 0
    timeout = pytestconfig.getoption("stream_test_time") + time.time()

    seq = None
    with StreamingCall(stream) as stream:
        # We should get a continous sequence of frames..
        start_time = time.time()
        for img in iter(stream.get, None):
            receive_time = time.time()
            benchmark_stat.update(receive_time - start_time)

            if seq and seq + 1 < img.seq:
                dropped += img.seq - seq + 1
            seq = img.seq
            count += 1
            if time.time() > timeout:
                break
            start_time = receive_time

    logging.warning("Received %d frames and dropped %d frames", count, dropped)
    assert True


@pytest.mark.perf
@pytest.mark.timeout(timeout=300, func_only=True)
@pytest.mark.benchmark(group="animation")
@pytest.mark.parametrize(
    "w,h",
    [(270, 480), (360, 640), (720, 1280), (810, 1440), (1080, 1920), (1440, 2880)],
)
def test_stream_screenshot_perf_mmap(
    animation_app, benchmark_stat, pytestconfig, tmpdir, w, h
):
    """Test the performance of streaming frames."""
    path = str(tmpdir.realpath())  # Needed for py2 compatibility
    tmp_file = os.path.join(path, "image_file.img")
    with open(tmp_file, "wb") as out:
        out.truncate(w * h * 4 + 1024)

    emu = pytest.emulator.get_emulator_controller()
    stream = emu.streamScreenshot(
        ImageFormat(
            width=w,
            height=h,
            format=ImageFormat.RGB888,
            transport=ImageTransport(
                channel=ImageTransport.MMAP, handle="file://" + tmp_file
            ),
        )
    )
    count = 0
    dropped = 0
    timeout = pytestconfig.getoption("stream_test_time") + time.time()

    seq = None
    with open(tmp_file, "r+b") as f:
        # memory-map the file, size 0 means whole file
        mm = mmap.mmap(f.fileno(), 0)
        with StreamingCall(stream) as stream:
            # We should get a continous sequence of frames..
            start_time = time.time()
            for img in iter(stream.get, None):
                # Force a read, as the gRPC call reads all the bytes as well.
                mm.seek(0)
                img_bytes = mm.read()
                receive_time = time.time()
                benchmark_stat.update(receive_time - start_time)

                if seq and seq + 1 < img.seq:
                    dropped += img.seq - seq + 1
                seq = img.seq
                count += 1
                if time.time() > timeout:
                    break
                start_time = receive_time

    logging.warning("Received %d frames and dropped %d frames", count, dropped)
    assert True


@pytest.mark.e2e
@pytest.mark.timeout(timeout=10, func_only=True)
@pytest.mark.parametrize(
    "fmt",
    [ImageFormat.RGBA8888, ImageFormat.RGB888],
)
def test_screenshot_bytes_size(fmt):
    """Test that getScreenshot returns the proper number of bytes."""
    emu = pytest.emulator.get_emulator_controller()
    image = emu.getScreenshot(
        ImageFormat(
            width=360,
            height=640,
            format=fmt,
        )
    )
    pixelSize = 4 if fmt == ImageFormat.RGBA8888 else 3
    assert image.format.width * image.format.height * pixelSize == len(image.image)
