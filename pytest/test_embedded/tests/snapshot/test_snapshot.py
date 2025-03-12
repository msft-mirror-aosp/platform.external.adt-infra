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

import asyncio
import re
import os
import tarfile
import logging

import pytest
from aemu.proto.snapshot_service_pb2_grpc import SnapshotServiceStub
from snaptool.snapshot import AsyncSnapshotService
from emu.timing import eventually
from functools import partial


@pytest.fixture
async def snapshot_service(avd, service):
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
        if entry.snapshot_id != "default_boot":
            await snap.delete(entry.snapshot_id)


@pytest.mark.snapshot
@pytest.mark.skipos("win", "reason: b/305017763 - error at setup.")
async def test_snapshot_cannot_load_unknown_snapshot(snapshot_service):
    assert not await snapshot_service.load("foo")


@pytest.mark.snapshot
async def test_snapshot_can_save_and_load_through_service(snapshot_service):
    assert await snapshot_service.save("foo")
    snapshots = await snapshot_service.lists()
    assert "foo" in [x.snapshot_id for x in snapshots]
    assert await snapshot_service.load("foo")


@pytest.mark.snapshot
@pytest.mark.sanity
@pytest.mark.fast
async def test_snapshot_delete_removes(snapshot_service):
    assert await snapshot_service.save("foo")
    snapshots = await snapshot_service.lists()
    assert "foo" in [x.snapshot_id for x in snapshots]
    assert await snapshot_service.delete("foo")
    snapshots = await snapshot_service.lists()
    assert "foo" not in [x.snapshot_id for x in snapshots]


@pytest.mark.skipos("all")
@pytest.mark.snapshot
async def test_snapshot_pull_gets_a_tar(snapshot_service, tmpdir):
    path = str(tmpdir.realpath())  # Needed for py2 compatibility
    assert await snapshot_service.save("foo")
    assert await snapshot_service.pull("foo", path)

    # Let's make sure the tarfile is valid..
    tar = tarfile.open(os.path.join(path, "foo.tar"))
    assert tar.getmembers()


@pytest.mark.sanity
@pytest.mark.snapshot
async def test_snapshot_can_restore_a_pulled_snapshot(snapshot_service, tmpdir):
    path = str(tmpdir.realpath())  # Needed for py2 compatibility
    assert await snapshot_service.save("foo")
    assert await snapshot_service.pull("foo", path)
    assert await snapshot_service.delete("foo")
    snapshots = await snapshot_service.lists()
    assert "foo" not in [x.snapshot_id for x in snapshots]
    assert await snapshot_service.push(os.path.join(path, "foo.tar"))
    snapshots = await snapshot_service.lists()
    assert "foo" in [x.snapshot_id for x in snapshots]
    assert await snapshot_service.load("foo")


@pytest.mark.snapshot
@pytest.mark.sanity
@pytest.mark.async_timeout(240)
async def test_app_launch_after_snapshot_load(avd, snapshot_service, animation_app):
    assert await snapshot_service.save("foo")
    snapshots = await snapshot_service.lists()
    assert "foo" in [x.snapshot_id for x in snapshots]
    assert await snapshot_service.load("foo")
    assert await avd.wait_for_boot(timeout=120)
    assert await avd.stop_activity("com.google.AnimateBox")
    await asyncio.sleep(5)
    assert await avd.start_activity(
        "com.google.AnimateBox/com.google.emu.MainActivity", params=None
    )


@pytest.mark.hostperf
@pytest.mark.benchmark(group="snapshot")
async def test_snapshot_list_perf(benchmark, snapshot_service, coldboot_animation_app):
    # create a 10 snapshots while we are running the animation app.
    for i in range(0, 10):
        # Make sure the animation state is changing the state a bit.
        await asyncio.sleep(1.0)
        await snapshot_service.save("test-{}".format(i))

    # And measure the lists service.
    benchmark(snapshot_service.lists)


async def contains_snapshot(telnet):
    snapshots = await telnet.send("avd snapshot list")
    return any("foo1" in sublist for sublist in snapshots)


@pytest.mark.snapshot
async def test_snapshot_can_save_and_list(telnet, snapshot_service):
    await telnet.send("avd snapshot save foo1")
    assert eventually(
        contains_snapshot, telnet, timeout=10.0
    ), "foo1 snapshot not available"


@pytest.mark.snapshot
@pytest.mark.fast
async def test_snapshot_can_save_and_delete(telnet, snapshot_service):
    await telnet.send("avd snapshot save foo1")
    assert eventually(
        contains_snapshot, telnet, timeout=10.0
    ), "foo1 snapshot not available"
    await telnet.send("avd snapshot del foo1")
    assert not await contains_snapshot(telnet), "foo1 snapshot not deleted"


