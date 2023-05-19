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


def adb_test_push(avd, temp_file):
    """Verify that pushing a file is successful.

    Args:
      avd: The emulator.
      temp_file : Temporary file to push

    Returns:
      True if successful, else False.
    """
    return not "adb: error" in avd.adb.run(["push", temp_file, "/sdcard"])


def adb_test_pull(avd, temp_file):
    """Verify that pulling a file is successful.

    Args:
      avd: The emulator.
      temp_file : Temporary file to pull.

    Returns:
      True if successful, else False.
    """
    return not "adb: error" in avd.adb.run(["pull /sdcard/", temp_file])


@pytest.mark.adb
@pytest.mark.flaky(reruns=3, reruns_delay=5)  # b/282855106 flaky on mac_aarch64.
def test_adb_push_pull(avd, tmp_path):
    """Test adb push/pull operation.

    Args:
        avd: The emulator
        tmp_path : Fixture for creating temporary files and directory
    """
    temp_file = tmp_path / TEMP_FILE
    temp_file.write_text(FILE_SIZE * "lorem ipsum\n")

    success = adb_test_push(avd, str(temp_file))
    assert success, "ADB Push failed"
    success = adb_test_pull(avd, str(temp_file))
    assert success, "ADB Pull failed"
