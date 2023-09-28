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

import time

from aemu.discovery.header_manipulator_client_interceptor import (
    header_adder_interceptor,
)
import pytest
from aemu.proto.emulator_controller_pb2 import ClipData
from aemu.proto.emulator_controller_pb2_grpc import EmulatorControllerStub
from google.protobuf import empty_pb2
from iterators import TimeoutIterator

from emu.timing import eventually
from tests.test_utils import StreamingCall
import grpc

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


@pytest.mark.e2e
@pytest.mark.embedded
@pytest.mark.timeout(timeout=10, func_only=True)
def test_stream_clipboard_immediately_sends_data(emulator_controller):
    """Validate that the streaming call will immediately send the current clipboard status."""
    clipboard_data = "Hello there!"
    set_clip_data = ClipData(text=clipboard_data)
    emulator_controller.setClipboard(set_clip_data)

    # We should actually have "Hello there!" on the clipboard.
    assert eventually(
        lambda: emulator_controller.getClipboard(_EMPTY_).text == clipboard_data
    ), "Clipboard data doesn't match"

    # We should get an "instant" notification with the clipboard data.
    emulator_controller.streamClipboard(_EMPTY_)
    with StreamingCall(emulator_controller.streamClipboard(_EMPTY_)) as stream:
        timed_iterator = TimeoutIterator(stream, timeout=0.5)
        assert wait_for_with_timed_iterator(
            lambda clip: clip.text == clipboard_data, timed_iterator
        ), f"Did receive the clipboard event with {clipboard_data}"


@pytest.mark.e2e
@pytest.mark.embedded
@pytest.mark.timeout(timeout=10, func_only=True)
def test_stream_clipboard_sends_updated_data(emulator_controller, avd):
    """Validate that the streaming call will immediately send the current clipboard status and
    will send out events if the clipboard status changes.
    """
    clipboard_data = "Hello there!"
    set_clip_data = ClipData(text=clipboard_data)
    emulator_controller.setClipboard(set_clip_data)

    # We should actually have "Hello there!" on the clipboard.
    assert eventually(
        lambda: emulator_controller.getClipboard(_EMPTY_).text == clipboard_data
    ), "Clipboard data doesn't match"

    # We should get nothing!
    with StreamingCall(emulator_controller.streamClipboard(_EMPTY_)) as stream:
        timed_iterator = TimeoutIterator(stream, timeout=0.5)
        assert wait_for_with_timed_iterator(
            lambda clip: clip.text == clipboard_data, timed_iterator
        ), f"Did receive the clipboard event with {clipboard_data}"

        # Now we update the clipboard, and expect an event with the new data
        clipboard_data = "Hello world"
        set_clip_data = ClipData(text=clipboard_data)
        emulator_controller.setClipboard(set_clip_data)

        # We should definitely not receive an update as we should be
        # using the same channel!
        assert not wait_for_with_timed_iterator(
            lambda clip: clip.text == clipboard_data, timed_iterator
        ), f"Did receive the clipboard event with {clipboard_data}"


def get_test_channel(desc, max_length=4096):
    """Configure a grpc test channel."""
    port = desc.get("grpc.port", 8554)
    addr = desc.get("grpc.address", f"localhost:{port}")
    channel = grpc.insecure_channel(
        addr,
        options=[
            ("grpc.max_send_message_length", max_length),
            ("grpc.max_receive_message_length", max_length),
        ],
    )

    # Install studio token if needed.
    if "grpc.token" in desc._description:
        bearer = "Bearer {}".format(desc.get("grpc.token", ""))
        return grpc.intercept_channel(
            channel, header_adder_interceptor("authorization", bearer)
        )


