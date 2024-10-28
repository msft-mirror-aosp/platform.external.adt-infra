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
import json
from aemu.proto.emulator_controller_pb2 import (
    DisplayConfiguration,
    DisplayConfigurations,
    ImageFormat,
    Rotation,
)
from aemu.proto.emulator_controller_pb2_grpc import EmulatorControllerStub
from emu.emulator import Emulator
from emu.timing import eventually, wait_until
from functools import partial
from google.protobuf import empty_pb2
from grpc import RpcError, StatusCode
from tests.test_utils import fmt_proto, decode_qrcodes
from snaptool.snapshot import AsyncSnapshotService
from aemu.proto.snapshot_service_pb2_grpc import SnapshotServiceStub
from aemu.proto.emulator_controller_pb2 import KeyboardEvent
from tests.test_utils import click_button, get_window_dump
import lxml.etree as ET

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
async def ensure_multidisplay_service_ready(emulator_controller):
    max_retries = 5
    retry_delay = 1  # Initial delay in seconds

    for attempt in range(max_retries):
        try:
            status = await emulator_controller.getStatus(_EMPTY_)
            if (
                "multidisplay" in status.guestConfig
                and status.guestConfig["multidisplay"] == "available"
            ):
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
async def no_displays(
    ensure_multidisplay_service_ready, emulator_controller, adb_shell
):
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


@pytest.mark.multidisplay
@pytest.mark.async_timeout(1080)
async def test_multidisplay_none(
    ensure_multidisplay_service_ready,
    avd,
    no_displays,
    emulator_controller,
    is_landscape,
):
    """Erasing displays leaves nothing behind."""
    if is_landscape:
        pytest.skip("Cannot run multi display tests in landscape mode.")

    cfg = await emulator_controller.setDisplayConfigurations(
        DisplayConfigurations(displays=[])
    )

    # We only have the default display
    assert len(cfg.displays) == 1


