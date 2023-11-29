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
import time

import pytest
from aemu.proto.emulator_controller_pb2 import (
    ImageFormat,
    ParameterValue,
    PhysicalModelValue,
    Posture,
    Notification,
)
from emu.timing import eventually
from google.protobuf import empty_pb2
from iterators import TimeoutIterator
from tests.test_utils import StreamingCall
from PIL import Image

avd_config = {"api": "34",
              "tag.id": "google_apis",
"hw.device.name" : "pixel_fold",
"hw.displayRegion.0.1.height" : "2092",
"hw.displayRegion.0.1.width" : "1080",
"hw.displayRegion.0.1.xOffset" : "0",
"hw.displayRegion.0.1.yOffset" : "0",
"hw.initialOrientation" : "landscape",
"hw.lcd.density" : "420",
"hw.lcd.height" : "1840",
"hw.lcd.width" : "2208",
"hw.sensor.hinge" : "yes",
"hw.sensor.hinge.areas" : "1080-0-0-1840",
"hw.sensor.hinge.count" : "1",
"hw.sensor.hinge.defaults" : "180",
"hw.sensor.hinge.ranges" : "0-180",
"hw.sensor.hinge.sub_type" : "1",
"hw.sensor.hinge.type" : "1",
"hw.sensor.hinge_angles_posture_definitions" : "0-30, 30-150, 150-180",
"hw.sensor.posture_list" : "1, 2, 3",
"hw.sensors.orientation" : "yes",
"hw.sensors.proximity" : "yes",
              }


def set_device_hinge_angle(emu, angle):
    """Change the device's hinge angle"""
    emu.setPhysicalModel(
        PhysicalModelValue(
            target=PhysicalModelValue.HINGE_ANGLE0,
            value=ParameterValue(data=[angle, 0.0, 0.0]),
        )
    )


@pytest.mark.foldable
@pytest.mark.parametrize(
    "fmt,fold_angle,unfold_angle", [(ImageFormat.RGB888, 15.0, 180.0)]
)
def test_new_foldable(emulator_controller, fmt, fold_angle, unfold_angle):

    set_device_hinge_angle(emulator_controller, unfold_angle)
    time.sleep(5)
    image1 = emulator_controller.getScreenshot(
        ImageFormat(
            format=fmt,
        )
    )
    # Since the device is unfolded, we should have
    # returned foldedDisplay with unset value 0.
    assert image1.format.foldedDisplay.width == 0
    assert image1.format.foldedDisplay.height == 0

    set_device_hinge_angle(emulator_controller, fold_angle)
    time.sleep(5)
    image2 = emulator_controller.getScreenshot(
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
    set_device_hinge_angle(emulator_controller, unfold_angle)
    time.sleep(5)
    image3 = emulator_controller.getScreenshot(
        ImageFormat(
            format=fmt,
        )
    )
    assert image3.format.width > image2.format.width


@pytest.mark.foldable
@pytest.mark.parametrize(
    "fmt,fold_angle,unfold_angle", [(ImageFormat.RGB888, 5.0, 180.0)]
)
def test_new_foldable_notifications(emulator_controller, fmt, fold_angle, unfold_angle):
    _EMPTY_ = empty_pb2.Empty()

    def check_posture_closed(notification):
        return notification.posture.value == Posture.PostureValue.POSTURE_CLOSED
    def check_posture_opened(notification):
        return notification.posture.value == Posture.PostureValue.POSTURE_OPENED

    # Due to an implementation issue of TimeoutIterator, we cannot use 2
    # "eventually" with one stream. Thus we implement our own version of
    # "eventually".
    #
    # We might consider moving this implementation into timing.py in future.
    def wait_for_with_timed_iterator(predicate, timed_iterator, timeout = 5):
        end = time.time() + timeout
        for event in timed_iterator:
            if time.time() > end:
                return None
            if event == timed_iterator.get_sentinel():
                continue
            if predicate(event):
                return event
        return None

    notificationStream = emulator_controller.streamNotification(_EMPTY_)
    with StreamingCall(notificationStream) as stream:
        timed_iterator = TimeoutIterator(stream, timeout=0.5)
        assert wait_for_with_timed_iterator(check_posture_opened,
            timed_iterator), f"Did not observe initial unfolded state."
        set_device_hinge_angle(emulator_controller, fold_angle)
        assert wait_for_with_timed_iterator(check_posture_closed,
            timed_iterator), f"Did not observe folding event."

    notificationStream = emulator_controller.streamNotification(_EMPTY_)
    with StreamingCall(notificationStream) as stream:
        timed_iterator = TimeoutIterator(stream, timeout=0.5)
        assert wait_for_with_timed_iterator(check_posture_closed,
            timed_iterator), f"Did not observe initial folded state."
        set_device_hinge_angle(emulator_controller, unfold_angle)
        assert wait_for_with_timed_iterator(check_posture_opened,
            timed_iterator), f"Did not observe unfolding event."
