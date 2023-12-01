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
from google.protobuf import empty_pb2
from aemu.proto.emulator_controller_pb2 import (
    ImageFormat,
    ParameterValue,
    PhysicalModelValue,
    Posture,
    Notification,
    DisplayMode,
    DisplayModeValue,
)

from tests.test_utils import StreamingCall
from emu.timing import wait_until

_EMPTY_ = empty_pb2.Empty()

avd_config = {
    "api": "34",
    "tag.id": "google_apis",
    "hw.device.name": "resizable",
"hw.lcd.density" : "420",
"hw.lcd.height" : "2340",
"hw.lcd.width" : "1080",
"hw.displayRegion.0.1.height" : "2092",
"hw.displayRegion.0.1.width" : "1080",
"hw.displayRegion.0.1.xOffset" : "0",
"hw.displayRegion.0.1.yOffset" : "0",
    "hw.resizable.configs": "phone-0-1080-2340-420, foldable-1-2208-1840-420, tablet-2-1920-1200-240, desktop-3-1920-1080-160",
    "hw.sensor.hinge" : "yes",
"hw.sensor.hinge.areas" : "1840-0-0-1840",
"hw.sensor.hinge.count" : "1",
"hw.sensor.hinge.defaults" : "180",
"hw.sensor.hinge.ranges" : "0-180",
"hw.sensor.hinge.sub_type" : "1",
"hw.sensor.hinge.type" : "1",
"hw.sensor.hinge_angles_posture_definitions" : "0-30, 30-150, 150-180",
"hw.sensor.posture_list" : "1, 2, 3",
"hw.sensors.orientation" : "yes",
"hw.sensors.proximity" : "yes",
    "skin.name": "1080x2340",
    "skin.path": "_no_skin",
}

def set_device_hinge_angle(emu, angle):
    """Change the device's hinge angle"""
    emu.setPhysicalModel(
        PhysicalModelValue(
            target=PhysicalModelValue.HINGE_ANGLE0,
            value=ParameterValue(data=[angle, 0.0, 0.0]),
        )
    )

def set_display_mode(emulator_controller, mode, timeout=5):
    emulator_controller.setDisplayMode(
        DisplayMode(
            value=mode,
        )
    )

    # Eventually the currentMode is equal to the one we have set.
    currentMode = emulator_controller.getDisplayMode(_EMPTY_).value
    timeout = time.time() + timeout
    while currentMode != mode and time.time() < timeout:
        time.sleep(0.1)
        currentMode = emulator_controller.getDisplayMode(_EMPTY_).value

    return emulator_controller.getDisplayMode(_EMPTY_).value


@pytest.mark.newresizable
@pytest.mark.parametrize(
    "width, height, mode",
    [
        (1080, 2340, DisplayModeValue.PHONE),
        (1768, 2208, DisplayModeValue.FOLDABLE),
        (1920, 1200, DisplayModeValue.TABLET),
        (1920, 1080, DisplayModeValue.DESKTOP),
    ],
)
@pytest.mark.timeout(timeout=10, func_only=True)
@pytest.mark.timeout_win(timeout=60)
@pytest.mark.flaky(reruns=2, reruns_delay=2)
@pytest.mark.sanity
@pytest.mark.skipos('all', 'reason: b/309463427')
def test_new_resizable_changes_resolution(
    animation_app, emulator_controller, width, height, mode, get_screenshot
):
    emulator_controller.setDisplayMode(DisplayMode(value=mode))
    # Eventually the currentMode is equal to the one we have set.
    # If this is broken the test will timeout
    assert wait_until(lambda: emulator_controller.getDisplayMode(_EMPTY_).value == mode)

    def screenshot_is_sized_properly():
        image, _ = get_screenshot(
            ImageFormat(
                format=ImageFormat.RGB888,
            )
        )

        format = image.format
        byte_count = len(image.image)

        return (
            format.width == width
            and format.height == height
            and byte_count == width * height * 3
        )

    # Eventually we should receive a screenshot that has the expected size.
    assert wait_until(screenshot_is_sized_properly)


