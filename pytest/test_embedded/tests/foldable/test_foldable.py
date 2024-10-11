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
from snaptool.snapshot import AsyncSnapshotService
from aemu.proto.snapshot_service_pb2_grpc import SnapshotServiceStub


async def set_device_hinge_angle(emu, angle):
    """Change the device's hinge angle"""
    await emu.setPhysicalModel(
        PhysicalModelValue(
            target=PhysicalModelValue.HINGE_ANGLE0,
            value=ParameterValue(data=[angle, 0.0, 0.0]),
        )
    )


@pytest.fixture
async def snapshot_service(avd, service):
    """Fixture to make sure the emulator has no snapshots."""
    snapshot_service = service(SnapshotServiceStub)
    snap = AsyncSnapshotService(snapshot_service=snapshot_service)
    snapshots = await snap.lists()
    for entry in snapshots:
        await snap.delete(entry.snapshot_id)
    yield snap
    snapshots = await snap.lists()
    for entry in snapshots:
        await snap.delete(entry.snapshot_id)


@pytest.mark.foldable
@pytest.mark.parametrize(
    "fmt,fold_angle,unfold_angle", [(ImageFormat.RGB888, 15.0, 180.0)]
)
async def test_foldable(emulator_controller, fmt, fold_angle, unfold_angle):
    set_device_hinge_angle(emulator_controller, unfold_angle)
    await asyncio.sleep(5)
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
    await asyncio.sleep(5)
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
    await asyncio.sleep(5)
    image3 = await emulator_controller.getScreenshot(
        ImageFormat(
            format=fmt,
        )
    )
    assert image3.format.width > image2.format.width


@pytest.mark.foldable
@pytest.mark.parametrize(
    "fmt,fold_angle,unfold_angle", [(ImageFormat.RGB888, 15.0, 180.0)]
)
@pytest.mark.async_timeout(90)
@pytest.mark.flaky(reruns=0)
async def test_folded_snapshot_sanity(
    emulator_controller, snapshot_service, fmt, fold_angle, unfold_angle
):
    # fold the device
    await set_device_hinge_angle(emulator_controller, fold_angle)
    await asyncio.sleep(5)

    # take a snapshot of folded device
    assert await snapshot_service.save("foo")
    snapshots = await snapshot_service.lists()
    assert "foo" in [x.snapshot_id for x in snapshots]

    # unfold the device
    await set_device_hinge_angle(emulator_controller, unfold_angle)
    await asyncio.sleep(5)

    # take a screenshot of unfolded device
    image1 = await emulator_controller.getScreenshot(
        ImageFormat(
            format=fmt,
        )
    )

    # load the snapshot of folded device to a unfolded device
    # verify if snapshot taken from a folded AVD, when loaded on unfolded AVD
    # makes an unfolded AVD to a folded AVD.
    assert await snapshot_service.load("foo")
    await asyncio.sleep(5)

    # take a screenshot of folded device
    image2 = await emulator_controller.getScreenshot(
        ImageFormat(
            format=fmt,
        )
    )

    assert image2.format.width < image1.format.width


@pytest.mark.foldable
@pytest.mark.parametrize(
    "fmt,fold_angle,unfold_angle", [(ImageFormat.RGB888, 15.0, 180.0)]
)
@pytest.mark.flaky(reruns=0)
@pytest.mark.async_timeout(90)
async def test_unfolded_snapshot_sanity(
    emulator_controller, snapshot_service, fmt, fold_angle, unfold_angle
):
    # unfold the device
    await set_device_hinge_angle(emulator_controller, unfold_angle)
    await asyncio.sleep(5)

    # take a snapshot of unfolded device
    assert await snapshot_service.save("foo")
    snapshots = await snapshot_service.lists()
    assert "foo" in [x.snapshot_id for x in snapshots]

    # fold the device
    await set_device_hinge_angle(emulator_controller, fold_angle)
    await asyncio.sleep(5)

    # take a screenshot of a folded device
    image1 = await emulator_controller.getScreenshot(
        ImageFormat(
            format=fmt,
        )
    )

    # load the snapshot of unfolded device to a folded device
    # Verify if snapshot taken from a unfolded AVD, when loaded on a folded AVD
    # makes a folded AVD to an unfolded AVD.
    assert await snapshot_service.load("foo")
    await asyncio.sleep(5)

    # take a screenshot of unfolded device
    image2 = await emulator_controller.getScreenshot(
        ImageFormat(
            format=fmt,
        )
    )

    assert image1.format.width < image2.format.width


@pytest.mark.foldable
@pytest.mark.parametrize(
    "fmt,fold_angle,unfold_angle", [(ImageFormat.RGB888, 5.0, 180.0)]
)
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
        contains(check_posture_closed, notificationStream), timeout=5
    )