@pytest.mark.multidisplay
@pytest.mark.sanity
@pytest.mark.async_timeout(1080)
async def test_multidisplay_multiple(
    ensure_multidisplay_service_ready,
    avd,
    no_displays,
    emulator_controller,
    is_landscape,
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

    assert len(cfg.displays) == 2
    assert cfg.displays[1].display == 2
    assert cfg.displays[1].dpi == 213
    assert cfg.displays[1].width == 720
    assert cfg.displays[1].height == 1280


@pytest.mark.multidisplay
@pytest.mark.sanity
@pytest.mark.async_timeout(1080)
async def test_multiple_display_snapshot(
    ensure_multidisplay_service_ready,
    avd,
    no_displays,
    emulator_controller,
    emu_snapshot_service,
    is_landscape,
):
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
    resolutions = [(3840, 2160)]
    displays = [
        DisplayConfiguration(width=x[0], height=x[1], dpi=213, display=idx + 1)
        for idx, x in enumerate(resolutions)
    ]
    to_set = DisplayConfigurations(displays=displays)
    cfg = await emulator_controller.setDisplayConfigurations(to_set)
    assert len(cfg.displays) == 2

    # load the snapshot and check the number of displays.
    assert await emu_snapshot_service.load("foo")
    # 99 percentile boots in less than 2 minutes.
    # go/stats/#report_id=Emulator%2FBootTime%2F7-day%20BootTime
    assert await avd.wait_for_boot(timeout=120)
    # there is no reliable way to detect it has reach home screen
    # so just wait long
    await asyncio.sleep(10)

    cfg2 = await emulator_controller.getDisplayConfigurations(_EMPTY_)
    assert len(cfg2.displays) == 3


@pytest.mark.multidisplay
@pytest.mark.async_timeout(1080)
async def test_multidisplay_multiple_error(
    ensure_multidisplay_service_ready,
    avd,
    no_displays,
    emulator_controller,
    is_landscape,
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


@pytest.mark.multidisplay
@pytest.mark.async_timeout(1080)
async def test_multidisplay_get_after_set(
    ensure_multidisplay_service_ready,
    avd,
    no_displays,
    emulator_controller,
    is_landscape,
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


@pytest.mark.multidisplay
@pytest.mark.async_timeout(1080)
async def test_multidisplay_double_ids_error(
    ensure_multidisplay_service_ready,
    avd,
    no_displays,
    emulator_controller,
    is_landscape,
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


@pytest.mark.multidisplay
@pytest.mark.flaky(reruns=0)  # b/322551553
async def test_multidisplay_can_configure_four(
    ensure_multidisplay_service_ready,
    avd,
    no_displays,
    emulator_controller,
    is_landscape,
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


@pytest.mark.multidisplay
@pytest.mark.async_timeout(1080)
async def test_multidisplay_add_should_not_remove(
    ensure_multidisplay_service_ready,
    avd,
    no_displays,
    emulator_controller,
    is_landscape,
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


@pytest.mark.multidisplay
@pytest.mark.async_timeout(1080)
async def test_multidisplay_error_too_many(
    ensure_multidisplay_service_ready,
    avd,
    no_displays,
    emulator_controller,
    is_landscape,
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


async def start_on_display(avd, activity, id, params=""):
    """Start an activity on a given display
    Args:
        avd (BaseEmulator): Running emulator.
        activity (str): Activity name
        id (int): ID of the target display
        params (str): Activity extra params. By default, "".
    Returns:
        True if the activity started successfully, False otherwise.
    """
    return await avd.start_activity(activity, params=params + f" --display {id}")


async def get_package_display_id(avd, package):
    """Get the ID of the display where 'package' is running.
    Args:
        avd (BaseEmulator): Running emulator.
        package (str): package name
    Returns:
        The Display ID (int) where the package is running.
        None if the package is not present in the window system dump.
    """
    windows_dump = await avd.adb.shell("dumpsys window", timeout=60)
    display_lines = re.search(f"Window.*{package}.*mDisplayId=([0-9]*)", windows_dump)
    if display_lines is None:
        return None
    return int(display_lines.groups()[0])


async def get_displays_ids(avd):
    """Retrieve the IDs of all displays
    Args:
        avd (BaseEmulator): Running emulator.
    Returns:
        list[int]: The list of display IDs.
                   Return None if there are no displays avaiable or if
                   there is a single display.
    """
    windows_dump = await avd.adb.shell("dumpsys window", timeout=60)
    display_ids = re.findall("displayId=([0-9]+)", windows_dump)
    if display_ids is None:
        return None
    display_ids_list = sorted(set(display_ids))
    if len(display_ids_list) == 1:
        return None
    return [int(id_) for id_ in display_ids_list]


@pytest.mark.multidisplay
@pytest.mark.fast
@pytest.mark.async_timeout(1080)
async def test_disable_multidisplay(
    ensure_multidisplay_service_ready,
    avd,
    no_displays,
    is_landscape,
    emulator_controller,
):
    """Ensure an app is moved to the primary display when multidisplay is disabled.

    Args:
        avd (BaseEmulator): Fixture that gives access to the running emulator.
        no_displays (callable): Fixture to make sure the emulator has no multi displays configured.
        is_landscape (bool): Fixture that indicates whether the emulator is in landscape orientation.
        emulator_controller (EmulatorControllerStub): An instance of the emulator controller fixture.

    Test UUID: d0114791-2781-45ee-b4fa-b496d767604e

    Test Steps:
        1. Configure multiple display resolutions.
        2. Launch the animation APK on the current display.
        3. Disable multidisplay functionality
        4. Confirm the animation APK moved to the primary display (Verify).
        5. Repeat the steps 2-4 for all display resolutions

    Verify:
        - Ensure that the secondary display is removed after disabling multidisplay.
        - Verify that the app running on the secondary display is correctly moved to the primary display.
    """
    if is_landscape:
        pytest.skip("Cannot run multi display tests in landscape mode.")

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
        logging.info("Disabling multidisplay mode")
        assert len(cfg.displays) == 1
        return cfg

    async def enable_multidisplay(displays):
        # Set the display configuration from 'displays'.
        to_set = DisplayConfigurations(displays=displays)
        logging.info("Enabling multidisplay mode")
        cfg = await emulator_controller.setDisplayConfigurations(to_set)
        return cfg

    async def app_is_on_primary_display(pkg):
        # Return True if 'pkg' is detected on the primary display.
        display_id = await get_package_display_id(avd, pkg)
        return display_id == 0

    dummy_pkg = "com.google.AnimateBox"
    dummy_activity = f"{dummy_pkg}/com.google.emu.MainActivity"
    pkg_name = dummy_pkg.split(".")[-1]
    await avd.stop_activity(dummy_pkg)

    for i in range(len(resolutions)):

        # Enable multidisplay.
        await enable_multidisplay(displays)
        await asyncio.sleep(20)

        # Get the current displays list.
        assert await eventually(
            partial(get_displays_ids, avd), timeout=60
        ), "Couldn't retrieve the displays Ids"
        ids = await get_displays_ids(avd)

        # Start app on the display 'ids[i + 1]'.
        assert await eventually(
            partial(start_on_display, avd, dummy_activity, ids[i + 1]), timeout=60
        ), f"Couldn't launch package '{pkg_name}' on display {ids[i + 1]}"

        # Disable multidisplay.
        logging.info(
            f"Disable multidisplay while app {pkg_name} is on display {ids[i + 1]}"
        )
        await disable_multidisplay()

        # Verify if the app is present in the primary display.
        assert await eventually(
            partial(app_is_on_primary_display, dummy_pkg)
        ), f"App {pkg_name} was not found on display 0"

        # Stop the app.
        await avd.stop_activity(dummy_pkg)


@pytest.mark.multidisplay
@pytest.mark.fast
@pytest.mark.async_timeout(510)
async def test_add_multidisplay_from_config(emulator, tmp_path):
    """Adding displays from config file should work

    Args:
        emulator (BaseEmulator): Fixture that gives access to the running emulator.
        tmp_path (Path): Fixture that provides a temporary working folder.

    Test UUID: ea5ede9a-8cdf-4e56-bae1-1b56c2d7ae71

    Test Steps:
        1. Create an AVD with two secondary displays.
        2. Launch a new emulator based on the newly created AVD (Verify).

    Verify:
        Three logical displays should appear in the emulator display dump.
    """
    # Avd configuration containing two secondary displays.
    config = {
        "abi": emulator.configuration.hardware.get("abi"),
        "api": emulator.configuration.hardware.get("api"),
        "tag.id": emulator.configuration.hardware.get("tag.id"),
        "hw.display1.width": 800,
        "hw.display1.height": 1200,
        "hw.display1.density": 320,
        "hw.display1.xOffset": -1,
        "hw.display1.yOffset": -1,
        "hw.display1.flag": 0,
        "hw.display2.width": 800,
        "hw.display2.height": 1200,
        "hw.display2.density": 320,
        "hw.display2.xOffset": -1,
        "hw.display2.yOffset": -1,
        "hw.display2.flag": 0,
    }

    n_displays = 3  # primary plus two secondary displays.

    # Launch the emulator with the specificed multidisplay configuration.
    logging.info("Launching emulator ...")
    myflags = ["-no-snapshot-save"]
    emu = Emulator(
        android_home=emulator.android_home,
        android_avd_home=tmp_path,
        exe=emulator.exe,
        avd_config=config,
        fetcher=emulator.fetcher,
        log_id="emu-0",
    )
    await emu.launch(flags=myflags)

    # 99 percentile boots in less than 2 minutes.
    # go/stats/#report_id=Emulator%2FBootTime%2F7-day%20BootTime
    await emu.wait_for_boot(timeout=120)

    async def ensure_logical_displays(n, emu):
        # Return True if the emulator has 'n' logical displays.
        display_dump = await emu.adb.shell("dumpsys display", timeout=30)
        display_size_pattern = re.search(
            "Logical Displays: size=([0-9]*).*", display_dump
        )
        if display_size_pattern is None:
            return False
        return display_size_pattern.groups()[0] == str(n)

    assert await eventually(
        partial(ensure_logical_displays, n_displays, emu), timeout=180
    ), "Wrong number of displays detected"

    await emu.stop()


async def get_focused_task(avd, id):
    """Retrieve the name of the top focused task on display <id>"""
    task = await avd.adb.shell("dumpsys window displays")
    match = re.search(
        f"displayId={id}.*?mPreferredTopFocusableRootTask=(Task{{[^}}]*}})", task
    )
    if match is None:
        return None
    return match.groups()[0]


async def assert_focused_task_of_display(display_id, task, avd):
    """Return True if the focused task on display <id> contains the string <task>"""
    focused_task = await get_focused_task(avd, display_id)
    if focused_task is None:
        return False
    return task in focused_task


async def assert_focused_task_has_type(expected_type, display_id, avd):
    """Return True if the focused task on display <id> has type <expected_type>"""
    focused_task = await get_focused_task(avd, display_id)
    if focused_task is None:
        return False
    type = re.search("type=(.*)}", focused_task).groups()[0]
    if type is None or type != expected_type:
        return False
    return True


async def get_multidisplays_ids(avd):
    """Wait until two or more displays are configured and return the displays IDs
    Returns:
        list[int]: List of displays IDs
    Raises:
        asyncio.TimeoutError: If multiple displays are't configured.
    """

    async def _get_displays_ids(avd, output_list):
        ids = await get_displays_ids(avd)
        if ids is None:
            return False
        output_list.append(ids)
        return True

    ids = []
    assert await eventually(
        partial(_get_displays_ids, avd, ids)
    ), "Couldn't enable multidisplay"
    return ids[0]


@pytest.mark.multidisplay
@pytest.mark.async_timeout(1080)
async def test_multidisplay_controls(
    ensure_multidisplay_service_ready, avd, no_displays, emulator_controller
):
    """Verify the Home and Back controls work on primary and secondary displays.
    Args:
        avd (BaseEmulator): Fixture that gives access to the running emulator.
        no_displays (callable): Fixture that ensures the emulator has a single display.
        emulator_controller (EmulatorControllerStub): Emulator controller fixture.
    Steps:
        1. Attach a secondary display.
        2. Launch two random activities on each display.
        3. Click on the Back and Home buttons on the primary display.(Verify 1)
        4. Click on the Back and Home buttons on the secondary display.(Verify 2)
    Verification:
        1. Buttons work as intended on primary display. Secondary display is not affected.
        2. Buttons work as intended on secondary display. Primary display is not affected.
    """

    async def keypress(key):
        """Send the keypress 'key' event."""
        logging.info("Sending %s key", key)
        await emulator_controller.sendKey(
            KeyboardEvent(key=key, eventType=KeyboardEvent.keypress)
        )
        await asyncio.sleep(1)

    async def test_display_controls(
        main_display_id,
        main_display_activity1,
        second_display_id,
        second_display_focused_activity,
    ):
        """Test the Back and Home controls of a particular (main) display.
           Make sure the secondary display is not affected by the key events.
        Args:
            main_display_id (int): The ID of the main display being tested.
            main_display_activity1 (str): Name of the activity on the main display
                                          launched before the focused activity.
            second_display_id (int): The ID of the secondary display
            second_display_focused_activity (str): Name of the top focused activity
                                                   on the secondary display.
        Notes:
            Two running activies are assumed on the main display, acitivies 1 and 2,
            where activity 2 is the top focused activity. When pressing the Back and
            Home buttons, it makes sure activity 1 and the Home screen, respectively,
            appear on the main display being tested.
        """
        logging.info(f"Testing the controls of display {main_display_id}")

        # Press the Back button and verify the first task of the main display appears
        await keypress("GoBack")
        task1_name = main_display_activity1.split("/")[0]
        assert await eventually(
            partial(assert_focused_task_of_display, main_display_id, task1_name, avd)
        ), (
            f"The task '{task1_name}' didn't appear on display {main_display_id}"
            + " after pressing the Back button."
        )

        # Press the Home button and verify the Home screen appears on the main display
        await keypress("GoHome")
        assert await eventually(
            partial(assert_focused_task_has_type, "home", main_display_id, avd)
        ), f"The Home screen didn't appear on display {main_display_id}"

        # Make sure the secondary display isn't affected by the key events
        second_display_focused_task = second_display_focused_activity.split("/")[0]
        assert await eventually(
            partial(
                assert_focused_task_of_display,
                second_display_id,
                second_display_focused_task,
                avd,
            )
        ), (
            f"The focused task of display {second_display_id} changed "
            "after pressing the Back and Home keys."
        )

    # Attach a 720x1280 secondary display
    logging.info("Attaching a secondary display")
    configurations = DisplayConfigurations(
        displays=[DisplayConfiguration(width=720, height=1280, dpi=213, display=1)]
    )
    await emulator_controller.setDisplayConfigurations(configurations)
    display1, display2 = await get_multidisplays_ids(avd)

    # Define the activities
    display1_activity1 = (
        "com.google.android.apps.messaging/.ui.ConversationListActivity"
    )
    display1_activity2 = "com.android.chrome/com.google.android.apps.chrome.Main"

    display2_activity1 = "com.android.dialer/com.android.dialer.main.impl.MainActivity"
    display2_activity2 = (
        "com.google.android.youtube/"
        + "com.google.android.apps.youtube.app.watchwhile.WatchWhileActivity"
    )

    # Launch activity 1 of display 2
    await start_on_display(avd, display2_activity1, display2, params="-W")
    # Launch activies 1 and 2 of display 1
    await start_on_display(avd, display1_activity1, display1, params="-W")
    await start_on_display(avd, display1_activity2, display1, params="-W")

    # Test the controls of display 1
    await test_display_controls(
        display1, display1_activity1, display2, display2_activity1
    )

    # Relaunch activity 1 of display 1
    await start_on_display(avd, display1_activity1, display1, params="-W")

    # Launch activity 2 of display 2 (switch focus to display 2)
    await start_on_display(avd, display2_activity2, display2, params="-W")

    # Test the controls of display 2
    await test_display_controls(
        display2, display2_activity1, display1, display1_activity1
    )


@pytest.mark.multidisplay
@pytest.mark.fast
@pytest.mark.async_timeout(1080)
@pytest.mark.skipos("mac", "reason: screenrecord user permission should be given.")
@pytest.mark.skipos("m1", "reason: screenrecord user permission should be given.")
async def test_multidisplay_video_playback(
    ensure_multidisplay_service_ready,
    avd,
    no_displays,
    emulator_controller,
    qrcodes_mp4,
):
    """Verify video can be played in secondary display without any rendering issues.

    Args:
        avd (BaseEmulator): Fixture that gives access to the running emulator.
        no_displays (callable): Fixture that ensures the emulator has a single display.
        emulator_controller (EmulatorControllerStub): Emulator controller fixture.
        qrcodes_mp4 (Qrcodes): Gives access to the Qrcodes mp4 video fixture.

    Steps:
        1. Launch an AVD.
        2. Attach a secondary display.
        3. Launch the default player and play the sample video containing the QR codes
           on the secondary display. (Verify 1)

    Verification:
        1. The video is played without any rendering issues, observed from successfully
           decoding the video QR codes through a series of screenshots of the sample video.

    Notes:
        The Screenshots are taken using Pillow, since the screenshots from the emulator
        controller don't include the secondary display.
    """

    async def assert_secondary_display_playback(sec_display):
        """Make sure the test video on <sec_display> contains all QR codes' payloads"""
        await qrcodes_mp4.play(sec_display)
        return await decode_qrcodes(qrcodes_mp4.payloads)

    # Attach a secondary display
    logging.info("Attaching a secondary display")
    configurations = DisplayConfigurations(
        displays=[DisplayConfiguration(width=1080, height=1920, dpi=213, display=1)]
    )
    await emulator_controller.setDisplayConfigurations(configurations)
    _, sec_display = await get_multidisplays_ids(avd)

    # Make sure the qrcodes video plays and is decoded correctly.
    assert await wait_until(
        partial(assert_secondary_display_playback, sec_display), timeout=120
    ), "Couldn't play the test video on the secondary display."


@pytest.mark.multidisplay
@pytest.mark.fast
@pytest.mark.async_timeout(1080)
async def test_multidisplay_avd_features_work(avd, no_displays, emulator_controller):
    """Verify AVD specific features such as app. shortcut work correctly.

    Notes:
        Test requires API 31+.

    Args:
        avd (BaseEmulator): Fixture that gives access to the running emulator.
        no_displays (callable): Fixture that ensures the emulator has a single display.
        emulator_controller (EmulatorControllerStub): Emulator controller fixture.

    Test Steps:
        1. Launch a new AVD.
        2. Attach a secondary display.
        3. Click on the apps. list icon in the secondary display.
        4. Long-click any app. whose shortcut can be added, such as Contacts.
        5. Click 'Add to home screen'.i

    Verification: App shortcut is added to secondary display only.
    """
    api = await avd.api_level()
    if api <= 31:
        pytest.skip(reason="Requires api level > 31!")

    # Attach a secondary display.
    logging.info("Attaching a secondary display")
    configurations = DisplayConfigurations(
        displays=[DisplayConfiguration(width=720, height=1280, dpi=213, display=1)]
    )
    cfg = await emulator_controller.setDisplayConfigurations(configurations)
    main_display_id, secondary_display_id = await get_multidisplays_ids(avd)

    # Tap the 'apps list' icon.
    assert await click_button(
        avd,
        resource_id="com.google.android.apps.nexuslauncher:id/all_apps_button",
        display_id=secondary_display_id,
    ), "Couldn't open the Apps list."
    await asyncio.sleep(2)

    # Long-tap 'shortcut_app' to open the detailed options menu.
    shortcut_app = "Contacts"
    assert await click_button(
        avd,
        text=shortcut_app,
        resource_id="com.google.android.apps.nexuslauncher:id/icon",
        parent_resource_id="com.google.android.apps.nexuslauncher:id/apps_list_view",
        display_id=secondary_display_id,
        long_click=True,
    ), f"Couldn't open '{shortcut_app}' short menu."

    # Tap 'Add to home screen'.
    await asyncio.sleep(2)
    assert await click_button(
        avd,
        text="Add to home screen" if api >= 34 else None,
        content_desc="Add to home screen" if api < 34 else None,
        display_id=secondary_display_id,
    ), f"Couldn't click 'Add to home screen' button."

    # Verify the shortcut is created in the secondary display's home screen.
    async def app_shorcut_in_secondary_display():
        window_dump = await get_window_dump(avd)
        xml_hierarchy = ET.fromstring(window_dump.encode("UTF-8"))
        # Check if we are really in display 2
        display2_bounds = xml_hierarchy.find("node").get("bounds")
        display2 = cfg.displays[1]
        assert display2_bounds == f"[0,0][{display2.width},{display2.height}]"
        # Verify app shortcut exists in the xml hierarchy
        workspace_id = "com.google.android.apps.nexuslauncher:id/workspace_grid"
        shortcut = xml_hierarchy.xpath(
            f"//node[@resource-id='{workspace_id}']//node[@text='{shortcut_app}']"
        )
        assert len(shortcut) == 1, "Couldn't detect the app shortcut in display 2."

    # Verify the main display's home screen has not the app shortcut.
    async def app_shorcut_not_in_main_display():
        window_dump = await get_window_dump(avd)
        # Tap display 1 to change focus
        display1 = cfg.displays[0]
        await avd.adb.shell(
            f"input -d {main_display_id} tap {display1.width/2} {display1.height/2}"
        )
        # Confirm we are in display 1
        window_dump = await get_window_dump(avd)
        xml_hierarchy = ET.fromstring(window_dump.encode("UTF-8"))
        display1_bounds = xml_hierarchy.find("node").get("bounds")
        assert (
            display1_bounds == f"[0,0][{display1.width},{display1.height}]"
        ), "Couldn't change focus to the primary display"
        assert (
            shortcut_app not in xml_hierarchy
        ), f"A shortcut for '{shortcut_app}' was found in the main display."

    await app_shorcut_in_secondary_display()
    await app_shorcut_not_in_main_display()
