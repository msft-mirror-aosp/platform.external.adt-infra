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
import datetime

import pytest
from PIL import Image


@pytest.fixture
def tmp_test_file(tmp_path):
    current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_file = tmp_path / f"__screenshot_{current_time}.png"
    return temp_file


@pytest.mark.adb
@pytest.mark.flaky(reruns=0)
async def test_adb_screencapture_creates_a_file(avd, tmp_test_file):
    device_file = f"/sdcard/{tmp_test_file.name}"
    await avd.adb.shell(f"rm {device_file}")
    assert "adb: error" not in await avd.adb.shell(f"screencap {device_file}")
    assert "yes" in await avd.adb.shell(f"[ -f {device_file} ] && echo 'yes'")


@pytest.mark.adb
@pytest.mark.flaky(reruns=0)
async def test_adb_screencapture_is_a_png(avd, tmp_test_file):
    device_file = f"/sdcard/{tmp_test_file.name}"
    await avd.adb.shell(f"rm {device_file}")
    assert "adb: error" not in await avd.adb.shell(f"screencap {device_file}")

    # Check that we have a png file.
    await avd.adb.pull(device_file, tmp_test_file)
    img: Image.Image = Image.open(tmp_test_file)
    assert img.format == "PNG"
