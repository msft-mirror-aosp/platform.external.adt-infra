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

import asyncio
import time

import grpc
import pytest
from aemu.discovery.header_manipulator_client_interceptor import (
    header_adder_interceptor,
)
from aemu.proto.emulator_controller_pb2 import ClipData
from aemu.proto.emulator_controller_pb2_grpc import EmulatorControllerStub
from google.protobuf import empty_pb2

from emu.timing import eventually

_EMPTY_ = empty_pb2.Empty()


def wait_for_with_timed_iterator(predicate, timed_iterator, timeout=5):
    end = time.time() + timeout
    for event in timed_iterator:
        if time.time() > end:
            return None
        if event == timed_iterator.get_sentinel():
            continue
        if predicate(event):
            return event
    return None


async def set_clip_data(emulator_controller, clipboard_data="Hello there!"):
    set_clip_data = ClipData(text=clipboard_data)
    await emulator_controller.setClipboard(set_clip_data)

    async def clipboard_matches_set_clip():
        status = await emulator_controller.getClipboard(_EMPTY_)
        return status.text == clipboard_data

    # We should actually have "Hello there!" on the clipboard.
    assert await eventually(clipboard_matches_set_clip), "Clipboard data doesn't match"


@pytest.mark.embedded
@pytest.mark.fast
@pytest.mark.skipos("win", "reason: b/303295516 - error at setup.")
@pytest.mark.parametrize(
    "clipboard_data",
    [
        "Hello There!",
        "How is Weather?",
    ],
)
async def test_clipboard_data(emulator_controller, clipboard_data):
    """Send clipboard data to the emulator.

    Verify that the clipboard data received is same.

    Args:
      clipboard_data: clipboard data to be set.
    """
    set_clip_data = ClipData(text=clipboard_data)
    await emulator_controller.setClipboard(set_clip_data)

    async def expected_clip():
        status = await emulator_controller.getClipboard(_EMPTY_)
        return status.text == clipboard_data

    assert await eventually(expected_clip), "Clipboard data doesn't match"


@pytest.mark.embedded
@pytest.mark.skipos("win", "reason=b/305040235 - error at setup.")
async def test_stream_clipboard_immediately_sends_data(emulator_controller):
    """Validate that the streaming call will immediately send the current clipboard status."""
    clipboard_data = "Hello there!"
    await set_clip_data(emulator_controller, clipboard_data)

    # We should get an "instant" notification with the clipboard data.
    # If we get nothin we would timeout.
    stream = emulator_controller.streamClipboard(_EMPTY_)
    async for clip in stream:
        assert clip.text == clipboard_data
        return

    assert False


@pytest.mark.embedded
@pytest.mark.skipos("win", "reason=b/305040856 - error at setup.")
async def test_stream_clipboard_sends_updated_data(emulator_controller, avd):
    """Validate that the streaming call will immediately send the current clipboard status and
    will send out events if the clipboard status changes.
    """
    clipboard_data = "Hello there!"
    await set_clip_data(emulator_controller, clipboard_data)

    stream = emulator_controller.streamClipboard(_EMPTY_)
    clip = await asyncio.wait_for(stream.read(), timeout=1)
    assert clip.text == "Hello there!"

    # Since the update came from our channel, we should not get anything
    update = ClipData(text="new data")
    await emulator_controller.setClipboard(update)

    with pytest.raises(asyncio.TimeoutError):
        # So we should timeout
        clip = await asyncio.wait_for(stream.read(), timeout=1)


def get_test_channel(desc, max_length=4096):
    """Configure a grpc test channel."""
    port = desc.get("grpc.port", 8554)
    addr = desc.get("grpc.address", f"localhost:{port}")

    interceptors = []
    # Install studio token if needed.
    if "grpc.token" in desc._description:
        bearer = "Bearer {}".format(desc.get("grpc.token", ""))
        interceptors = header_adder_interceptor("authorization", bearer, True)

    return grpc.aio.insecure_channel(
        addr,
        options=[
            ("grpc.max_send_message_length", max_length),
            ("grpc.max_receive_message_length", max_length),
        ],
        interceptors=interceptors,
    )


@pytest.mark.embedded
async def test_stream_clipboard_sends_updated_data_to_other_channel(avd):
    # We forcefully create 2 different channel configurations to make
    # sure that python is not going to "cleverly" re-use an existing channel.
    channel1 = get_test_channel(avd.description, 8192)
    channel2 = get_test_channel(avd.description, 8192 * 2)
    assert channel1 != channel2

    emulator_controller = EmulatorControllerStub(channel1)
    second_controller = EmulatorControllerStub(channel2)

    # Set the clipboard to a known state
    clipboard_data = "Hello there!"
    await set_clip_data(emulator_controller, clipboard_data)

    # The 2nd stream should immediately get this.
    stream = second_controller.streamClipboard(_EMPTY_)
    clip = await asyncio.wait_for(stream.read(), timeout=2)
    assert clip.text == "Hello there!"

    # Now we update the clipboard from channel1
    clipboard_data = "Hello world"
    update = ClipData(text=clipboard_data)
    await emulator_controller.setClipboard(update)

    # And the 2nd stream should immediately get this.
    clip = await asyncio.wait_for(stream.read(), timeout=2)
    assert clip.text == "Hello world"


@pytest.mark.embedded
async def test_stream_clipboard_sends_updated_data_to_other_channel_only_once(avd):
    # We forcefully create 2 different channel configurations to make
    # sure that python is not going to "cleverly" re-use an existing channel.
    channel1 = get_test_channel(avd.description, 8192)
    channel2 = get_test_channel(avd.description, 8192 * 2)
    assert channel1 != channel2

    emulator_controller = EmulatorControllerStub(channel1)
    second_controller = EmulatorControllerStub(channel2)

    # Set the clipboard to a known state
    clipboard_data = "Hello there!"
    await set_clip_data(emulator_controller, clipboard_data)

    # The 2nd stream should immediately get this.
    stream = second_controller.streamClipboard(_EMPTY_)
    clip = await asyncio.wait_for(stream.read(), timeout=2)
    assert clip.text == "Hello there!"

    # Now we update the clipboard from channel1
    clipboard_data = "Hello world"
    update = ClipData(text=clipboard_data)
    await emulator_controller.setClipboard(update)

    # And the 2nd stream should immediately get this.
    clip = await asyncio.wait_for(stream.read(), timeout=2)
    assert clip.text == "Hello world"

    # Now we update the clipboard from channel1 with the same value
    # again, since we are not changing the clipboard we should
    # not get notified
    update = ClipData(text=clipboard_data)
    await emulator_controller.setClipboard(update)

    # Since the update didn't change any state
    with pytest.raises(asyncio.TimeoutError):
        # We should timeout
        clip = await asyncio.wait_for(stream.read(), timeout=1)


@pytest.mark.embedded
async def test_stream_clipboard_from_android_immediately_sends_data(
    avd, emulator_controller, animation_app
):
    """Verify that the internal clipboard status that is changed within android is sent."""
    clipboard_data = "ola"
    await avd.stop_activity("com.google.AnimateBox")
    await avd.start_activity(
        "com.google.AnimateBox/com.google.emu.ClipActivity",
        f'--es "clip" "{clipboard_data}"',
    )

    # We should get a notification with the clipboard data.
    stream = emulator_controller.streamClipboard(_EMPTY_)
    clip = await asyncio.wait_for(stream.read(), timeout=2)
    assert clip.text == clipboard_data
