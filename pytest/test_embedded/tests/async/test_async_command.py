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
import asyncio
from pathlib import Path

import pytest

from emu.process.command import Command

# These are all non emulator tests.
pytestmark = pytest.mark.std


@pytest.fixture()
@pytest.mark.async_timeout(1.1)
async def my_amazing_fixture():
    try:
        await asyncio.sleep(1)
        yield 1
    finally:
        await asyncio.sleep(1)


async def test_my_amazing_fixture(my_amazing_fixture):
    assert True


@pytest.mark.xfail
@pytest.mark.async_timeout(1)
@pytest.mark.std
@pytest.mark.skipos("win", "reason: no sleep cmd")
async def test_sleep_times_out():
    cmd = Command(["sleep", "10"])
    process = await cmd.run()
    await process.wait()


@pytest.mark.xfail
@pytest.mark.async_timeout(1)
@pytest.mark.skipos("win", "reason: no sleep cmd")
async def test_sleep_times_out_in_iterator():
    cmd = Command(["sleep", "10"])
    count = 0
    async with await cmd.run() as stream:
        async for line in stream:
            count += 1
    assert False


@pytest.mark.skipos("win", "reason: no sleep cmd")
async def test_can_iterate():
    current_script_path = Path(__file__).resolve()
    cmd = Command(["cat", current_script_path])
    count = 0
    async with await cmd.run() as stream:
        async for line in stream:
            count += 1

    assert count > 0


@pytest.mark.skipos("win", "reason: no sleep cmd")
async def test_times_out_status():
    cmd = Command(["sleep", "10"])
    status, lines = await cmd.run_until_finished(1)
    assert status == -1


@pytest.mark.skipos("win", "reason: might not behave as expected")
async def test_reads_std_out_err():
    cmd = Command(["echo", "Hello World"])
    status, lines = await cmd.run_until_finished(1)
    assert status == 0
    assert "Hello World" in lines
