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
from aemu.proto.emulator_controller_pb2 import (ImageFormat, ParameterValue,
                                                PhysicalModelValue)
from PIL import Image


def set_device_hinge_angle(emu, angle):
    """Change the device's hinge angle"""
    emu.setPhysicalModel(
        PhysicalModelValue(
            target=PhysicalModelValue.HINGE_ANGLE0,
            value=ParameterValue(data=[angle, 0.0, 0.0]),
        )
    )
    time.sleep(5)


@pytest.mark.skip(
    reason="Curretly, e2e test doesn't support running a different AVD with foldable support."
)
@pytest.mark.parametrize(
    "fmt,fold_angle,unfold_angle", [(ImageFormat.RGB888, 15.0, 180.0)]
)
def test_foldable(fmt, fold_angle, unfold_angle):
    emu = pytest.emulator.get_emulator_controller()
    set_device_hinge_angle(emu, unfold_angle)
    image1 = emu.getScreenshot(
        ImageFormat(
            format=fmt,
        )
    )
    # Since the device is unfolded, we should have
    # returned foldedDisplay with unset value 0.
    assert image1.format.foldedDisplay.width == 0
    assert image1.format.foldedDisplay.height == 0

    set_device_hinge_angle(emu, fold_angle)
    image2 = emu.getScreenshot(
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
    set_device_hinge_angle(emu, unfold_angle)

    image3 = emu.getScreenshot(
        ImageFormat(
            format=fmt,
        )
    )
    assert image3.format.width > image2.format.width
