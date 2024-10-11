from pathlib import Path

import pytest
import logging
import random
import asyncio
import emu.console.emulator_connection

from grpc import RpcError, StatusCode

from aemu.proto.ui_controller_service_pb2 import PaneEntry, WindowPosition
from aemu.proto.ui_controller_service_pb2_grpc import UiControllerStub
from google.protobuf import empty_pb2
from emu.timing import eventually
from functools import partial
import re

__EMPTY__ = empty_pb2.Empty()


@pytest.fixture
async def ensure_multidisplay_service_ready(emulator_controller):
    max_retries = 5
    retry_delay = 1  # Initial delay in seconds

    for attempt in range(max_retries):
        try:
            await emulator_controller.getDisplayConfigurations(__EMPTY__)
            return  # Success, exit the loop
        except RpcError as exc_info:
            if exc_info.value.code() != StatusCode.UNAVAILABLE:
                raise  # Unexpected error, re-raise
        except Exception:
            raise  # Unexpected error, re-raise

        # Exponential backoff
        await asyncio.sleep(retry_delay)
        retry_delay *= 2  # Double the delay for the next attempt

    raise TimeoutError(
        f"Failed to get display configurations after {max_retries} attempts"
    )


@pytest.fixture
def ui_controller(service):
    yield service(UiControllerStub)


@pytest.mark.console
@pytest.mark.multidisplay
@pytest.mark.e2e
async def test_multidisplay_out_of_order_add_no_crash(
    avd, telnet, ui_controller, ensure_multidisplay_service_ready
):
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

    out_of_order_add_result = await telnet.send("multidisplay add 3 720 1280 240 0")
    await asyncio.sleep(2)
    assert avd.is_alive()
    assert "OK" in out_of_order_add_result

    valid_del_result = await telnet.send("multidisplay del 3")
    await asyncio.sleep(2)
    assert avd.is_alive()
    assert "OK" in valid_del_result


@pytest.mark.console
@pytest.mark.multidisplay
@pytest.mark.e2e
async def test_multidisplay_del_empty_no_crash(avd, ensure_multidisplay_service_ready):
    """Test adb emu multidisplay del does not crash emulator"""

    del_empty_result = await avd.adb.run(["emu", "multidisplay", "del"])
    await asyncio.sleep(3)
    assert avd.is_alive()


@pytest.mark.console
@pytest.mark.multidisplay
@pytest.mark.e2e
async def test_multidisplay_del_invalid_display_no_crash(
    avd, ensure_multidisplay_service_ready
):
    """Test adb emu multidisplay del invalidid does not crash emulator"""

    del_invalid_display_result = await avd.adb.run(["emu", "multidisplay", "del", "3"])
    await asyncio.sleep(3)
    assert avd.is_alive()


async def ensure_logical_displays(n, emu):
    # Return True if the emulator has 'n' logical displays.
    display_dump = await emu.adb.shell("dumpsys display", timeout=30)
    display_size_pattern = re.search("Logical Displays: size=([0-9]*).*", display_dump)
    if display_size_pattern is None:
        return False
    return display_size_pattern.groups()[0] == str(n)


@pytest.mark.multidisplay
@pytest.mark.fast
@pytest.mark.async_timeout(510)
async def test_add_multidisplay_from_telnet(
    avd, emulator_controller, telnet, ensure_multidisplay_service_ready
):
    await telnet.send("multidisplay add 1 1200 800 240 0")
    cfg = await emulator_controller.getDisplayConfigurations(__EMPTY__)

    n_displays = 2  # primary plus one secondary display.

    assert await eventually(
        partial(ensure_logical_displays, n_displays, avd), timeout=180
    ), "Wrong number of displays detected"

    assert cfg.displays[1].dpi == 240
    assert cfg.displays[1].width == 1200
    assert cfg.displays[1].height == 800


@pytest.mark.multidisplay
@pytest.mark.fast
@pytest.mark.async_timeout(510)
async def test_remove_multidisplay_from_telnet(
    avd, emulator_controller, telnet, ensure_multidisplay_service_ready
):
    await telnet.send("multidisplay add 1 1200 800 240 0")
    n_displays = 2  # primary plus one secondary display.
    assert await eventually(
        partial(ensure_logical_displays, n_displays, avd), timeout=180
    ), "Wrong number of displays detected"

    await telnet.send("multidisplay del 1")

    n_displays = 1  # since display is deleted

    assert await eventually(
        partial(ensure_logical_displays, n_displays, avd), timeout=180
    ), "Wrong number of displays detected"
