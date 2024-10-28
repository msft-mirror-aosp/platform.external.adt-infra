from pathlib import Path

import pytest
import emu.console.emulator_connection
from emu.timing import eventually
from functools import partial

from emu.emulator import Emulator
from aemu.proto.snapshot_service_pb2_grpc import SnapshotServiceStub
from snaptool.snapshot import AsyncSnapshotService
from aemu.proto.screen_recording_service_pb2 import RecordingInfo
from aemu.proto.screen_recording_service_pb2_grpc import ScreenRecordingStub
from aemu.proto.emulator_controller_pb2 import PhoneCall, PhoneResponse
from aemu.proto.emulator_controller_pb2_grpc import EmulatorControllerStub
import logging
import asyncio


@pytest.mark.boot
@pytest.mark.console
@pytest.mark.fast
async def test_avd_canonical_path(avd, telnet):
    """Test adb emu avd path returns a canonical path"""
    expected_path = Path(
        avd.android_avd_home, f"{avd.configuration.name}.avd"
    ).absolute()
    path = await telnet.send("avd path")
    assert str(expected_path) in path


@pytest.mark.boot
@pytest.mark.console
@pytest.mark.fast
async def test_avd_snapshots_path_has_no_dots(telnet):
    """Exposes b/299320133, paths should be normalized."""
    path = await telnet.send("avd snapshotspath")
    assert ".." not in path[0]


@pytest.mark.boot
@pytest.mark.console
@pytest.mark.sanity
async def test_avd_tracing_is_mounted(avd, telnet):
    """Test adb shell ls /sys/kernel/tracing/trace_marker valid"""
    no_file = "No such file or directory"
    ls_file = await avd.adb.shell("ls /sys/kernel/tracing/trace_marker")
    if no_file in ls_file:
        ls_file = await avd.adb.shell("ls /sys/kernel/debug/tracing/trace_marker")
        assert no_file not in ls_file


def read_property_file(from_file) -> str:
    """Reads a property file and returns a dictionary of the key-value pairs.

    Args:
        from_file: The filename of the property file.

    Returns:
        A dictionary of the key-value pairs in the property file.
    """
    with open(from_file, "r", encoding="utf-8") as f:
        return dict([x.strip().split("=", 1) for x in f.readlines()])


@pytest.mark.boot
@pytest.mark.console
@pytest.mark.sanity
async def test_avd_dir_is_canonical_in_pid_xxx_ini(avd, telnet):
    """Test pid_xxx.ini contains canonical path for avd.dir

    example:
    avd.dir=/Users/me/.android/avd/x.avd
    """
    discovery = await telnet.send("avd discoverypath")
    pid_path = Path(discovery[0])
    assert (
        pid_path.exists()
    ), f"We expect the reported discovery path: {pid_path} to exist"

    props = read_property_file(pid_path)
    assert "avd.dir" in props, f"Did not find 'avd.dir' in {props}"

    expected_path = Path(
        avd.android_avd_home, f"{avd.configuration.name}.avd"
    ).absolute()
    assert props["avd.dir"] == str(expected_path)


@pytest.mark.sanity
async def test_emulator_help_console_command(avd, telnet):
    help_commands = [
        "help-verbose",
        "ping",
        "avd",
        "crash",
        "fold",
        "unfold",
        "sms",
        "sensor",
        "multidisplay",
        "rotate",
        "debug",
        "grpc",
        "screenrecord",
        "network",
        "event",
        "power",
        "restart",
        "geo",
        "gsm",
        "posture",
        "kill",
        "restart",
    ]
    result = await telnet.send("help")

    for help_command in help_commands:
        assert help_command in result, "console help command failed"


@pytest.mark.sanity
async def test_emulator_exit_console_command(telnet):
    try:
        await telnet.send("exit")
        assert False, "Emulator client connection did not close as expected"
    except emu.console.emulator_connection.EmulatorClientEOF:
        pass  # Connection closed successfully


@pytest.mark.sanity
async def test_telnet_will_reconnect_after_exit(telnet):
    try:
        await telnet.send("exit")
        assert False, "Emulator client connection did not close as expected"
    except emu.console.emulator_connection.EmulatorClientEOF:
        hello = await telnet.send("ping")
        assert hello == ["I am alive!", "OK"]


@pytest.fixture
async def avd_factory(emulator):
    """Create and launch AVDs with the same configuration as the default AVD.

    Args:
        emulator (BaseEmulator): Fixture that gives access to a configured emulator.

    Note: Each time the fixture is called, a copy of the default AVD
          is created and launched.

    Note: The AVDs are named after the default AVD, plus '_<count>'.
          At the test teardown, all AVDs created are deleted.
    """
    avds = []

    async def _create_avd_from():
        tag = emulator.configuration.hardware["tag.id"]
        abi = emulator.configuration.hardware["abi"]
        api = emulator.configuration.hardware["api"]
        name = emulator.configuration.name + "_" + str(len(avds) + 1)
        config = {"tag.id": tag, "abi": abi, "api": api, "AvdId": name}
        avd = Emulator(
            android_home=emulator.android_home,
            android_avd_home=emulator.android_avd_home,
            exe=emulator.exe,
            avd_config=config,
            log_id=f"emu-{len(avds)}",
            fetcher=emulator.fetcher,
        )
        avds.append(avd)
        await avd.launch(["-no-snapshot-save"])
        await avd.wait_for_boot()
        return avd

    yield _create_avd_from

    for avd in avds:
        if avd.is_alive():
            await avd.stop()
        avd.delete()


