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
import asyncio

import pytest
from aemu.proto.emulator_controller_pb2 import (
    ImageFormat,
    ParameterValue,
    PhysicalModelValue,
    Posture,
)
from google.protobuf import empty_pb2

# b/288457753
# Should use API 33 instead
avd_config = {"api": "31", "tag.id": "google_apis", "device.name": "PixelFold"}


async def set_device_hinge_angle(emu, angle):
    """Change the device's hinge angle"""
    await emu.setPhysicalModel(
        PhysicalModelValue(
            target=PhysicalModelValue.HINGE_ANGLE0,
            value=ParameterValue(data=[angle, 0.0, 0.0]),
        )
    )


@pytest.mark.skipos("all", "b/288335290")
@pytest.mark.foldable
@pytest.mark.parametrize(
    "fmt,fold_angle,unfold_angle", [(ImageFormat.RGB888, 15.0, 180.0)]
)
@pytest.mark.async_timeout(30)
async def test_foldable(emulator_controller, fmt, fold_angle, unfold_angle):
    set_device_hinge_angle(emulator_controller, unfold_angle)
    asyncio.sleep(5)
    image1 = await emulator_controller.getScreenshot(
        ImageFormat(
            format=fmt,
        )
    )
    # Since the device is unfolded, we should have
    # returned foldedDisplay with unset value 0.
    assert image1.format.foldedDisplay.width == 0
    assert image1.format.foldedDisplay.height == 0

    await set_device_hinge_angle(emulator_controller, fold_angle)
    asyncio.sleep(5)
    image2 = await emulator_controller.getScreenshot(
        ImageFormat(
            format=fmt,
        )
    )
    assert image1.format.width > image2.format.width
    # Since we don't specify the width and height
    # in the request, the retruned imageFormat size
    # should be the same as the folded screen in config.ini
    assert image2.format.foldedDisplay.width == image2.format.width
    assert image2.format.foldedDisplay.height == image2.format.height
    await set_device_hinge_angle(emulator_controller, unfold_angle)
    asyncio.sleep(5)
    image3 = await emulator_controller.getScreenshot(
        ImageFormat(
            format=fmt,
        )
    )
    assert image3.format.width > image2.format.width


@pytest.mark.foldable
@pytest.mark.parametrize(
    "fmt,fold_angle,unfold_angle", [(ImageFormat.RGB888, 5.0, 180.0)]
)
@pytest.mark.async_timeout(30)
async def test_foldable_notifications(
    emulator_controller, fmt, fold_angle, unfold_angle
):
    _EMPTY_ = empty_pb2.Empty()

    def check_posture_closed(notification):
        return notification.posture.value == Posture.PostureValue.POSTURE_CLOSED

    def check_posture_opened(notification):
        return notification.posture.value == Posture.PostureValue.POSTURE_OPENED

    # True if the predicate holds for an element in the stream
    async def contains(predicate, stream):
        async for elem in stream:
            if predicate(elem):
                return True
        return False

    notificationStream = emulator_controller.streamNotification(_EMPTY_)
    # assert await eventually(contains(check_posture_opened, notificationStream))

    assert await asyncio.wait_for(
        contains(check_posture_opened, notificationStream), timeout=5
    )
    await set_device_hinge_angle(emulator_controller, fold_angle)
    # assert await eventually(contains(check_posture_closed, notificationStream))
    assert await asyncio.wait_for(
        await contains(check_posture_closed, notificationStream), timeout=5
    )
