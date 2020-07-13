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
import logging
from tests.test_utils import fmt_proto, StreamingCall
from aemu.proto.emulator_controller_pb2 import (
    ImageFormat,
    ParameterValue,
    PhysicalModelValue,
    Rotation,
)


@pytest.mark.e2e
def test_rotation_observable_through_screenshot():
    """Test that setting the rotation, is observable through screenshot."""
    emu = pytest.emulator.get_emulator_controller()
    for (fine, coarse) in [
        (-180, Rotation.REVERSE_PORTRAIT),
        (-90, Rotation.REVERSE_LANDSCAPE),
        (0, Rotation.PORTRAIT),
        (90, Rotation.LANDSCAPE),
    ]:
        emu.setPhysicalModel(
            PhysicalModelValue(
                target=PhysicalModelValue.ROTATION,
                value=ParameterValue(data=[0, 0, fine]),
            )
        )
        img = emu.getScreenshot(ImageFormat())
        assert img.format.rotation.rotation == coarse


@pytest.mark.e2e
@pytest.mark.timeout(10)
def test_rotation_observable_through_stream_screenshot():
    """Test that setting the rotation, is observable through streaming screenshot."""
    emu = pytest.emulator.get_emulator_controller()
    imgStream = emu.streamScreenshot(ImageFormat(width=320, height=200))
    with StreamingCall(imgStream) as stream:
        for (fine, coarse) in [
            (-180, Rotation.REVERSE_PORTRAIT),
            (-90, Rotation.REVERSE_LANDSCAPE),
            (0, Rotation.PORTRAIT),
            (90, Rotation.LANDSCAPE),
        ]:
            emu.setPhysicalModel(
                PhysicalModelValue(
                    target=PhysicalModelValue.ROTATION,
                    value=ParameterValue(data=[0, 0, fine]),
                )
            )

            # Keep looking at the queue until we see what we need.
            # if we never see it we will timeout.
            for img in iter(stream.get, None):
                if img.format.rotation.rotation == coarse:
                    logging.info(
                        "Observered rotation to %s", fmt_proto(img.format.rotation)
                    )
                    break


@pytest.mark.e2e
def test_rotation_through_console_observable_through_physical_model():
    """Test that rotate through console, is observable through screenshot.
    bug: b/159635109
    """
    emu = pytest.emulator.get_emulator_controller()

    # Make sure we start straight!
    emu.setPhysicalModel(
        PhysicalModelValue(
            target=PhysicalModelValue.ROTATION, value=ParameterValue(data=[0, 0, 0]),
        )
    )
    for (angle, coarse) in [
        (-90, Rotation.REVERSE_LANDSCAPE),
        (-180, Rotation.REVERSE_PORTRAIT),
        (90, Rotation.LANDSCAPE),
        (0, Rotation.PORTRAIT),
    ]:
        pytest.emulator.adb(["emu", "rotate"])
        rotate = emu.getPhysicalModel(
            PhysicalModelValue(target=PhysicalModelValue.ROTATION)
        )
        assert rotate.value.data[2] == angle


@pytest.mark.e2e
def test_rotation_through_console_observable_through_screenshot():
    """Test that rotate through console, is observable through screenshot.
    bug: b/159635109
    """
    emu = pytest.emulator.get_emulator_controller()

    # Make sure we start straight!
    emu.setPhysicalModel(
        PhysicalModelValue(
            target=PhysicalModelValue.ROTATION, value=ParameterValue(data=[0, 0, 0]),
        )
    )
    for (_, coarse) in [
        (-90, Rotation.REVERSE_LANDSCAPE),
        (-180, Rotation.REVERSE_PORTRAIT),
        (90, Rotation.LANDSCAPE),
        (0, Rotation.PORTRAIT),
    ]:
        pytest.emulator.adb(["emu", "rotate"])
        img = emu.getScreenshot(ImageFormat())
        assert img.format.rotation.rotation == coarse


@pytest.mark.e2e
@pytest.mark.timeout(10)
def test_rotation_through_console_observable_through_stream_screenshot():
    """Test that rotate through console, is observable through stream screenshot.

    bug: b/159635109, b/160171559
    """
    emu = pytest.emulator.get_emulator_controller()
    imgStream = emu.streamScreenshot(ImageFormat(width=320, height=200))
    with StreamingCall(imgStream) as stream:

        # Make sure we start straight!
        emu.setPhysicalModel(
            PhysicalModelValue(
                target=PhysicalModelValue.ROTATION,
                value=ParameterValue(data=[0, 0, 0]),
            )
        )
        for (_, coarse) in [
            (-90, Rotation.REVERSE_LANDSCAPE),
            (-180, Rotation.REVERSE_PORTRAIT),
            (90, Rotation.LANDSCAPE),
            (0, Rotation.PORTRAIT),
        ]:
            pytest.emulator.adb(["emu", "rotate"])

            cnt = 0
            # Keep looking at the queue until we see what we need.
            # if we never see it we will timeout.
            for img in iter(stream.get, None):
                cnt = cnt + 1
                if img.format.rotation.rotation == coarse:
                    logging.info(
                        "Observered rotation to %s", fmt_proto(img.format.rotation)
                    )
                    break

            logging.info("Popped %d elements", cnt)