@pytest.mark.e2e
@pytest.mark.embedded
@pytest.mark.timeout(timeout=10, func_only=True)
def test_stream_clipboard_sends_updated_data_to_other_channel(avd):
    # We forcefully create 2 different channel configurations to make
    # sure that python is not going to "cleverly" re-use an existing channel.
    channel1 = get_test_channel(avd.description, 8192)
    channel2 = get_test_channel(avd.description, 8192 * 2)
    assert channel1 != channel2

    emulator_controller = EmulatorControllerStub(channel1)
    second_controller = EmulatorControllerStub(channel2)

    clipboard_data = "Hello there!"
    set_clip_data = ClipData(text=clipboard_data)
    emulator_controller.setClipboard(set_clip_data)

    # We should actually have "Hello there!" on the clipboard.
    assert eventually(
        lambda: emulator_controller.getClipboard(_EMPTY_).text == clipboard_data
    ), "Clipboard data doesn't match"


    with StreamingCall(second_controller.streamClipboard(_EMPTY_)) as stream:
        timed_iterator = TimeoutIterator(stream, timeout=0.5)

        # We immediately get the current state of the clipboard
        assert wait_for_with_timed_iterator(
            lambda clip: clip.text == clipboard_data, timed_iterator
        ), f"Did receive the clipboard event with {clipboard_data}"

        # Now we update the clipboard, and expect an event with the new data
        # Note that we are sending the change over channel1, and are streaming
        # on channel2
        clipboard_data = "Hello world"
        set_clip_data = ClipData(text=clipboard_data)
        emulator_controller.setClipboard(set_clip_data)

        # channel2 should be notified of the change.
        assert wait_for_with_timed_iterator(
            lambda clip: clip.text == clipboard_data, timed_iterator
        ), f"Did receive the clipboard event with {clipboard_data}"


@pytest.mark.e2e
@pytest.mark.embedded
@pytest.mark.timeout(timeout=10, func_only=True)
def test_stream_clipboard_sends_updated_data_to_other_channel_only_once(avd):
    # We forcefully create 2 different channel configurations to make
    # sure that python is not going to "cleverly" re-use an existing channel.
    channel1 = get_test_channel(avd.description, 8192)
    channel2 = get_test_channel(avd.description, 8192 * 2)
    assert channel1 != channel2

    emulator_controller = EmulatorControllerStub(channel1)
    second_controller = EmulatorControllerStub(channel2)

    clipboard_data = "Hello there!"
    set_clip_data = ClipData(text=clipboard_data)
    emulator_controller.setClipboard(set_clip_data)

    # We should actually have "Hello there!" on the clipboard.
    assert eventually(
        lambda: emulator_controller.getClipboard(_EMPTY_).text == clipboard_data
    ), "Clipboard data doesn't match"


    with StreamingCall(second_controller.streamClipboard(_EMPTY_)) as stream:
        timed_iterator = TimeoutIterator(stream, timeout=0.5)

        # We immediately get the current state of the clipboard
        assert wait_for_with_timed_iterator(
            lambda clip: clip.text == clipboard_data, timed_iterator
        ), f"Did receive the clipboard event with {clipboard_data}"

        # Now we update the clipboard, and expect an event with the new data
        # Note that we are sending the change over channel1, and are streaming
        # on channel2
        clipboard_data = "Hello world"
        set_clip_data = ClipData(text=clipboard_data)
        emulator_controller.setClipboard(set_clip_data)

        # channel2 should be notified of the change.
        assert wait_for_with_timed_iterator(
            lambda clip: clip.text == clipboard_data, timed_iterator
        ), f"Did receive the clipboard event with {clipboard_data}"

        # Now let's set the same text once more, this should not
        # result in an event as we are not "changing" the clipboard
        emulator_controller.setClipboard(set_clip_data)

        # We are not changing the state, so we should not get an event
        assert not wait_for_with_timed_iterator(
            lambda clip: clip.text == clipboard_data, timed_iterator
        ), f"Did receive the clipboard event with {clipboard_data}"


@pytest.mark.e2e
@pytest.mark.embedded
@pytest.mark.timeout(timeout=10, func_only=True)
def test_stream_clipboard_from_android_immediately_sends_data(avd, emulator_controller):
    """Verify that the internal clipboard status that is changed within android is sent."""
    clipboard_data = "ola"
    avd.stop_activity("com.google.AnimateBox")
    avd.start_activity(
        "com.google.AnimateBox/com.google.emu.ClipActivity",
        f'--es "clip" "{clipboard_data}"',
    )

    # We should get a notification with the clipboard data.
    emulator_controller.streamClipboard(_EMPTY_)
    with StreamingCall(emulator_controller.streamClipboard(_EMPTY_)) as stream:
        timed_iterator = TimeoutIterator(stream, timeout=0.5)
        assert wait_for_with_timed_iterator(
            lambda clip: clip.text == clipboard_data, timed_iterator
        ), f"Did receive the clipboard event with {clipboard_data}"
