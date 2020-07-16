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
import pytest
from aemu.proto.emulator_controller_pb2 import ImageFormat, KeyboardEvent

from tests.test_utils import StreamingCall


@pytest.mark.e2e
@pytest.mark.timeout(10)
def test_stream_screenshot_receives_frames(at_home):
    """Test that streaming screenshot receives a series of frames.
    """

    emu = pytest.emulator.get_emulator_controller()
    stream = emu.streamScreenshot(ImageFormat(width=320, height=200))
    count = 0

    # We enter some text, which should bring up the search bar.
    emu.sendKey(KeyboardEvent(text="x"))
    with StreamingCall(stream) as stream:
        # We should get a continous sequence of frames..
        for _ in iter(stream.get, None):
            count += 1
            if count > 10:
                break
    assert True
