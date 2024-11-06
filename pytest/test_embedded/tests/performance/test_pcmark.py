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
import logging
import pathlib
import pytest
import shutil
import xml.etree.ElementTree as ET
import zipfile


pcmark_package = "com.futuremark.pcmark.android.benchmark"
pcmark_activity = f"{pcmark_package}/com.futuremark.gypsum.activity.PcmaWorkActivity"
install_path = f"/storage/emulated/0/Android/data/{pcmark_package}/files"


async def install_pcmark(avd, bundle_path):
    await avd.install_apk(
        bundle_path.joinpath("pcmark-android-v3-0-4061.apk"), pcmark_package
    )
    await avd.adb.shell(f"mkdir -p {install_path}")
    await avd.adb.push(f"{bundle_path.joinpath('key.txt')}", install_path)
    await avd.adb.push(
        f"{bundle_path.joinpath('pcmark-for-android-v3-0-4061-pcma-storagev2-data-v1-0-0.dlc')}",
        install_path,
    )
    await avd.adb.push(
        f"{bundle_path.joinpath('pcmark-for-android-v3-0-4061-pcma-workv3-data-v1-0-1.dlc')}",
        install_path,
    )


async def run_pcmark(avd, bundle_path):
    # A subset of PCMark which runs very quickly and is suitable for testing.
    await avd.adb.push(
        f"{bundle_path.joinpath('Work_v3_test_xmls/pcma_work_v3_photoediting.xml')}",
        f"{install_path}/benchmark_run.xml",
    ),
    await avd.adb.shell(f"rm -f {install_path}/result.zip")
    await avd.start_activity(
        pcmark_activity,
        params="-e com.futuremark.android.InstallDLC true"
        f" --es com.futuremark.android.BenchmarkFilePath {install_path}/benchmark_run.xml",
    )


async def pull_results(avd, temp_path, results):
    while "No such file" in await avd.adb.shell(f"ls {install_path}/result.zip"):
        await asyncio.sleep(5)
    await avd.adb.pull(f"{install_path}/result.zip", f"{temp_path}")

    with zipfile.ZipFile(str(temp_path.joinpath("result.zip")), "r") as zip_ref:
        zip_ref.extract(member="Result.xml", path=temp_path)

    xml_results = (
        ET.parse(str(temp_path.joinpath("Result.xml"))).getroot().find("results")
    )
    for xml_result in xml_results.findall("result"):
        if xml_result.find("passIndex").text != "0":
            continue
        for elem in results:
            results[elem].append(int(xml_result.find(elem).text))

    return results


async def cool_down():
    # Sleep for a few of minutes to let the host settle and cool down a bit.
    await asyncio.sleep(60 * 2)


@pytest.mark.slow
@pytest.mark.guestperf
@pytest.mark.async_timeout(1080)
async def test_pcmark(avd, log_directory, record_property):
    bundle_path = pathlib.Path.home().joinpath("emu-perf-bundle/Pcmark")
    if not bundle_path.exists():
        logging.error(f"Could not find the Pcmark test bundle. path: {bundle_path}")
        return

    temp_path = bundle_path.joinpath("tmp")
    if temp_path.exists():
        shutil.rmtree(temp_path)
    temp_path.mkdir()

    await install_pcmark(avd, bundle_path)

    elements = [
        "result_PcmaWritingV3ScoreForPass",
        "result_PcmaVideoEditingV3ScoreForPass",
        "result_PcmaDataManipulationV3ScoreForPass",
        "result_PcmaWebV3ScoreForPass",
        "result_PcmaPhotoEditingV3ScoreForPass",
        "result_PcmaWorkv3ScoreForPass",
    ]
    results = dict([(x, []) for x in elements])

    # Performance tests are notoriously noisy. Re-run and report average.
    repeats = 3
    for i in range(repeats):
        await cool_down()
        await run_pcmark(avd, bundle_path)
        await pull_results(avd, temp_path, results)

    for elem in results:
        avg = sum(results[elem]) / len(results[elem])
        record_property(elem, int(avg))
