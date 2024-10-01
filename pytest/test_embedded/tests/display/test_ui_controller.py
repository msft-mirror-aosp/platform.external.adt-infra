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
import logging
import random

import pytest
from aemu.proto.ui_controller_service_pb2 import PaneEntry, WindowPosition
from aemu.proto.ui_controller_service_pb2_grpc import UiControllerStub
from google.protobuf import empty_pb2

__EMPTY__ = empty_pb2.Empty()


@pytest.fixture
def ui_controller(service):
    yield service(UiControllerStub)


async def get_user_config(avd):
    channel = avd.description.get_async_grpc_channel([("emulator.security", "token")])
    ui_controller = UiControllerStub(channel)
    status = await ui_controller.getUserConfig(__EMPTY__)
    return dict([(x.key, x.value) for x in status.entries])


@pytest.mark.dependency()
@pytest.mark.embedded
async def test_ui_controller_clean(avd):
    """Tests that the emulator has no extended control setting, this means
    the extended window was never shown before.
    """
    userConfig = await get_user_config(avd)
    logging.info(userConfig)
    assert (
        "extended_controls.x" not in userConfig
    ), "The emulator already has an initial configuration, which implies the extended window has been displayed at least once!"



@pytest.mark.embedded
@pytest.mark.dependency(depends=["test_ui_controller_clean"])
async def test_ui_controller_first_position_works(avd, ui_controller):
    """Tests that setting the position for the first time will work.

    Note: This is really a best effort test.
    """
    await ui_controller.closeExtendedControls(__EMPTY__)
    x = random.randrange(800, 1200)
    y = random.randrange(400, 500)
    controlStatus = await ui_controller.showExtendedControls(
        PaneEntry(
            position=WindowPosition(
                x=x,
                y=y,
                horizontalAnchor=WindowPosition.HCENTER,
                verticalAnchor=WindowPosition.BOTTOM,
            )
        )
    )

    # We became visible.
    assert controlStatus.visibilityChanged

    userConfig = await get_user_config(avd)

    # Check the window is left and above what we set it to.
    assert "extended_controls.x" in userConfig
    assert "extended_controls.y" in userConfig
    assert "extended_controls.vanchor" in userConfig
    assert "extended_controls.hanchor" in userConfig

    assert int(userConfig["extended_controls.x"]) == x
    assert int(userConfig["extended_controls.y"]) == y
    assert userConfig["extended_controls.hanchor"] == "1"
    assert userConfig["extended_controls.vanchor"] == "2"

    # We become invisible.
    controlStatus = await ui_controller.closeExtendedControls(__EMPTY__)
    assert controlStatus.visibilityChanged



@pytest.mark.embedded
@pytest.mark.dependency(depends=["test_ui_controller_first_position_works"])
async def test_ui_controller_position_does_not_change(avd, ui_controller):
    """Tests that setting the position for the second time will work, but
       does not modify the location of the window.

    Note: This is really a best effort test.
    """
    userConfig = await get_user_config(avd)
    controlStatus = await ui_controller.closeExtendedControls(__EMPTY__)

    controlStatus = await ui_controller.showExtendedControls(
        PaneEntry(
            position=WindowPosition(
                x=10,
                y=10,
                horizontalAnchor=WindowPosition.RIGHT,
                verticalAnchor=WindowPosition.RIGHT,
            )
        )
    )

    # We became visible
    assert controlStatus.visibilityChanged

    # Similarly we SHOULD NOT update the window position, as it was already set.
    latestConfig = await get_user_config(avd)
    assert userConfig["extended_controls.x"] == latestConfig["extended_controls.x"]
    assert userConfig["extended_controls.y"] == latestConfig["extended_controls.y"]

    # We become invisible.
    controlStatus = await ui_controller.closeExtendedControls(__EMPTY__)
    assert controlStatus.visibilityChanged



@pytest.mark.embedded
async def test_ui_controller_fast_switch_should_work(ui_controller):
    """Make sure we can open and close the window quickly.

    This exposes b/183641352
    """
    controlStatus = await ui_controller.closeExtendedControls(__EMPTY__)
    controlStatus = await ui_controller.showExtendedControls(__EMPTY__)
    controlStatus = await ui_controller.closeExtendedControls(__EMPTY__)
    assert controlStatus.visibilityChanged
