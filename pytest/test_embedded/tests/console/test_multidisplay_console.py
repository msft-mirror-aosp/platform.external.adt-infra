from pathlib import Path

import pytest
import logging
import random
import asyncio
import emu.console.emulator_connection

from aemu.proto.ui_controller_service_pb2 import PaneEntry, WindowPosition
from aemu.proto.ui_controller_service_pb2_grpc import UiControllerStub
from google.protobuf import empty_pb2

__EMPTY__ = empty_pb2.Empty()

@pytest.fixture
def ui_controller(service):
    yield service(UiControllerStub)


@pytest.mark.console
@pytest.mark.multidisplay
@pytest.mark.e2e
async def test_multidisplay_out_of_order_add_no_crash(avd, telnet, ui_controller):
    """Test adb emu multidisplay add 3  does not crash emulator"""

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

    out_of_order_add_result =await telnet.send("multidisplay add 3 720 1280 240 0")
    await asyncio.sleep(2)
    assert avd.is_alive();
    assert "OK" in out_of_order_add_result

    valid_del_result = await telnet.send("multidisplay del 3")
    await asyncio.sleep(2)
    assert avd.is_alive();
    assert "OK" in valid_del_result

