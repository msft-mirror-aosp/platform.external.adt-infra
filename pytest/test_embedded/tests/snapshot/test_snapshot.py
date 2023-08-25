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
import os
import tarfile
import time

import pytest
from snaptool.snapshot import SnapshotService


@pytest.fixture
def snapshot_service(avd):
    """Fixture to make sure the emulator has no snapshots."""
    snap = SnapshotService(snapshot_service=avd.description.get_snapshot_service())
    for entry in snap.lists():
        snap.delete(entry.snapshot_id)
    yield snap
    for entry in snap.lists():
        snap.delete(entry.snapshot_id)


@pytest.mark.e2e
@pytest.mark.snapshot
@pytest.mark.timeout(timeout=20, func_only=True)
def test_snapshot_cannot_load_unknown_snapshot(snapshot_service):
    assert not snapshot_service.load("foo")


@pytest.mark.e2e
@pytest.mark.snapshot
@pytest.mark.timeout(timeout=60, func_only=True)
def test_snapshot_can_save_and_load(snapshot_service):
    assert snapshot_service.save("foo")
    assert "foo" in [x.snapshot_id for x in snapshot_service.lists()]
    assert snapshot_service.load("foo")


@pytest.mark.e2e
@pytest.mark.snapshot
@pytest.mark.timeout(timeout=60, func_only=True)
def test_snapshot_delete_removes(snapshot_service):
    assert snapshot_service.save("foo")
    assert "foo" in [x.snapshot_id for x in snapshot_service.lists()]
    assert snapshot_service.delete("foo")
    assert "foo" not in [x.snapshot_id for x in snapshot_service.lists()]


@pytest.mark.skip
@pytest.mark.snapshot
@pytest.mark.e2e
def test_snapshot_pull_gets_a_tar(snapshot_service, tmpdir):
    path = str(tmpdir.realpath())  # Needed for py2 compatibility
    assert snapshot_service.save("foo")
    assert snapshot_service.pull("foo", path)

    # Let's make sure the tarfile is valid..
    tar = tarfile.open(os.path.join(path, "foo.tar"))
    assert tar.getmembers()


@pytest.mark.skip
@pytest.mark.snapshot
@pytest.mark.e2e
def test_snapshot_can_restore_a_pulled_snapshot(snapshot_service, tmpdir):
    path = str(tmpdir.realpath())  # Needed for py2 compatibility
    assert snapshot_service.save("foo")
    assert snapshot_service.pull("foo", path)
    assert snapshot_service.delete("foo")
    assert "foo" not in [x.snapshot_id for x in snapshot_service.lists()]

    assert snapshot_service.push(os.path.join(path, "foo.tar"))
    assert "foo" in [x.snapshot_id for x in snapshot_service.lists()]
    assert snapshot_service.load("foo")


@pytest.mark.perf
@pytest.mark.benchmark(group="snapshot")
def test_snapshot_list_perf(benchmark, snapshot_service, coldboot_animation_app):
    # create a 10 snapshots while we are running the animation app.
    for i in range(0, 10):
        # Make sure the animation state is changing the state a bit.
        time.sleep(1.0)
        snapshot_service.save("test-{}".format(i))

    # And measure the lists service.
    benchmark(snapshot_service.lists)
