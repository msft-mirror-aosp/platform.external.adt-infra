# Copyright 2022 The Android Open Source Project
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

import sys

import pytest

from aemu.proto.emulator_controller_pb2 import ClipData
from emu.timing import eventually

from google.protobuf import empty_pb2

_EMPTY_ = empty_pb2.Empty()


@pytest.mark.e2e
@pytest.mark.embedded
@pytest.mark.timeout(timeout=10, func_only=True)
@pytest.mark.parametrize(
    "clipboard_data",
    [
        "Hello There!",
        "How is Weather?",
    ],
)
@pytest.mark.skipif(sys.platform == "win32", reason="298027530")
def test_clipboard_data(emulator_controller, clipboard_data):
    """Send clipboard data to the emulator.

    Verify that the clipboard data received is same.

    Args:
      clipboard_data: clipboard data to be set.
    """
    set_clip_data = ClipData(text=clipboard_data)
    emulator_controller.setClipboard(set_clip_data)
    assert eventually(
        lambda: emulator_controller.getClipboard(_EMPTY_).text == clipboard_data
    ), "Clipboard data doesn't match"
