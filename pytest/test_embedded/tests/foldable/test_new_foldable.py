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
import time
import logging

import pytest
from aemu.proto.emulator_controller_pb2 import (
    ImageFormat,
    Notification,
    ParameterValue,
    PhysicalModelValue,
    Posture,
)
from google.protobuf import empty_pb2
from PIL import Image

from grpc import RpcError, StatusCode
from grpc.aio import AioRpcError


from emu.timing import eventually

avd_config = {
    "api": "34",
    "tag.id": "google_apis",
    "hw.device.name": "pixel_fold",
    "hw.displayRegion.0.1.height": "2092",
    "hw.displayRegion.0.1.width": "1080",
    "hw.displayRegion.0.1.xOffset": "0",
    "hw.displayRegion.0.1.yOffset": "0",
    "hw.initialOrientation": "landscape",
    "hw.lcd.density": "420",
    "hw.lcd.height": "1840",
    "hw.lcd.width": "2208",
    "hw.sensor.hinge": "yes",
    "hw.sensor.hinge.areas": "1080-0-0-1840",
    "hw.sensor.hinge.count": "1",
    "hw.sensor.hinge.defaults": "180",
    "hw.sensor.hinge.ranges": "0-180",
    "hw.sensor.hinge.sub_type": "1",
    "hw.sensor.hinge.type": "1",
    "hw.sensor.hinge_angles_posture_definitions": "0-30, 30-150, 150-180",
    "hw.sensor.posture_list": "1, 2, 3",
    "hw.sensors.orientation": "yes",
    "hw.sensors.proximity": "yes",
}


async def set_device_hinge_angle(emu, angle):
    """Change the device's hinge angle"""
    await emu.setPhysicalModel(
        PhysicalModelValue(
            target=PhysicalModelValue.HINGE_ANGLE0,
            value=ParameterValue(data=[angle, 0.0, 0.0]),
        )
    )


@pytest.fixture
async def get_safe_screenshot(emulator_controller):
    """Gets a screenshot that handles the case where the emulator return
    FAILED_PRECONDITION The guest has not posted new frame yet"""

    async def get_safe_screenshot_impl(fmt: ImageFormat):
        # We are willing to wait up to 5 seconds for a valid screenshot.
        for i in range(0, 50):
            try:
                return await emulator_controller.getScreenshot(
                    ImageFormat(
                        format=fmt,
                    )
                )
            except AioRpcError as exc:
                if exc.code() == StatusCode.FAILED_PRECONDITION:
                    logging.error(
                        "Screenshot is not ready, will retry in 100ms, (%s)",
                        exc.details,
                    )
                    asyncio.sleep(0.1)
                else:
                    raise

    return get_safe_screenshot_impl


@pytest.mark.newfoldable
@pytest.mark.parametrize(
    "fmt,fold_angle,unfold_angle", [(ImageFormat.RGB888, 15.0, 180.0)]
)
@pytest.mark.async_timeout(1080)
async def test_new_foldable(
    emulator_controller, get_safe_screenshot, fmt, fold_angle, unfold_angle
):
    await set_device_hinge_angle(emulator_controller, unfold_angle)
    await asyncio.sleep(5)
    image1 = await get_safe_screenshot(fmt)

    # Since the device is unfolded, we should have
    # returned foldedDisplay with unset value 0.
    assert image1.format.foldedDisplay.width == 0
    assert image1.format.foldedDisplay.height == 0

    await set_device_hinge_angle(emulator_controller, fold_angle)
    await asyncio.sleep(5)
    image2 = await get_safe_screenshot(fmt)

    assert image1.format.width > image2.format.width
    # Since we don't specify the width and height
    # in the request, the retruned imageFormat size
    # should be the same as the folded screen in config.ini
    assert image2.format.foldedDisplay.width == image2.format.width
    assert image2.format.foldedDisplay.height == image2.format.height
    await set_device_hinge_angle(emulator_controller, unfold_angle)
    await asyncio.sleep(5)
    image3 = await get_safe_screenshot(fmt)
    assert image3.format.width > image2.format.width


@pytest.mark.newfoldable
@pytest.mark.parametrize(
    "fmt,fold_angle,unfold_angle", [(ImageFormat.RGB888, 5.0, 180.0)]
)
@pytest.mark.async_timeout(1080)
async def test_new_foldable_notifications(
    emulator_controller, fmt, fold_angle, unfold_angle
):
    _EMPTY_ = empty_pb2.Empty()

    def check_posture_closed(notification):
        return notification.posture.value == Posture.PostureValue.POSTURE_CLOSED

    def check_posture_opened(notification):
        return notification.posture.value == Posture.PostureValue.POSTURE_OPENED

    notificationStream = emulator_controller.streamNotification(_EMPTY_)
    assert await eventually(
        check_posture_opened, notificationStream
    ), f"Did not observe initial unfolded state."
    await set_device_hinge_angle(emulator_controller, fold_angle)
    assert await eventually(
        check_posture_closed, notificationStream
    ), f"Did not observe folding event."

    notificationStream = emulator_controller.streamNotification(_EMPTY_)
    assert await eventually(
        check_posture_closed, notificationStream
    ), f"Did not observe initial folded state."
    await set_device_hinge_angle(emulator_controller, unfold_angle)
    assert await eventually(
        check_posture_opened, notificationStream
    ), f"Did not observe unfolding event."
