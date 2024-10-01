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
import json
import logging

import pytest
from aemu.proto.emulator_controller_pb2 import InputEvent, KeyboardEvent, MouseEvent


@pytest.fixture
async def retrieve_events(animation_app, avd):
    """Retrieves events from the aemu animation app.

    The animation app logs key and mouse events. With this
    fixture you can extract them after you have send your
    sequence of events.

    expected = [....]
    send_events(...)

    assert expected == retrieve_events()

    Note: This will pull everything from the adb stream and wait at 1s before it returns..

    Returns:
        A list of events.
    """
    observed = []

    def _extract_event(line: str):
        """Extracts an event from a line of logcat output.

        Args:
            line: A line of logcat output.

        Returns:
            An event, or an empty dictionary if the line does not contain an event.
        """
        AEMU_STR = "I aemu    :"
        try:
            offset = line.index(AEMU_STR) + len(AEMU_STR)
            return json.loads(line[offset:])
        except ValueError as _ignore:
            return {}

    async def _retrieve_events():
        """Retrieves events from logcat."""
        async with await avd.adb.logcat(tag="aemu") as stream:
            observed.clear()
            async for logline in stream:
                logging.info("Extracting %s", logline)
                if "--STARTED--" in logline:
                    # Workaround for lingering logcat.
                    observed.clear()
                event = _extract_event(logline)
                if "type" in event:
                    observed.append(event)

    async def _retrieve_events_with_timeout():
        try:
            await asyncio.wait_for(_retrieve_events(), 1)
        except asyncio.TimeoutError:
            return observed

    return _retrieve_events_with_timeout


def event_to_json(event):
    typ = ""
    obj = {}
    if isinstance(event, MouseEvent):
        typ = "MouseEvent"
        obj = {"x": event.x - 1, "y": event.y - 1}
        if event.buttons:
            obj["buttons"] = event.buttons

    if isinstance(event, KeyboardEvent):
        typ = "KeyboardEvent"
        obj = {"key": event.key}

        if event.eventType == KeyboardEvent.keyup:
            obj["eventType"] = "keyup"

    return {"type": typ, "object": obj}


@pytest.fixture
async def send_event(avd, emulator_controller):
    expected = []

    async def send_single_event(event, throttle=0.1):
        await asyncio.sleep(throttle)

        if isinstance(event, MouseEvent):
            await emulator_controller.sendMouse(event)
        if isinstance(event, KeyboardEvent):
            await emulator_controller.sendKey(event)

        expected.append(event_to_json(event))
        return expected

    return send_single_event


async def test_send_a_sequence_of_single_mouse_events(
    animation_app, send_event, retrieve_events
):
    # Send a series of clicks that we can observe
    for x in range(150, 160):
        await send_event(MouseEvent(x=x, y=x, buttons=1))
        expected = await send_event(MouseEvent(x=x, y=x, buttons=0))

    retrieved = await retrieve_events()
    logging.info("expected: %s", expected)
    logging.info("retrieved: %s", retrieved)
    assert expected == retrieved


async def test_send_a_sequence_of_single_key_events(
    animation_app, send_event, retrieve_events
):
    # Send a series of clicks that we can observe
    for key in "abcdefghijklmnopqrstuvwxyz":
        await send_event(KeyboardEvent(key=key, eventType=KeyboardEvent.keydown))
        expected = await send_event(
            KeyboardEvent(key=key, eventType=KeyboardEvent.keyup)
        )

    retrieved = await retrieve_events()
    logging.info("expected: %s", expected)
    logging.info("retrieved: %s", retrieved)
    assert expected == retrieved


async def test_stream_a_sequence_of_key_events(
    animation_app, emulator_controller, retrieve_events
):
    # Send a series of clicks that we can observe
    def key_input_event_generator():
        for key in "abcdefghijklmnopqrstuvwxyz":
            yield KeyboardEvent(key=key, eventType=KeyboardEvent.keydown)
            yield KeyboardEvent(key=key, eventType=KeyboardEvent.keyup)

    async def delayed_key_input_event_generator():
        for key in key_input_event_generator():
            await asyncio.sleep(0.1)
            yield InputEvent(key_event=key)

    await emulator_controller.streamInputEvent(delayed_key_input_event_generator())

    expected = [event_to_json(event) for event in key_input_event_generator()]
    retrieved = await retrieve_events()
    logging.info("expected: %s", expected)
    logging.info("retrieved: %s", retrieved)
    assert expected == retrieved


@pytest.mark.embedded
async def test_stream_a_sequence_of_mouse_events(
    animation_app, emulator_controller, retrieve_events
):
    # Send a series of clicks that we can observe
    def mouse_input_event_generator():
        for x in range(150, 160):
            yield MouseEvent(x=x, y=x, buttons=1)
            yield MouseEvent(x=x, y=x, buttons=0)

    async def delayed_mouse_input_event_generator():
        for mouse in mouse_input_event_generator():
            await asyncio.sleep(0.1)
            yield InputEvent(mouse_event=mouse)

    await emulator_controller.streamInputEvent(delayed_mouse_input_event_generator())

    expected = [event_to_json(event) for event in mouse_input_event_generator()]
    retrieved = await retrieve_events()
    logging.info("expected: %s", expected)
    logging.info("retrieved: %s", retrieved)
    assert expected == retrieved
