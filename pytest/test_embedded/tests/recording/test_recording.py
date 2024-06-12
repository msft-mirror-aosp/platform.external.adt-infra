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
import asyncio
import logging

import grpc
import platform
import pytest
from aemu.proto.screen_recording_service_pb2 import RecordingInfo
from aemu.proto.screen_recording_service_pb2_grpc import ScreenRecordingStub
from google.protobuf import empty_pb2

from emu.timing import eventually


@pytest.fixture
async def screen_service(service):
    """A screen service fixture that will stop any active recording on test completion."""
    screen_service: ScreenRecordingStub = service(ScreenRecordingStub)
    logging.info("--> screen_service: stopping recording")
    await screen_service.StopRecording(RecordingInfo())
    logging.info("--> Yielding screen_service")
    yield screen_service
    logging.info("<-- screen_service: stopping recording")
    await screen_service.StopRecording(RecordingInfo())


@pytest.mark.flaky
@pytest.mark.graphics
async def test_screen_record_sends_event(screen_service, tmp_path):
    stream = screen_service.ReceiveRecordingEvents(empty_pb2.Empty())
    info = RecordingInfo(width=120, height=120, file_name=str(tmp_path / "sample.webm"))

    def receives_an_update_event(recording_info):
        # We expect a notification that a recording event happened, with our
        # temporary file.
        return recording_info.file_name == info.file_name

    logging.info("Starting the recording: %s", info)
    await screen_service.StartRecording(info)
    assert await eventually(
        receives_an_update_event, stream
    ), "Did not receive a notification, even though I started recording"


@pytest.mark.flaky
@pytest.mark.graphics
@pytest.mark.sanity
@pytest.mark.fast
async def test_screen_records_video(screen_service, animation_app, tmp_path):
    sample_webm = tmp_path / "sample.webm"
    info = RecordingInfo(width=120, height=120, file_name=str(sample_webm))
    logging.info("Starting the recording: %s", info)
    await screen_service.StartRecording(info)
    await asyncio.sleep(5)
    logging.info("Stopping the recording: %s", info)
    await screen_service.StopRecording(info)

    # bump the size to 10240, as empty webm will be around 4k already
    # realistically, the size should be around 49621, but lets leave some
    # room for that
    assert sample_webm.exists()
    assert (
        sample_webm.stat().st_size > 10240
    ), "We should have recorded a series of frames"


@pytest.mark.flaky
@pytest.mark.graphics
@pytest.mark.fast
async def test_can_only_record_once(screen_service, tmp_path):
    sample_webm = tmp_path / "sample.webm"
    info = RecordingInfo(width=120, height=120, file_name=str(sample_webm))
    await screen_service.StartRecording(info)
    with pytest.raises(
        grpc.aio._call.AioRpcError, match=".*The recorder is not in a stopped state.*"
    ):
        # Our second record attempt should result in an error
        await screen_service.StartRecording(info)

@pytest.mark.flaky
@pytest.mark.graphics
@pytest.mark.sanity
@pytest.mark.wear
@pytest.mark.atv
async def test_screen_records_video_in_webm(screen_service, animation_app, tmp_path):
    sample_file = tmp_path / "sample.webm"
    sample_file_header =  b"\x1A\x45\xDF\xA3"
    await screen_records_video(screen_service, sample_file, sample_file_header)

@pytest.mark.flaky
@pytest.mark.graphics
@pytest.mark.sanity
async def test_screen_records_video_in_gif(screen_service, animation_app, tmp_path):
    sample_file = tmp_path / "sample.gif"
    sample_file_header = b"\x1aE\xdf\xa3"
    await screen_records_video(screen_service, sample_file, sample_file_header)

async def screen_records_video(screen_service, sample_file, sample_file_header):
    info = RecordingInfo(width=120, height=120, file_name=str(sample_file))
    logging.info("Starting the recording: %s", info)
    await screen_service.StartRecording(info)
    await asyncio.sleep(2)
    logging.info("Stopping the recording: %s", info)
    await screen_service.StopRecording(info)

    with open(sample_file, "rb") as file:
        header = file.read(4)

    assert (
            header == sample_file_header
    ), f'{header} != sample_file_header, the magic header'


@pytest.mark.parametrize(
    "gpu_mode",
    ["auto", "host", "swiftshader_indirect", "angle_indirect", "swangle"]
)

@pytest.mark.e2e
@pytest.mark.graphics
@pytest.mark.fast
@pytest.mark.async_timeout(1080)
async def test_screen_records_with_different_gpu_modes(
    emulator, gpu_mode, tmp_path
):
    """Verify screen recording work with different gpu modes.

    Args:
        emulator (BaseEmulator): Fixture that gives access to the running emulator.
        gpu_mode (str): gpu mode.
        tmp_path (Path): Fixture that provides a temporary working directory.

    Test Steps:
        1. Launch an AVD with the option "-gpu auto".
        2. Perform a Screen Recording.
        3. Wait for couple of seconds and then Stop the Recording.
        4. Save the video in "WEBM" format (Verify).
        5. Repeat the process with other gpu modes:
        host, swiftshader_indirect, angle_indirect (Windows), swangle.

    Verification:
        The saved WEBM recording should be a valid video file.
    """
    if gpu_mode == "angle_indirect" and platform.system != "Windows":
        pytest.skip(f"gpu mode {gpu_mode} is only available on Windows.")

    logging.info(f"Launching the emulator with the gpu mode '{gpu_mode}'.")
    await emulator.launch(emulator.launch_flags + ["-no-snapshot-save",
                                                   "-gpu", f"{gpu_mode}"])
    await emulator.wait_for_boot()
    screen_service = ScreenRecordingStub(channel=emulator.channel)

    sample_file = tmp_path / "sample.webm"
    sample_file_header =  b"\x1A\x45\xDF\xA3"
    await screen_records_video(screen_service, sample_file, sample_file_header)
