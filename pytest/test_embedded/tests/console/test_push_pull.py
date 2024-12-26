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
    """Creates a temporary text file for testing, and cleans it up afterwards.

    Args:
        tmp_path: pytest's temporary path fixture.

    Yields:
        Path: The path to the temporary file.
    """
    temp_file = tmp_path / TEMP_FILE
    temp_file.write_text(FILE_SIZE * "lorem ipsum\n")
    yield temp_file
    temp_file.unlink()


@pytest.fixture
async def android_tmp_file(avd):
    """Creates a temporary file on the Android device and cleans it up afterwards.

    Args:
        avd: The Android Virtual Device instance.

    Yields:
        str: The path to the temporary file on the device.
    """
    device_file = await avd.adb.exec_out("mktemp")
    yield device_file
    await avd.adb.exec_out(f"rm -rf {device_file}")


@pytest.mark.adb
@pytest.mark.flaky(reruns=1)
async def test_adb_push(avd, tmp_test_file, android_tmp_file):
    """Tests adb push and pull functionality.

    This test pushes a local file to the Android device, verifies its size,
    then pulls it back and verifies its content.

    Args:
        avd: The Android Virtual Device instance.
        tmp_test_file: Fixture providing a temporary local file.
        android_tmp_file: Fixture providing a temporary file path on the device.
    """
    await avd.adb.push(str(tmp_test_file), android_tmp_file)
    file_size = await avd.adb.exec_out(f"stat -c %s {android_tmp_file}")
    assert int(file_size) == tmp_test_file.stat().st_size


@pytest.mark.adb
@pytest.mark.flaky(reruns=1)
async def test_adb_pull(avd, tmp_path, tmp_test_file, android_tmp_file):
    """Tests adb push and pull functionality.

    This test pushes a local file to the Android device, verifies its size,
    then pulls it back and verifies its content.

    Args:
        avd: The Android Virtual Device instance.
        tmp_test_file: Fixture providing a temporary local file.
        android_tmp_file: Fixture providing a temporary file path on the device.
    """
    await avd.adb.push(tmp_test_file, android_tmp_file)

    local_tmp = tmp_path / "pulled.txt"
    await avd.adb.pull(android_tmp_file, str(local_tmp))
    assert open(local_tmp, "r").read() == FILE_SIZE * "lorem ipsum\n"
