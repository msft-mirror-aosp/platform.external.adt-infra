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
import pytest
from aemu.proto.screen_recording_service_pb2 import RecordingInfo
from aemu.proto.screen_recording_service_pb2_grpc import ScreenRecordingStub
from google.protobuf import empty_pb2

from emu.timing import eventually
from emu.emulator import Emulator


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


@pytest.mark.e2e
@pytest.mark.fast
@pytest.mark.wear
@pytest.mark.atv
@pytest.mark.async_timeout(1080)
async def test_different_AVDs_can_record_in_webm(emulator, avd_config, tmp_path):
    """Ensure screen recording works for different AVDs.

    Args:
        emulator (BaseEmulator): Fixture with the configured emulator.
        avd_config (dict): AVD configuration.
        tmp_path (pathlib.Path): temporary directory path to save the videos.

    Test steps:
        1. Create and launch a new AVD.
        2. Perform Screen Recording
        3. Wait for couple of seconds and stop the recording.
        4. Save the recording to a WEBM file.(Verify 1).
        5. Repeat Steps 1 to 4 for Tablets, Wear and TV.

    Verification:
    1. The video is recorded, and the webm file is saved correctly.
    """
    # Launch the emulator with the specificed AVD.
    logging.info("Launching emulator ...")
    myflags = ["-no-snapshot-save"]
    emu = Emulator(android_home=emulator.android_home,
                   android_avd_home=emulator.android_avd_home,
                   exe=emulator.exe,
                   avd_config=avd_config)

    await emu.launch(flags=myflags)
    await emu.wait_for_boot()

    channel = emu.description.get_async_grpc_channel([("emulator.security", "token")])
    screen_service = ScreenRecordingStub(channel)

    # Ensure Screen Recording works for the specified AVD.
    device = avd_config['device.name']
    sample_webm = tmp_path / f"sample_{device}.webm"
    info = RecordingInfo(width=120, height=120, file_name=str(sample_webm))

    logging.info(f"Starting the recording: {info} ({device } AVD)")
    await screen_service.StartRecording(info)
    await asyncio.sleep(5)

    logging.info(f"Stopping the recording: {info} ({device } AVD)")
    await screen_service.StopRecording(info)

    assert sample_webm.exists()
    assert sample_webm.stat().st_size > 10240, \
            f"We should have recorded a series of frames in the device {device}"

    await emu.stop()