@pytest.mark.sanity
@pytest.mark.async_timeout(2500)
async def test_concurrent_avds(avd, avd_factory, tmp_path):
    """Ensure concurrent AVDs work.

    Args:
        avd (BaseEmulator): Fixture that gives access to a booted emulator.
        avd_factory (callback): Fixture that creates and launches an AVD
            with the same configuration as the default AVD.
        tmp_path: Fixture that returns a temporary directory path

    Test UUID: 411183cc-b115-4df9-be0a-397e8ea81d60

    Test steps:
        1. Launch an emulator AVD (AVD1).
        2. Create and launch another AVD (AVD2).
        3. Launch YouTube on both the AVDs. (Verify 1)
        4. Take and load snapshots from both AVDs. (Verify 2)
        5. Perform screen recording on both AVDs. (Verify 3)
        6. Make calls to each AVD. (Verify 4)

    Verify:
        1. YouTube is launched without any issues.
        2. Snapshots are saved and loaded without any issues.
        3. Screen video are recorded and can be played without any issues.
        4. Call are received on the AVD UI without any issues.
    """
    avd1 = avd  # AVD1 represents the current active AVD, to optimize the test duration.
    avd2 = await avd_factory()
    channel1 = avd1.description.get_async_grpc_channel([("emulator.security", "token")])
    channel2 = avd2.description.get_async_grpc_channel([("emulator.security", "token")])

    # Ensure Youtube launches on both AVDs.
    youtube_pkg = "com.google.android.youtube"
    youtube_activity = (
        "com.google.android.apps.youtube.app.watchwhile.WatchWhileActivity"
    )
    assert await avd1.start_activity(
        "/".join((youtube_pkg, youtube_activity)), params="-W"
    ), "Couldn't launch Youtube on AVD1"
    assert await avd2.start_activity(
        "/".join((youtube_pkg, youtube_activity)), params="-W"
    ), "Couldn't launch Youtube on AVD2"

    # Ensure snapshots are saved and loaded on both AVDs.
    snapshot_services = [
        AsyncSnapshotService(snapshot_service=SnapshotServiceStub(channel1)),
        AsyncSnapshotService(snapshot_service=SnapshotServiceStub(channel2)),
    ]

    for i, snapshot_service in enumerate(snapshot_services):
        snapshot_name = tmp_path.stem + "_" + str(i + 1)
        assert await snapshot_service.save(snapshot_name)
        snapshots = await snapshot_service.lists()
        assert snapshot_name in [
            x.snapshot_id for x in snapshots
        ], f"Couldn't save a snapshot on AVD {i+1}"
        assert await snapshot_service.delete(snapshot_name)

    # Ensure screen recording work on both AVDs.
    screen_services = [ScreenRecordingStub(channel1), ScreenRecordingStub(channel2)]

    for i, screen_service in enumerate(screen_services):
        sample_webm = tmp_path / f"sample_{i}.webm"
        info = RecordingInfo(width=120, height=120, file_name=str(sample_webm))

        logging.info(f"Starting the recording: {info} (AVD {i + 1})")
        await screen_service.StartRecording(info)
        await asyncio.sleep(5)

        logging.info(f"Stopping the recording: {info} (AVD {i + 1})")
        await screen_service.StopRecording(info)

        assert sample_webm.exists()
        assert (
            sample_webm.stat().st_size > 10240
        ), f"We should have recorded a series of frames from AVD {i + 1}"

    # Ensure both AVDs can receive calls.
    phone_call = PhoneCall(operation=PhoneCall.InitCall, number="1234567890")
    emulator_controllers = [
        EmulatorControllerStub(channel1),
        EmulatorControllerStub(channel2),
    ]

    async def check_phone_response(controller):
        phone_response = await controller.sendPhone(phone_call)
        return phone_response.response == PhoneResponse.OK

    for controller in emulator_controllers:
        phone_response = await controller.sendPhone(phone_call)
        assert await eventually(
            partial(check_phone_response, controller)
        ), f"Phone response is {phone_response.response}, expected {PhoneResponse.OK}"


@pytest.mark.fast
async def test_avd_commands(avd, telnet):
    avd_commands = [
        "avd start",
        "avd stop",
        "avd status",
        "avd heartbeat",
        "avd name",
        "avd id",
        "avd resume",
        "avd pause",
        "avd resume",
        "avd windowtype",
        "avd path",
        "avd discoverypath",
        "avd snapshotspath",
    ]
    avd_result = await telnet.send("help avd")
    for avd_command in avd_commands:
        assert any([avd_command in item.strip() for item in avd_result])

    response = await telnet.send("avd name")
    assert response is not None and response != ""
    response = await telnet.send("avd status")
    assert any(["running" in element for element in response])
    response = await telnet.send("avd path")
    assert any([".avd" in element for element in response])
    response = await telnet.send("avd discoverypath")
    assert any([".ini" in element for element in response])
    response = await telnet.send("avd snapshotspath")
    assert any(["snapshots" in element for element in response])
