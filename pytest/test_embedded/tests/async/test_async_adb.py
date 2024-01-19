# Copyright 2024 The Android Open Source Project
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
from pathlib import Path

import pytest

from emu.adb.adb import Adb
from emu.adb.async_device import AdbDeviceAsync

#
# Note these test should be disabled, they are used only
# to validate that the async adb plugin works as expected
#
# You will need to have an emulator up and running


@pytest.fixture
async def device() -> AdbDeviceAsync:
    adb = Adb("34", "emulator-5554", Path("/usr/local/bin/adb"))
    return await adb.device()


async def test_can_find_device(device):
    assert device is not None


async def test_waits_for_boot(device):
    await device.wait_boot_complete()
    assert True


async def test_can_get_props(device):
    props = await device.shell("getprop")
    assert len(props) > 0


async def test_is_not_installed(device):
    installed = await device.is_installed("foo-bar")
    assert not installed


async def test_state_good(device):
    state = await device.get_state()
    assert state


async def test_is_installed(device):
    installed = await device.is_installed("com.google.android.gms.supervision")
    assert installed


@pytest.mark.xfail
@pytest.mark.async_timeout(2)
async def test_logcat(device):
    count = 0
    async with await device.shell_stream("logcat") as stream:
        async for line in stream:
            logging.info(count)
            count = count + 1

    # This test should timeout..
    assert False
