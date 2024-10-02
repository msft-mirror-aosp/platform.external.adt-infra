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
from aemu.proto.emulator_controller_pb2_grpc import EmulatorControllerStub
from google.protobuf import empty_pb2

from emu.timing import eventually, wait_until

from tests.test_utils import decode_qrcodes, get_window_dump, click_button
from pathlib import Path


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
@pytest.mark.fast
@pytest.mark.graphics
@pytest.mark.sanity
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
    sample_file_header = b"\x1A\x45\xDF\xA3"
    await screen_records_video(screen_service, sample_file)
    verify_recorded_file_header(sample_file, sample_file_header)


@pytest.mark.flaky
@pytest.mark.sanity
@pytest.mark.graphics
async def test_screen_records_video_in_gif(screen_service, animation_app, tmp_path):
    sample_file = tmp_path / "sample.gif"
    sample_file_header = b"\x1aE\xdf\xa3"
    await screen_records_video(screen_service, sample_file)
    verify_recorded_file_header(sample_file, sample_file_header)



@pytest.mark.console
@pytest.mark.fast
@pytest.mark.async_timeout(1080)
async def test_screen_records_video_telnet(emulator, animation_app, tmp_path, telnet):
    myflags = ["-no-window"]
    assert await emulator.launch(flags=myflags)

    assert (
     await emulator.wait_for_boot(timeout=1080)
    ), f"The emulator couldn't be launched with no-window option"

    sample_file = tmp_path / "sample_record.webm"
    await telnet.send("screenrecord start {}".format(sample_file))
    await asyncio.sleep(5)
    await telnet.send("screenrecord stop")

    sample_file_header = b"\x1A\x45\xDF\xA3"
    verify_recorded_file_header(sample_file, sample_file_header)



@pytest.mark.embedded
@pytest.mark.fast
@pytest.mark.async_timeout(1080)
async def test_screen_recording_duration(animation_app, emulator, tmp_path):
    screen_service = ScreenRecordingStub(channel=emulator.channel)
    sample_file = tmp_path / "sample.gif"
    sample_file_header = b"\x1aE\xdf\xa3"
    info = RecordingInfo(width=120, height=120, file_name=str(sample_file))
    logging.info("Starting the recording: %s", info)
    await screen_service.StartRecording(info)
    # Recording can be done to max of 180 secs. Once 180 secs are over, it will stop the recording
    await asyncio.sleep(200)  # Wait for more than 180 secs
    await screen_service.StartRecording(info)  # Recording can be started again after 180 secs
    logging.info("Stopping the recording: %s", info)
    await screen_service.StopRecording(info)
    verify_recorded_file_header(sample_file, sample_file_header)


async def screen_records_video(screen_service, sample_file,
                               width=140, height=140, duration=2):
    info = RecordingInfo(width=width, height=height, file_name=str(sample_file))
    logging.info("Starting the recording: %s", info)
    await screen_service.StartRecording(info)
    await asyncio.sleep(duration)
    logging.info("Stopping the recording: %s", info)
    await screen_service.StopRecording(info)


def verify_recorded_file_header(sample_file, sample_file_header):
    with open(sample_file, "rb") as file:
        header = file.read(4)

    assert (
            header == sample_file_header
    ), f'{header} != sample_file_header, the magic header'


async def play_webm(emulator, file):
    """Play a .webm video using the default video player.
    """
    async def dismiss_fullscreen_popup():
        # Dismiss fullscreen mode if needed.
        status = await click_button(emulator, text="Got it")
        return None if not status else True

    await emulator.stop_activity("com.google.android.apps.photos")
    await emulator.start_activity(
        "com.google.android.apps.photos/.pager.HostPhotoPagerActivity",
        params=f'-a android.intent.action.VIEW -W -d file://{file} -t "video/*"'
    )
    await eventually(dismiss_fullscreen_popup)
    logging.info(f"Launched recording file '{file}'")


async def verify_qrcode(emulator, webm_recording, payload):
    """ Play a .webm recording in the emulator and check if a QR code exists
    """
    video_path = Path('/sdcard/Downloads/') / webm_recording.name
    await emulator.adb.push(webm_recording, video_path)
    emulator_controller = EmulatorControllerStub(emulator.channel)
    async def _play_and_decode():
        await play_webm(emulator, video_path)
        return await decode_qrcodes([payload], emulator_controller=emulator_controller)
    assert await wait_until(
        _play_and_decode, timeout=240
    ), "Unable to decode the QR code from video '{sample_file}'."


@pytest.mark.parametrize(
    "gpu_mode",
    ["auto", "host", "swiftshader_indirect", "angle_indirect", "swangle"]
)

