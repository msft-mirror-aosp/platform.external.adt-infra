# Copyright 2023 The Android Open Source Project
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
from emu.recording.screen_recorder import AsyncScreenRecorder
from emu.recording.screen_grab import ScreenGrabStrategyFactory


@pytest.fixture
async def screen_recorder_strategy(screen_recorder_file, request):
    recorder = AsyncScreenRecorder(
        output_filename=screen_recorder_file, strategy=request.param
    )
    await recorder.start_recording()
    yield recorder
    await recorder.stop_recording()


@pytest.mark.parametrize(
    "screen_recorder_strategy", ["mss", "pil", "pyscreeze", None], indirect=True
)
async def test_screenrecorder_fixture(screen_recorder_strategy):
    logging.info("Hello from the screen recorder test, i'm going to take a nap!")
    await asyncio.sleep(5)
    logging.info("Yawn! I'm back. You should have a recording")
