# Copyright 2021 The Android Open Source Project
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
"""
This contains a set of performance tests to determine how long it takes to deliver a new frame event to a different process.

Both tests will launch the animation app that should deliver frames at a constant rate, and will retrieve images as defined by
the stream_test_time propery
"""
import asyncio
import collections
import os
import struct
import time
from multiprocessing.shared_memory import SharedMemory

import pytest
from aemu.proto.emulator_controller_pb2 import ImageFormat, ImageTransport
from google.protobuf import empty_pb2


async def dimenisions(emulator_controller):
    response = await emulator_controller.getStatus(empty_pb2.Empty())
    cfg = response.hardwareConfig
    width, height = 0
    for entry in cfg.entry:
        if entry.key == "hw.lcd.width":
            width = int(entry.value)
        if entry.key == "hw.lcd.height":
            height = int(entry.value)
    return width, height


@pytest.mark.skipos("all", "b/203787882")
@pytest.mark.hostperf
@pytest.mark.benchmark(group="shared_mem")
async def test_mmap_grpc_perf(
    animation_app, emulator_controller, tmpdir, benchmark_stat, pytestconfig
):
    """Test time it takes to detect a frame change event using the gRPC + mmap


    Change events are delivered via gRPC, whereas the image data is a mmap file.
    This uses the emulators notification + image scaling mechanism.
    """
    # This test can only run if we launched the emulator
    width, height = await dimenisions(emulator_controller)
    path = str(tmpdir.realpath())  # Needed for py2 compatibility
    tmp_file = os.path.join(path, "image_file.img")
    with open(tmp_file, "wb") as out:
        out.truncate(width * height + 1024)

    stream = emulator_controller.streamScreenshot(
        ImageFormat(
            width=width,
            height=height,
            format=ImageFormat.RGBA8888,
            transport=ImageTransport(
                channel=ImageTransport.MMAP, handle="file://" + tmp_file
            ),
        ),
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


@pytest.mark.skipos("all", "b/203787882")
@pytest.mark.hostperf
@pytest.mark.benchmark(group="shared_mem")
async def test_mmap_webrtc_perf(
    avd,
    telnet,
    animation_app,
    tmpdir,
    benchmark_stat,
    pytestconfig,
    emulator_controller,
):
    """Test time it takes to detect a frame change event by polling the shared memory
    region setup by the webrtc screen recorder.

    This uses the emulator screen recorder infrastructure, and can not deliver scaled frames.

    Issues:
     - This only works on linux
     - Python seems to destroy the /dev/shm region.
    """
    await telnet.send("screenrecord webrtc start")
    # HACK: Give the emulator some time to create /dev/shm/videmulator####
    asyncio.sleep(0.5)
    width, height = await dimenisions(emulator_controller)

    video_info_struct_size = 24
    mem = SharedMemory(
        name="videmulator{}".format(avd.telnet.port),
        size=24 + (width * height * 4),
    )

    # Mimics struct VideoInfo from
    # android/android-emu/android/recording/video/VideoFrameSharer.h
    VideoInfo = collections.namedtuple(
        "VideoInfo", ["width", "height", "fps", "frameNumber", "tsUs"]
    )
    assert struct.calcsize("IIIIQ") == video_info_struct_size

    async def frame_counter():
        count = 0
        dropped = 0
        seq = None

        start_time = time.time()
        info = VideoInfo._make(
            struct.unpack("IIIIQ", mem.buf[0:video_info_struct_size])
        )
        receive_time = time.time()

        # Poll the shared memory region for the next frame number
        while seq and seq >= info.frameNumber and time.time() < timeout:
            info = VideoInfo._make(
                struct.unpack("IIIIQ", mem.buf[0:video_info_struct_size])
            )
            receive_time = time.time()

        benchmark_stat.update(receive_time - start_time)

        if seq != None and seq + 1 < info.frameNumber:
            dropped += info.frameNumber - seq + 1
        seq = info.frameNumber
        count += 1
        start_time = receive_time

    timeout = pytestconfig.getoption("stream_test_time")
    with pytest.raises(asyncio.exceptions.TimeoutError):
        await asyncio.wait_for(frame_counter(), timeout=timeout)

    await telnet.send("screenrecord webrtc stop")
    mem.close()
