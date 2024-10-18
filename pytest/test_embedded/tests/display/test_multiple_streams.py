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
import asyncio
import logging

import pytest
from aemu.proto.emulator_controller_pb2 import ImageFormat


@pytest.mark.embedded
@pytest.mark.async_timeout(40)
async def test_multiple_streams_do_not_block(animation_app, emulator_controller):
    """Tests that the streamScreenshot does not block when multiple streams are
    requested.

    This simulates b/312677259 where the embedded emulator issues a resize, which will
    result in multiple callbacks being registered inside the emulator which used
    to deadlock due to incorrect listener registration.

    The result is that when the deadlock happens, only 1 frame will be delivered.
    If the bug is present in the emulator this test will timeout, as no frames will be
    delivered.
    """

    # Note that we deliver 60 fps, so this should be very fast.
    async def async_stream_10_images(size):
        w = 360 + size * 10
        h = 640 + size * 10
        stream = emulator_controller.streamScreenshot(
            ImageFormat(
                width=w,
                height=h,
                format=ImageFormat.RGB888,
            ),
            timeout=5,
        )

        async def count_10_images():
            count = 0
            # Only 1 frame will be delivered in case of a deadlock.
            async for img in stream:
                count += 1
                if count >= 10:
                    logging.info("Received %d images: %sx%s", count, w, h)
                    return

        await asyncio.wait_for(count_10_images(), timeout=4)

    # Create a set of tasks for concurrent execution
    tasks = [asyncio.create_task(async_stream_10_images(size)) for size in range(40)]

    # Wait for all tasks to complete, this will timeout if we hit a deadlock
    # in the emulator
    await asyncio.gather(*tasks)
