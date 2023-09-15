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
TEMP_FILE = "__screenshot.png"

@pytest.fixture
def tmp_test_file(tmp_path):
    temp_file = tmp_path / TEMP_FILE
    return temp_file

@pytest.mark.adb
@pytest.mark.timeout(timeout=20, func_only=True)
def test_adb_screencapture(avd, tmp_test_file):
    device_file = f"/sdcard/{tmp_test_file.name}"
    assert not "adb: error" in avd.adb.run(["shell", "screencap", device_file])
    avd.adb.pull(device_file, tmp_test_file)
    assert "yes" in avd.adb.shell(f"[ -f {device_file} ] && echo 'yes'")
