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
import asyncio
import mmap
import os
import time

import pytest
from aemu.proto.emulator_controller_pb2 import ImageFormat, ImageTransport
from google.protobuf import empty_pb2
from grpc import RpcError, StatusCode


def read_pixel(width, height, pack, arr):
    # Reads a pixel
    return arr[(width - 1) * (height - 1) * pack]


@pytest.mark.e2e
@pytest.mark.graphics
@pytest.mark.embedded
@pytest.mark.skipos(
    "win", "reason: b/305252175 - error at setup. Only the parameter [2-1] fails."
)
@pytest.mark.flaky(reruns=2, reruns_delay=2)
@pytest.mark.timeout_win(timeout=60)
@pytest.mark.parametrize(
    "fmt,channel",
    [
        (ImageFormat.RGBA8888, ImageTransport.TRANSPORT_CHANNEL_UNSPECIFIED),
        (ImageFormat.RGB888, ImageTransport.TRANSPORT_CHANNEL_UNSPECIFIED),
        (ImageFormat.RGBA8888, ImageTransport.MMAP),
        (ImageFormat.RGB888, ImageTransport.MMAP),
    ],
)
async def test_stream_screenshot_receives_frames(
    animation_app, emulator_controller, tmpdir, fmt, channel
):
    """Test that streaming screenshot receives a series of frames."""
    path = str(tmpdir.realpath())  # Needed for py2 compatibility
    tmp_file = os.path.join(path, "image_file.img")
    with open(tmp_file, "wb") as out:
        out.truncate(360 * 640 * 4 + 1024)

    stream = emulator_controller.streamScreenshot(
        ImageFormat(
            width=360,
            height=640,
            format=fmt,
            transport=ImageTransport(channel=channel, handle="file://" + tmp_file),
        ),
        timeout=5,
    )

    async def count_10_images():
        count = 0
        async for img in stream:
            count += 1
            if count >= 10:
                return

    await asyncio.wait_for(count_10_images(), timeout=4)


@pytest.mark.perf
@pytest.mark.benchmark(group="animation")
@pytest.mark.parametrize(
    "w,h",
    [(270, 480), (360, 640), (720, 1280), (810, 1440), (1080, 1920), (1440, 2880)],
)
async def test_stream_screenshot_perf(
    animation_app, emulator_controller, benchmark_stat, pytestconfig, w, h
):
    """Test the performance of streaming frames."""
    stream = emulator_controller.streamScreenshot(
        ImageFormat(width=w, height=h, format=ImageFormat.RGB888),
    )

    async def frame_counter():
        start_time = time.time()
        async for img in stream:
            receive_time = time.time()
            benchmark_stat.update(receive_time - start_time)
            start_time = receive_time

    timeout = pytestconfig.getoption("stream_test_time")
    with pytest.raises(asyncio.exceptions.TimeoutError):
        await asyncio.wait_for(frame_counter(), timeout=timeout)


@pytest.mark.perf
@pytest.mark.benchmark(group="animation")
@pytest.mark.parametrize(
    "w,h",
    [(270, 480), (360, 640), (720, 1280), (810, 1440), (1080, 1920), (1440, 2880)],
)
async def test_stream_screenshot_perf_mmap(
    emulator_controller, animation_app, benchmark_stat, pytestconfig, tmpdir, w, h
):
    """Test the performance of streaming frames."""
    path = str(tmpdir.realpath())  # Needed for py2 compatibility
    tmp_file = os.path.join(path, "image_file.img")
    with open(tmp_file, "wb") as out:
        out.truncate(w * h * 4 + 1024)

    stream = emulator_controller.streamScreenshot(
        ImageFormat(
            width=w,
            height=h,
            format=ImageFormat.RGB888,
            transport=ImageTransport(
                channel=ImageTransport.MMAP, handle="file://" + tmp_file
            ),
        )
    )

    async def frame_counter_mmap():
        with open(tmp_file, "r+b") as f:
            # memory-map the file, size 0 means whole file
            mm = mmap.mmap(f.fileno(), 0)

            start_time = time.time()
            async for img in stream:
                mm.seek(0)  # Let's do something with the bytes..
                _ = mm.read()

                receive_time = time.time()
                benchmark_stat.update(receive_time - start_time)
                start_time = receive_time

    timeout = pytestconfig.getoption("stream_test_time")
    with pytest.raises(asyncio.exceptions.TimeoutError):
        await asyncio.wait_for(frame_counter_mmap(), timeout=timeout)


@pytest.mark.e2e
@pytest.mark.graphics
@pytest.mark.embedded
@pytest.mark.skipos("win", "reason: b/305254892 FAILURES | b/305255695 ERRORS at setup")
@pytest.mark.parametrize(
    "fmt",
    [ImageFormat.RGBA8888, ImageFormat.RGB888],
)
async def test_screenshot_bytes_size(emulator_controller, fmt):
    """Test that getScreenshot returns the proper number of bytes."""
    image = await emulator_controller.getScreenshot(
        ImageFormat(
            width=360,
            height=640,
            format=fmt,
        )
    )
    pixelSize = 4 if fmt == ImageFormat.RGBA8888 else 3
    assert image.format.width * image.format.height * pixelSize == len(image.image)


@pytest.mark.graphics
@pytest.mark.embedded
@pytest.mark.skipos("win", "reason: b/305258769 - error at setup.")
async def test_stream_screenshot_should_fail_if_does_not_exist(
    at_home,
    emulator_controller,
    animation_app,
):
    """Verifies b/206033509 streamScreenshot/getScreenshot should fail with INVALID_ARGUMENT if the display doesn't exist"""
    _EMPTY_ = empty_pb2.Empty()
    cfg = await emulator_controller.getDisplayConfigurations(_EMPTY_)
    non_existing_display = len(cfg.displays) + 1

    with pytest.raises(RpcError) as e:
        stream = emulator_controller.streamScreenshot(
            ImageFormat(display=non_existing_display)
        )
        async for img in stream:
            assert False, "We should never have received an image!"

    assert e.value.code() == StatusCode.INVALID_ARGUMENT
    assert e.value.details() == "Invalid display: {}".format(non_existing_display)
