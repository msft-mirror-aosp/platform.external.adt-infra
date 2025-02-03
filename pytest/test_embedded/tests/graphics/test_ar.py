# Copyright 2025 The Android Open Source Project
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

from emu.timing import eventually
from emu.images.convert import proto_to_pillow
from aemu.proto.emulator_controller_pb2 import Image, ImageFormat, RotationRadian
from functools import partial
import numpy as np
import cv2
import pytest
import logging


@pytest.fixture
async def camera_activity(avd, ad_ui, do_not_display_virtualscene_info):
    """Launch the camera activity.

    Args:
        emulator: The configured emulator instance.
        ad_ui: UIautomator snippet's emulator device.
    """
    await avd.start_activity("com.android.camera2/com.android.camera.CameraActivity")
    ad_ui(text="NEXT", res="com.android.camera2:id/confirm_button").wait.click(20e3)

    ad_ui(
        text="Only this time",
        res="com.android.permissioncontroller:id/permission_allow_one_time_button",
    ).wait.click(20e3)

    assert ad_ui(res="com.android.camera2:id/shutter_button").wait.exists(20e3)


async def get_AR_green_rect_coords(stream, timeout=20):
    """Detect the green marker in the virtual scene and retrieve its center coordinates.

    Scans the screenshot stream to detect the green rectangle marker in the
    virtual scene and calculates its center coordinates using OpenCV.

    Args:
        stream (streaming_img_call): The asynchronous stream providing screenshots.
        timeout (int, optional): The maximum time in seconds to wait for the
                                 rectangle to appear. Defaults to 20 seconds.

    Returns:
        list: A list containing the horizontal (x) and vertical (y) coordinates
              of the rectangle's center, if detected.
        None: If the green marker region is not found within the specified timeout.
    """
    center_coords = []

    async def _detect_AR_green_rect(img: Image):
        """Check for the presence of the green rectangle and calculate its center.

        Identifies green-colored contours in the provided screenshot. If exactly
        one green region is detected, calculates the centroid coordinates using
        image moments and stores them in `center_coords`.

        Args:
            img (Image): A screenshot image obtained from the stream.

        Returns:
            bool:
                - True: If exactly one green region is detected.
                - False: If no green rectangle is found, multiple green contours are
                         detected or if the centroid cannot be determined.
        """
        nonlocal center_coords
        pillow_img = proto_to_pillow(img)
        img_arr = np.array(pillow_img)
        image = cv2.cvtColor(img_arr, cv2.COLOR_RGB2BGR)
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        green_mask = cv2.inRange(hsv, (40, 40, 40), (70, 255, 255))
        contours, _ = cv2.findContours(
            green_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        if len(contours) != 1:
            # We expect only one green contour
            return False
        # Calculate the region's centroid
        M = cv2.moments(contours[0])
        if M["m00"] == 0:
            return False
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])
        center_coords += [cx] + [cy]
        return True

    res = await eventually(_detect_AR_green_rect, stream, timeout)
    return center_coords if res else None


async def get_navigation_direction(initial_center_coords, stream):
    """Determine the direction of the virtual scene camera movement.

    Analyzes the movement of the virtual scene camera based on the initial x-y
    coordinates of the green marker's center. Determines whether the camera moves
    left, right, up, down, remains idle, or is in an unknown state.

    Args:
        initial_center_coords (list): The initial x-y coordinates of the
                                      rectangle's center.
        stream (streaming_img_call): The asynchronous stream providing screenshots.

    Returns:
        str: The navigation direction of the virtual scene camera (left, right,
             up, down, idle, or unknown).

    Notes:
        In the 'idle' state, the virtual scene camera tends to fluctuate around the center.
        Movement is detected if the variation in x-y coordinates exceeds `move_threshold`.
        If the variation is less than `idle_threshold`, the camera is assumed to be idle.
    """
    move_threshold = 200  # in Pixels
    iddle_threshold = 10  # in Pixels
    cx0, cy0 = initial_center_coords
    final_coords = await get_AR_green_rect_coords(stream)
    assert final_coords is not None, "Couldn't detect AR marker."
    cx, cy = final_coords

    deltax, deltay = cx - cx0, cy - cy0
    if abs(deltax) < iddle_threshold and abs(deltay) < iddle_threshold:
        direction = "idle"
    if deltax < -move_threshold and abs(deltay) < iddle_threshold:
        direction = "right"
    elif deltax > move_threshold and abs(deltay) < iddle_threshold:
        direction = "left"
    elif deltay < -move_threshold and abs(deltax) < iddle_threshold:
        direction = "up"
    elif deltay > move_threshold and abs(deltax) < iddle_threshold:
        direction = "down"
    else:
        direction = "unknown"
    return direction


@pytest.mark.async_timeout(300)
async def test_ar_sanity(avd, camera_activity, stream_screenshot, emulator_controller):
    """
    Objective: Verify the Augmented Reality (AR) emulator feature is supported.

    Args:
        avd: The emulator instance.
        camera_activity: A fixture that launches the camera app.
        stream_screenshot: A fixture that provides the screenshot streaming function.
        emulator_controller: The EmulatorControllerStub instance.

    Test Steps:
        1. Launch a new AVD with the AR feature flags (Verify 1).
        2. Open the camera app (Verify 2).
        3. Navigate the virtual scene right, left, up, and down using the emulator
           controller (Verify 3).

    Verify:
        1. The emulator starts without errors or crashes.
        2. The camera app displays the virtual scene room, confirmed by the
           presence of a small green rectangular-like region in the TV corner.
        3. Virtual scene navigation works without issues, with the green marker
           moving as expected in response to navigation input.
    """

    async def _has_navigated(expected_direction, original_center, stream):
        """Check if the virtualscene camera has moved to a specified direction."""
        return (
            await get_navigation_direction(original_center, stream)
            == expected_direction
        )

    api = await avd.api_level()
    if api != 31:
        pytest.skip(reason="Requires API level 31.")

    assert avd.is_alive(), "Couldn't launch the emulator."

    if avd.configuration.hardware['hw.camera.back'] != 'virtualscene':
        pytest.skip("Test requires AR feature flags.")

    stream = stream_screenshot(ImageFormat(format=ImageFormat.RGB888))

    for expected_direction, radian in [
        ("right", RotationRadian(x=0, y=-0.4, z=0)),
        ("left", RotationRadian(x=0, y=0.4, z=0)),
        ("up", RotationRadian(x=-0.4, y=0, z=0)),
        ("down", RotationRadian(x=0.4, y=0, z=0)),
    ]:
        logging.info(f"Navigating VirtualScene camera to the {expected_direction} ...")

        # Get the current center coordinates
        original_coords = await get_AR_green_rect_coords(stream)
        assert original_coords is not None, "Couldn't detect AR marker."

        # Rotate the virtualscene camera
        await emulator_controller.rotateVirtualSceneCamera(radian)

        # Verify camera navigation
        assert await eventually(
            partial(_has_navigated, expected_direction, original_coords, stream),
            timeout=30,
        )