async def booted_from_snapshot(telnet, expected_snapshot: str):
    """Return True if booted from 'expected_snapshot'"""
    snapshots = await telnet.send("avd snapshot get")
    if snapshots is None:
        return None
    logging.info(f"Current snapshot loaded: {snapshots[0]}")
    if snapshots[0] == expected_snapshot:
        return True


@pytest.mark.snapshot
@pytest.mark.fast
async def test_snapshot_can_save_and_load(avd, telnet, snapshot_service):
    snapshots = await telnet.send("avd snapshot get")
    logging.info("Emulator booted from snapshot %s.", snapshots[0])

    await telnet.send("avd snapshot save foo1")
    assert await eventually(
        partial(contains_snapshot, telnet), timeout=10.0
    ), "foo1 snapshot not available"
    logging.info("Snapshot foo1 successfully saved.")

    assert await telnet.send("avd snapshot load foo1")
    assert await eventually(
        partial(booted_from_snapshot, telnet, "foo1"), timeout=30
    ), "Couldn't load snapshot foo1"



@pytest.mark.snapshot
@pytest.mark.async_timeout(1080)
async def test_avd_launch_after_wipe_data(avd, telnet):
    """Verify AVD launch after data is wiped.

    Args:
        avd (BaseEmulator): Fixture that gives access to a booted emulator.
        telnet (EmulatorConnection): Fixture that gives access to thee mulator console.

    Test Steps:
        1. Launch the AVD.
        2. Modify the "Auto-rotate" and "Airplane mode" system settings.
        3. Restart the AVD (verify 1).
        4. Repeat Step 3 with the launch option '-wipe-data' (verify 2).

    Verification:
        1. The AVD is loaded and the previously saved settings are kept.
        2. The emulator loads and all settings are reverted to default.
    """

    async def get_system_key(key: str):
        # Return the value of the system {key}
        async def _get_system_key(key: str, output: list):
            # Return 'False' if the settings service isn't running.
            # Otherwise, store the value in the output list and return 'True'.
            value = await avd.adb.shell(f"settings get system {key}")
            if "Can't find service: settings" in value:
                return False
            output.append(0 if value == "null" else int(value))
            return True

        output = []
        assert await eventually(
            partial(_get_system_key, key, output)
        ), f"Couldn't retrieve the system key {key}"
        return output[0]

    async def toggle_system_key(key: str):
        # Toggle the integer valued system {key} and return its original value
        initial_value = await get_system_key(key)
        await avd.adb.shell(f"settings put system {key} {initial_value ^ 1}")
        return initial_value

    async def key_has_value(key: str, expected_value: str):
        # Return 'True' if the system {key} has its value equal to {expected_value}
        return expected_value == await get_system_key(key)

    # Toggle the "Auto-rotate" and "Airplane mode" settings.
    initial_rotation_lock = await toggle_system_key("accelerometer_rotation")
    initial_airplane_mode = await toggle_system_key("airplane_mode_on")

    # Make the changes persistent.
    await telnet.send("avd snapshot save default_boot")

    # Restart the emulator and verify the changes persist.
    await avd.restart(avd.launch_flags)
    await avd.wait_for_boot()
    rotation_lock = await get_system_key("accelerometer_rotation")
    airplane_mode = await get_system_key("airplane_mode_on")
    assert (
        rotation_lock != initial_rotation_lock
        and airplane_mode != initial_airplane_mode
    ), "System settings changed when launched from the saved snapshot."

    # Restart the emulator with the '-wipe-data' launch option.
    await avd.stop()
    myflags = ["-wipe-data"]
    await avd.launch(myflags)
    await avd.wait_for_boot()

    # Verify the "Auto-rotate" and "Airplane-mode" setttings reverted to the defaults.
    assert await eventually(
        partial(key_has_value, "accelerometer_rotation", initial_rotation_lock)
    ), "The key 'accelerometer_rotation' didn't revert to the default value."

    assert await eventually(
        partial(key_has_value, "airplane_mode_on", initial_airplane_mode)
    ), "The key 'airplane_mode_on' didn't revert to the default value."


@pytest.mark.snapshot
@pytest.mark.fast
@pytest.mark.async_timeout(2080)
async def test_snapshot_can_edit(snapshot_service):
    """Verify the snapshot name and description can be edited.

    Args:
        snapshot_service (AsyncSnapshotService): snapshot service.

    Test Steps:
        1. Save a new snapshot.
        2. Update the snapshot logical name and description (verify).

    Verification:
        The original snapshot name and description changes.
    """
    assert await snapshot_service.save("snap")

    # Update the snapshot details.
    logical_name = "update_snap"
    description = "Updated Snapshot"
    await snapshot_service.update(
        snap_id="snap", logical_name=logical_name, description=description
    )
    # Verify the changes.
    snapshots = await snapshot_service.lists()
    snapshot = next(iter([snap for snap in snapshots if snap.snapshot_id == "snap"]))
    assert (
        snapshot.details.logical_name == logical_name
        and snapshot.details.description == description
    ), "Coudn't update the snapshot name and description."