@pytest.mark.graphics
@pytest.mark.fast
@pytest.mark.async_timeout(1080)
async def test_screen_records_with_different_gpu_modes(
    emulator, gpu_mode, tmp_path, qrcode_png
):
    """Verify screen recording work with different gpu modes.

    Args:
        emulator (BaseEmulator): Fixture that gives access to the running emulator.
        gpu_mode (str): gpu mode.
        tmp_path (Path): Fixture that provides a temporary working directory.

    Test Steps:
        1. Launch an AVD with the option "-gpu auto".
        2. Launch a PNG image with a pre-encoded QR code.
        3. Perform a Screen Recording.
        4. Wait for couple of seconds and then Stop the Recording.
        5. Save the video in "WEBM" format (Verify 1).
        6. Play the video in the default video player (Verify 2).
        7. Repeat the process with other gpu modes:
        host, swiftshader_indirect, angle_indirect (Windows), swangle.

    Verification:
        1. The saved WEBM recording should be a valid video file.
        2. The video is played without any rendering issues, observed from the
           decoding of the embedded QR code through a series of screenshots.
    """
    if gpu_mode == "angle_indirect" and platform.system != "Windows":
        pytest.skip(f"gpu mode {gpu_mode} is only available on Windows.")

    logging.info(f"Launching the emulator with the gpu mode '{gpu_mode}'.")
    await emulator.launch(emulator.launch_flags + ["-no-snapshot-save",
                                                   "-gpu", f"{gpu_mode}"])
    await emulator.wait_for_boot()
    screen_service = ScreenRecordingStub(channel=emulator.channel)

    sample_file = tmp_path / "sample.webm"
    sample_file_header = b"\x1A\x45\xDF\xA3"
    await qrcode_png.show()
    await screen_records_video(screen_service, sample_file, 270, 480, 15)
    verify_recorded_file_header(sample_file, sample_file_header)
    await verify_qrcode(emulator, sample_file, qrcode_png.payload)



@pytest.mark.graphics
@pytest.mark.fast
@pytest.mark.async_timeout(1080)
async def test_screen_records_with_different_orientations(
        avd, screen_service, telnet, tmp_path, qrcode_png):
    """Verify the behavior of screen recording with different screen orientation.

    Args:
        avd (BaseEmulator): Fixture that gives access to the running emulator.
        screen_service (ScreenRecordingStub): screen recording service.
        telnet (EmulatorConnection): Fixture that gives access to the emulator console.
        tmp_path (Path): Fixture that provides a temporary directory.

    Test Steps:
        1. Create a new AVD.
        2. Change device orientation to (reverse) landscape mode.
        3. Start a Screen Recording in WEBM format.
        4. Wait for couple of seconds and then stop the recording. (Verify 1 and 2)
        6. Start the Screen Recording.
        7. Change device orientation from reverse landscape do portrait during
           the recording. (Verify 1 and 2)

    Verification:
        1. The video is recorded without any issues, verified by checking the recording
           file size and header.
        2. The video is played without any rendering issues, observed from the decoding
           of the embedded QR code through a series of screenshots.
    """
    async def rotate():
        # Rotate the emulator clockwise by 90 degrees.
        await telnet.send("rotate")
        await asyncio.sleep(7)

    async def check_webm(sample_webm, sample_file_header):
        # Check file size.
        assert sample_webm.exists()
        assert (
            sample_webm.stat().st_size > 10240
        ), "We should have recorded a series of frames"
        # Check file header.
        with open(sample_webm, "rb") as file:
            header = file.read(4)
        assert (
                header == sample_file_header
        ), f'{header} != sample_file_header, the magic header'

    sample_file_header = b"\x1A\x45\xDF\xA3"

    # Ensure screen recording work in (reverse) landscape mode.
    landscape_file = tmp_path / "sample_landscape.webm"
    logging.info(f"Rotating the emulator to reverse landscape ...")
    await rotate()
    await qrcode_png.show()
    await screen_records_video(screen_service, landscape_file, 270, 480, 20)
    verify_recorded_file_header(landscape_file, sample_file_header)
    await verify_qrcode(avd, landscape_file, qrcode_png.payload)

    # Ensure a valid recording is produced while the emulator is rotated.
    landscape_portrait_file = tmp_path / "sample_landscape_portrait.webm"
    info = RecordingInfo(width=270, height=480, file_name=str(landscape_portrait_file))
    logging.info("Starting the recording: %s", info)
    await screen_service.StartRecording(info)
    for angle in [-180, 90, 0]:
        logging.info(f"Rotating the emulator to {angle} degrees ..")
        await rotate()

    logging.info("Stopping the recording: %s", info)
    await screen_service.StopRecording(info)

    await check_webm(landscape_portrait_file, sample_file_header)
    await verify_qrcode(avd, landscape_portrait_file, qrcode_png.payload)
