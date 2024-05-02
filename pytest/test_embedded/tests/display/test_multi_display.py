# Copyright 2020 The Android Open Source Project
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
import asyncio
import pytest
import re
from aemu.proto.emulator_controller_pb2 import (
    DisplayConfiguration,
    DisplayConfigurations,
    ImageFormat,
    Rotation,
)
from aemu.proto.emulator_controller_pb2_grpc import EmulatorControllerStub
from emu.emulator import Emulator
from emu.timing import eventually
from functools import partial
from google.protobuf import empty_pb2
from grpc import RpcError, StatusCode
from tests.test_utils import fmt_proto
from snaptool.snapshot import AsyncSnapshotService
from aemu.proto.snapshot_service_pb2_grpc import SnapshotServiceStub

_EMPTY_ = empty_pb2.Empty()


def contains(display: DisplayConfiguration, displays: [DisplayConfiguration]):
    logging.info("Checking if %s is in %s", display, displays)
    displays_by_ids = [d for d in displays if d.display == display.display]
    assert len(displays_by_ids) == 1
    display_by_id = displays_by_ids[0]
    assert display_by_id is not None
    assert display_by_id.width == display.width
    assert display_by_id.height == display.height
    assert display_by_id.dpi == display.dpi


@pytest.fixture
async def is_landscape(get_screenshot):
    image, _ = await get_screenshot(ImageFormat(width=320, height=200))
    logging.info("get_screenshot: %s", fmt_proto(image.format))
    return (
        image.format.rotation.rotation == Rotation.REVERSE_LANDSCAPE
        or image.format.rotation.rotation == Rotation.LANDSCAPE
    )


@pytest.fixture
async def no_displays(emulator_controller, adb_shell):
    """Fixture to make sure the emulator has no multi displays configured.

    Use this if you want to make sure the emulator has no secondary displays
    """
    logging.info("--> no_displays")
    await adb_shell("input keyevent KEYCODE_WAKEUP")
    await emulator_controller.setDisplayConfigurations(
        DisplayConfigurations(displays=[])
    )
    yield
    logging.info("<-- no_displays")
    await emulator_controller.setDisplayConfigurations(
        DisplayConfigurations(displays=[])
    )
    logging.info("=== finished no_displays")

@pytest.fixture
async def emu_snapshot_service(avd, service):
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


@pytest.mark.e2e
@pytest.mark.timeout_win(timeout=60)
@pytest.mark.graphics
@pytest.mark.multidisplay
async def test_multidisplay_none(avd, no_displays, emulator_controller, is_landscape):
    """Erasing displays leaves nothing behind."""
    if is_landscape:
        pytest.skip("Cannot run multi display tests in landscape mode.")

    cfg = await emulator_controller.setDisplayConfigurations(
        DisplayConfigurations(displays=[])
    )

    # We only have the default display
    assert len(cfg.displays) == 1


@pytest.mark.e2e
@pytest.mark.graphics
@pytest.mark.multidisplay
@pytest.mark.sanity
async def test_multidisplay_multiple(avd, no_displays, emulator_controller, is_landscape):
    """Adding a display should work."""
    if is_landscape:
        pytest.skip("Cannot run multi display tests in landscape mode.")

    cfg = await emulator_controller.setDisplayConfigurations(
        DisplayConfigurations(
            displays=[
                DisplayConfiguration(width=720, height=1280, dpi=213, display=2),
            ]
        )
    )

    assert len(cfg.displays) == 2
    assert cfg.displays[1].display == 2
    assert cfg.displays[1].dpi == 213
    assert cfg.displays[1].width == 720
    assert cfg.displays[1].height == 1280

@pytest.mark.e2e
@pytest.mark.graphics
@pytest.mark.multidisplay
@pytest.mark.sanity
@pytest.mark.async_timeout(510)
async def test_multiple_display_snapshot(avd, no_displays, emulator_controller, emu_snapshot_service,  is_landscape):
    """Snapshots on multiple display should work."""
    if is_landscape:
        pytest.skip("Cannot run multi display tests in landscape mode.")

    # add two additional displays
    resolutions = [(720, 1280), (1080, 1920)]
    displays = [
        DisplayConfiguration(width=x[0], height=x[1], dpi=213, display=idx + 1)
        for idx, x in enumerate(resolutions)
    ]
    to_set = DisplayConfigurations(displays=displays)
    cfg = await emulator_controller.setDisplayConfigurations(to_set)
    assert len(cfg.displays) == 3

    # take a snapshot of multiple displays
    assert await emu_snapshot_service.save("foo")
    snapshots = await emu_snapshot_service.lists()
    assert "foo" in [x.snapshot_id for x in snapshots]

    # change the display configuration, add just one additional display
    resolutions = [ (3840, 2160)]
    displays = [
        DisplayConfiguration(width=x[0], height=x[1], dpi=213, display=idx + 1)
        for idx, x in enumerate(resolutions)
    ]
    to_set = DisplayConfigurations(displays=displays)
    cfg = await emulator_controller.setDisplayConfigurations(to_set)
    assert len(cfg.displays) == 2

    # load the snapshot and check the number of displays.
    assert await emu_snapshot_service.load("foo")
    assert await avd.wait_for_boot(timeout=240)
    # there is no reliable way to detect it has reach home screen
    # so just wait long
    await asyncio.sleep(10)

    cfg2 = await emulator_controller.getDisplayConfigurations(_EMPTY_)
    assert len(cfg2.displays) == 3