@pytest.mark.async_timeout(1200)
@pytest.mark.embedded
async def test_invalid_snapshot_notifies_user(avd):
    """Verify that invalid snapshot cannot be loaded, and that the user will be
       properly notified.

    Args:
        avd (BaseEmulator): Fixture that gives access to a booted emulator.

    Test Steps:
        1. Launch an AVD.
        2. Take a Snapshot.
        3. Repeat Step 2, 2-3 times to verify if multiple snapshots are invalid.
        4. Close the AVD and make a hardware change (front-camera mode).
        5. Re-launch the AVD. (Verify 1).
        6. List the snapshots (Verify 2).

    Verification:
        1. AVD is launched in cold boot mode.
        2. The previously created snapshots are shown as invalid.
    """

    async def take_snapshot(snapshot_id):
        console = await avd.console()
        await console.send(f"avd snapshot save {snapshot_id}")

    async def delete_snapshot(snapshot_id):
        console = await avd.console()
        await console.send(f"avd snapshot delete {snapshot_id}")

    # Take 3 Snapshots.
    await asyncio.gather(*[take_snapshot(f"foo_{i}") for i in range(3)])

    # Change front-camera mode and update the AVD configuration.
    hw_camera_front = avd.configuration.hardware["hw.camera.front"]
    avd.configuration.hardware["hw.camera.front"] = (
        "emulated" if hw_camera_front == "none" else "none"
    )
    with open(avd.configuration.directory / "config.ini", "w") as config_file:
        avd.configuration.hardware.parser.write(config_file)

    # Re-launch the AVD.

    ## Use a filter to check the cold boot message.
    cold_boot_mode = False

    def cold_boot_filter(record):
        # Set 'cold_boot_mode' to 'True' if the cold boot text is detected in the log.
        nonlocal cold_boot_mode
        message = record.getMessage()
        if "USER_INFO" in message and (
            "The emulator is starting from scratch" in message
            or "Emulator is performing a full startup." in message
        ):
            cold_boot_mode = True
        return True

    avd.logger.addFilter(cold_boot_filter)

    try:
        logging.info("Restart the emulator to look for the cold boot message.")
        await avd.restart(avd.launch_flags)
        await avd.wait_for_boot()
        assert cold_boot_mode == True, "The AVD wasn't launched in cold boot mode"
    finally:
        avd.logger.removeFilter(cold_boot_filter)

    # Verify previous saved snapshots are invalid.
    snap = AsyncSnapshotService(snapshot_service=SnapshotServiceStub(avd.channel))
    snapshots = await snap.lists()
    INCOMPATIBLE_STATUS = next(iter(snapshots)).LoadStatus.Value("Incompatible")

    assert all(
        [
            snapshot.status == INCOMPATIBLE_STATUS
            for snapshot in snapshots
            if "foo_" in snapshot.snapshot_id
        ]
    ), "The previously saved snapshots are not invalid!"

    # Remove the created snapshots.
    await asyncio.gather(*[delete_snapshot(f"foo_{i}") for i in range(3)])


@pytest.mark.slow
@pytest.mark.snapshot
@pytest.mark.fast
@pytest.mark.async_timeout(1080)
async def test_on_demand_ram_loading(emulator):
    """Verify AVD stability with on-demand RAM loading.

    Args:
        emulator (BaseEmulator): Fixture that gives access to the configured emulator.

    Test Steps:
        1. Launch a new AVD.
        2. Reboot the AVD by using adb reboot.
        3. Create and launch a quickboot snapshot.
        4. Repeat Step 2.

    Verification:
        1. There are no crashes. AVD should reboot and work normally.
    """
    await emulator.restart(emulator.launch_flags + ["-snapshot", "snap"])
    await emulator.wait_for_boot()

    logging.info("Attempting to reboot the emulator ...")
    await emulator.adb.run(["reboot"])
    assert await (
        emulator.wait_for_boot()
    ), "Emulator didn't come online after adb reboot."
    await asyncio.sleep(5)
    console = await emulator.console()

    logging.info("Attempting to save quickboot snapshot ...")
    await console.send("avd snapshot save snap")

    logging.info("Attempting to load the quickboot snapshot")
    await console.send("avd snapshot load snap")
    try:
        assert await emulator.wait_for_boot()
        response = await console.send("avd snapshot get")
        assert any(
            ["snap" in element for element in response]
        ), "Couldn't load the quickboot snapshot"
        await emulator.adb.run(["reboot"])
        assert await (
            emulator.wait_for_boot()
        ), "Emulator didn't come online after adb reboot."

    except AssertionError as e:
        logging.error("Couldn't boot from the quickboot snapshot.")
        raise
    finally:
        await console.send("avd snapshot del snap")