@pytest.mark.newresizable
@pytest.mark.timeout(timeout=60, func_only=True)
@pytest.mark.parametrize(
    "fmt, bpp",
    [
        (ImageFormat.RGBA8888, 4),
        (ImageFormat.RGB888, 3),
    ],
)
def test_new_resizable_observable_from_streaming(
    emulator_controller, stream_screenshot, fmt, bpp
):
    available_dimensions = iter(
        [
            (1080, 2340, DisplayModeValue.PHONE),
            (2208, 1840, DisplayModeValue.FOLDABLE),
            (1920, 1200, DisplayModeValue.TABLET),
            (1920, 1080, DisplayModeValue.DESKTOP),
        ]
    )

    # Start with moving to the intial dimension
    w, h, mode = next(available_dimensions)
    assert set_display_mode(emulator_controller, mode) == mode
    time.sleep(5)

    # Wait until we observe the expected dimension in the stream of screenshots
    # If we see it we move to the next dimension we are going to check
    # Eventually we run out dimensions, resulting in a StopIteration
    # If things are broken we will timeout.
    with pytest.raises(StopIteration):
        with stream_screenshot(ImageFormat(format=fmt)) as stream:
            for image in stream:
                if image.format.width == w and image.format.height == h:
                    pixel_count = len(image.image)
                    assert pixel_count == w * h * bpp

                    # Transition to the next.
                    w, h, mode = next(available_dimensions)
                    assert set_display_mode(emulator_controller, mode) == mode
                    time.sleep(5)


@pytest.mark.newresizable
@pytest.mark.timeout(timeout=60, func_only=True)
@pytest.mark.parametrize(
    "fmt, bpp",
    [
        (ImageFormat.RGBA8888, 4),
        (ImageFormat.RGB888, 3),
    ],
)
def test_new_resizable_observable_from_streaming(
    emulator_controller, stream_screenshot, fmt, bpp
):
    available_dimensions = iter(
        [
            (1080, 2340, DisplayModeValue.PHONE),
            (2208, 1840, DisplayModeValue.FOLDABLE),
            (1920, 1200, DisplayModeValue.TABLET),
            (1920, 1080, DisplayModeValue.DESKTOP),
        ]
    )

    # Start with moving to the intial dimension
    w, h, mode = next(available_dimensions)
    emulator_controller.setDisplayMode(DisplayMode(value=mode))
    # Eventually the currentMode is equal to the one we have set.
    # If this is broken the test will timeout
    assert wait_until(lambda: emulator_controller.getDisplayMode(_EMPTY_).value == mode)
    time.sleep(5)

    # Wait until we observe the expected dimension in the stream of screenshots
    # If we see it we move to the next dimension we are going to check
    # Eventually we run out dimensions, resulting in a StopIteration
    # If things are broken we will timeout.
    with pytest.raises(StopIteration):
        with stream_screenshot(ImageFormat(format=fmt)) as stream:
            for image in stream:
                if image.format.width == w and image.format.height == h:
                    pixel_count = len(image.image)
                    assert pixel_count == w * h * bpp

                    # Transition to the next.
                    w, h, mode = next(available_dimensions)

                    emulator_controller.setDisplayMode(DisplayMode(value=mode))
                    time.sleep(5)
                    # Eventually the currentMode is equal to the one we have set.
                    # If this is broken the test will timeout
                    assert wait_until(
                        lambda: emulator_controller.getDisplayMode(_EMPTY_).value
                        == mode
                    )

@pytest.mark.newresizable
@pytest.mark.timeout(timeout=60, func_only=True)
@pytest.mark.parametrize(
    "fmt, bpp",
    [
        (ImageFormat.RGBA8888, 4),
        (ImageFormat.RGB888, 3),
    ],
)
def test_new_resizable_folding_observable_from_streaming(
    emulator_controller, stream_screenshot, fmt, bpp
):
    available_dimensions = iter(
        [
            (1080, 2340, DisplayModeValue.PHONE),
            (2208, 1840, DisplayModeValue.FOLDABLE),
            (1920, 1200, DisplayModeValue.TABLET),
            (1920, 1080, DisplayModeValue.DESKTOP),
        ]
    )

    # start with unfold
    set_device_hinge_angle(emulator_controller, 180);
    time.sleep(5)

    foldedw = 1080
    foldedh = 2092
    # Start with moving to the intial dimension
    w, h, mode = next(available_dimensions)
    assert set_display_mode(emulator_controller, mode) == mode
    time.sleep(5)

    # Transition to the next.
    w, h, mode = next(available_dimensions)
    assert set_display_mode(emulator_controller, mode) == DisplayModeValue.FOLDABLE
    time.sleep(5)

    # Now fold it
    set_device_hinge_angle(emulator_controller, 0);
    time.sleep(5)

    # Wait until we observe the expected dimension in the stream of screenshots
    with pytest.raises(StopIteration):
        with stream_screenshot(ImageFormat(format=fmt)) as stream:
            for image in stream:
                if image.format.width == foldedw and image.format.height == foldedh:
                    pixel_count = len(image.image)
                    assert pixel_count == foldedw * foldedh * bpp
                    w, h, mode = next(available_dimensions)
                    w, h, mode = next(available_dimensions)
                    w, h, mode = next(available_dimensions)
                    w, h, mode = next(available_dimensions)
