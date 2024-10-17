# Copyright 2023 The Android Open Source Project
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

import pytest

TEMP_FILE = "__push_file.txt"
FILE_SIZE = 100


@pytest.fixture
def tmp_test_file(tmp_path):
    temp_file = tmp_path / TEMP_FILE
    temp_file.write_text(FILE_SIZE * "lorem ipsum\n")
    return temp_file


@pytest.mark.adb
@pytest.mark.flaky(reruns=0)  # b/282855106 flaky on mac_aarch64.
@pytest.mark.skipos("win", "Test fails on Windows b/288447852")
async def test_adb_push_pull(avd, tmp_test_file):
    device_file = f"/sdcard/{tmp_test_file.name}"
    await avd.adb.push(tmp_test_file, device_file)
    assert "yes" in await avd.adb.shell(f"[ -f {device_file} ] && echo 'yes'")

    tmp_test_file.unlink()
    await avd.adb.pull(device_file, tmp_test_file)
    assert open(tmp_test_file, "r").read() == FILE_SIZE * "lorem ipsum\n"