@pytest.mark.e2e
@pytest.mark.graphics
@pytest.mark.multidisplay
async def test_multidisplay_multiple_error(
    avd, no_displays, emulator_controller, is_landscape
):
    """A failure should not modify the status."""
    if is_landscape:
        pytest.skip("Cannot run multi display tests in landscape mode.")

    cfg = await emulator_controller.setDisplayConfigurations(
        DisplayConfigurations(
            displays=[
                DisplayConfiguration(width=720, height=1280, dpi=213, display=2),
            ]
        )
    )

    # We should have the default display, and 1 other.
    assert len(cfg.displays) == 2

    # Incorrectly modifying a display configuration should fail and leave the existing one intact
    with pytest.raises(RpcError) as exc_info:
        cfg = await emulator_controller.setDisplayConfigurations(
            DisplayConfigurations(
                displays=[
                    DisplayConfiguration(
                        width=99720, height=991280, dpi=213, display=1
                    ),
                ]
            )
        )
    assert exc_info.value.code() == StatusCode.INVALID_ARGUMENT

    # The failure leaves the displays untouched.
    cfg = await emulator_controller.getDisplayConfigurations(_EMPTY_)
    assert len(cfg.displays) == 2
    assert cfg.displays[1].display == 2
    assert cfg.displays[1].dpi == 213
    assert cfg.displays[1].width == 720
    assert cfg.displays[1].height == 1280


@pytest.mark.e2e
@pytest.mark.graphics
@pytest.mark.multidisplay
@pytest.mark.fast
async def test_multidisplay_get_after_set(
    avd, no_displays, emulator_controller, is_landscape
):
    """Adding a display should work."""
    if is_landscape:
        pytest.skip("Cannot run multi display tests in landscape mode.")

    cfg = await emulator_controller.setDisplayConfigurations(
        DisplayConfigurations(
            displays=[
                DisplayConfiguration(width=720, height=1280, dpi=213, display=2),
            ]
        )
    )

    cfg2 = await emulator_controller.getDisplayConfigurations(_EMPTY_)
    assert cfg == cfg2


@pytest.mark.e2e
@pytest.mark.graphics
@pytest.mark.multidisplay
async def test_multidisplay_double_ids_error(
    avd, no_displays, emulator_controller, is_landscape
):
    """Adding the same display twice should result in an error."""
    if is_landscape:
        pytest.skip("Cannot run multi display tests in landscape mode.")

    with pytest.raises(RpcError) as exc_info:
        await emulator_controller.setDisplayConfigurations(
            DisplayConfigurations(
                displays=[
                    DisplayConfiguration(width=720, height=1280, dpi=213, display=2),
                    DisplayConfiguration(width=1080, height=1920, dpi=213, display=2),
                ]
            )
        )
    assert exc_info.value.code() == StatusCode.INVALID_ARGUMENT


@pytest.mark.e2e
@pytest.mark.graphics
@pytest.mark.multidisplay
@pytest.mark.fast
@pytest.mark.flaky  # b/322551553
async def test_multidisplay_can_configure_four(
    avd, no_displays, emulator_controller, is_landscape
):
    """This tests makes sure that a total of 4 displays can be configured.

    Adding 3 additional displays, should return a total of 4.
    """
    if is_landscape:
        pytest.skip("Cannot run multi display tests in landscape mode.")

    resolutions = [(720, 1280), (1080, 1920), (3840, 2160)]
    displays = [
        DisplayConfiguration(width=x[0], height=x[1], dpi=213, display=idx + 1)
        for idx, x in enumerate(resolutions)
    ]
    to_set = DisplayConfigurations(displays=displays)
    cfg = await emulator_controller.setDisplayConfigurations(to_set)

    logging.info(
        "setDisplayConfigurations:(%s) = %s", fmt_proto(to_set), fmt_proto(cfg)
    )

    # We have default screen, + the ones we added.
    assert len(cfg.displays) == len(displays) + 1

    # All screens have been made available.
    for display in displays:
        contains(display, cfg.displays)


