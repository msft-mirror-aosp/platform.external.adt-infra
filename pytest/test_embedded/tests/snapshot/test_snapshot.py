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
import os
import tarfile

import pytest
from aemu.proto.snapshot_service_pb2_grpc import SnapshotServiceStub
from snaptool.snapshot import AsyncSnapshotService


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


@pytest.mark.e2e
@pytest.mark.snapshot
@pytest.mark.skipos("win", "reason: b/305017763 - error at setup.")
async def test_snapshot_cannot_load_unknown_snapshot(snapshot_service):
    assert not await snapshot_service.load("foo")


@pytest.mark.e2e
@pytest.mark.snapshot
@pytest.mark.sanity
async def test_snapshot_can_save_and_load(snapshot_service):
    assert await snapshot_service.save("foo")
    snapshots = await snapshot_service.lists()
    assert "foo" in [x.snapshot_id for x in snapshots]
    assert await snapshot_service.load("foo")


@pytest.mark.e2e
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
@pytest.mark.e2e
async def test_snapshot_pull_gets_a_tar(snapshot_service, tmpdir):
    path = str(tmpdir.realpath())  # Needed for py2 compatibility
    assert await snapshot_service.save("foo")
    assert await snapshot_service.pull("foo", path)

    # Let's make sure the tarfile is valid..
    tar = tarfile.open(os.path.join(path, "foo.tar"))
    assert tar.getmembers()


@pytest.mark.skipos("all")
@pytest.mark.snapshot
@pytest.mark.e2e
@pytest.mark.sanity
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


@pytest.mark.e2e
@pytest.mark.snapshot
@pytest.mark.sanity
@pytest.mark.async_timeout(300)
async def test_app_launch_after_snapshot_load(avd, snapshot_service):
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