@pytest.mark.e2e
@pytest.mark.graphics
@pytest.mark.multidisplay
async def test_multidisplay_add_should_not_remove(
    avd, no_displays, emulator_controller, is_landscape
):
    """This tests makes sure that a total of 4 displays can be configured.

    Adding 3 additional displays, should return a total of 4.
    """
    if is_landscape:
        pytest.skip("Cannot run multi display tests in landscape mode.")

    displays = [DisplayConfiguration(width=720, height=1280, dpi=213, display=2)]
    to_set = DisplayConfigurations(displays=displays)
    cfg = await emulator_controller.setDisplayConfigurations(to_set)
    logging.info(
        "setDisplayConfigurations:(%s) = %s", fmt_proto(to_set), fmt_proto(cfg)
    )

    # All screens have been made available.
    for display in displays:
        contains(display, cfg.displays)

    displays = [
        DisplayConfiguration(width=720, height=1280, dpi=213, display=1),
        DisplayConfiguration(width=720, height=1280, dpi=213, display=2),
    ]
    to_set = DisplayConfigurations(displays=displays)
    cfg = await emulator_controller.setDisplayConfigurations(to_set)

    logging.info(
        "setDisplayConfigurations:(%s) = %s", fmt_proto(to_set), fmt_proto(cfg)
    )

    # All screens have been made available.
    for display in displays:
        contains(display, cfg.displays)


@pytest.mark.e2e
@pytest.mark.graphics
@pytest.mark.multidisplay
async def test_multidisplay_error_too_many(
    avd, no_displays, emulator_controller, is_landscape
):
    """Adding too many displays should raise an exception."""
    if is_landscape:
        pytest.skip("Cannot run multi display tests in landscape mode.")

    resolutions = [(720, 1280), (1080, 1920), (3840, 2160), (900, 900)]
    displays = [
        DisplayConfiguration(width=x[0], height=x[1], dpi=213, display=idx + 1)
        for idx, x in enumerate(resolutions)
    ]
    with pytest.raises(RpcError):
        await emulator_controller.setDisplayConfigurations(
            DisplayConfigurations(displays=displays)
        )


@pytest.mark.graphics
@pytest.mark.multidisplay
@pytest.mark.fast
@pytest.mark.async_timeout(120)
async def test_disable_multidisplay(avd, is_landscape):
    """Ensure an app is moved to the primary display when multidisplay is disabled.

    Args:
        emulator (BaseEmulator): Fixture that gives access to the running emulator.
        is_landscape (bool): Fixture that indicates whether the emulator is in landscape orientation.
        emulator_controller (EmulatorControllerStub): An instance of the emulator controller fixture.

    Test UUID: d0114791-2781-45ee-b4fa-b496d767604e

    Test Steps:
        1. Configure the emulator to support multiple display resolutions.
        2. Launch a dummy app (e.g., calendar) on the current display.
        3. Disable multidisplay functionality
        4. confirm the dummy app moved to the primary display (Verify).
        5. Repeat the steps 2-4 for all display resolutions

    Verify:
        - Ensure that the secondary display is removed after disabling multidisplay.
        - Verify that the app running on the secondary display is correctly moved to the primary display.
    """
    if is_landscape:
        pytest.skip("Cannot run multi display tests in landscape mode.")

    emulator_controller = EmulatorControllerStub(avd.channel)

    # Displays configurations to be tested.
    resolutions = [(720, 1280), (1080, 1920)]
    displays = [
        DisplayConfiguration(width=x[0], height=x[1], dpi=213, display=idx + 1)
            for idx, x in enumerate(resolutions)
    ]

    async def disable_multidisplay():
        # Ensure the device has only one display
        cfg = await emulator_controller.setDisplayConfigurations(
            DisplayConfigurations(displays=[])
        )
        logging.info('Disabling multidisplay mode')
        assert len(cfg.displays) == 1
        return cfg

    async def enable_multidisplay(displays):
        # Set the display configuration according to `displays`
        to_set = DisplayConfigurations(displays=displays)
        logging.info('Enabling multidisplay mode')
        cfg = await emulator_controller.setDisplayConfigurations(to_set)
        return cfg

    async def get_display_id(package):
        # Get the display id where `package` is running
        windows_dump = await avd.adb.shell("dumpsys window", timeout=30)
        display_lines = re.search(f"Window.*{package}.*mDisplayId=([0-9]*)", windows_dump)
        return int(display_lines.groups()[0])

    dummy_pkg = "com.android.contacts"
    dummy_activity = f"{dummy_pkg}/.activities.PeopleActivity"

    # Make sure we start with the primary display only.
    cfg = await emulator_controller.getDisplayConfigurations(empty_pb2.Empty())
    if len(cfg.displays) > 1:
        await disable_multidisplay()

    for idx in range(len(resolutions)):

        # Enable multidisplay.
        await enable_multidisplay(displays)
        await asyncio.sleep(10)

        # Start app on current display.
        await avd.start_activity(dummy_activity, params=f"--display {idx + 1}")
        await asyncio.sleep(10)

        # Disable multidisplay.
        logging.info(f'Disable multidisplay while contacts app is on display {idx + 1}')
        cfg = await disable_multidisplay()
        await asyncio.sleep(10)

        # Verify if the app is present in the primary display.
        display_id = await get_display_id(dummy_pkg)
        assert display_id == 0, f"Contacts app was detected in display {display_id}"

        # Stop the app.
        await avd.stop_activity("com.android.contacts")
        await asyncio.sleep(5)
