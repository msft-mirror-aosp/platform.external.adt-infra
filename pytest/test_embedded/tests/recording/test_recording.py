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
import time

import pytest

from aemu.proto.screen_recording_service_pb2 import RecordingInfo
from aemu.proto.screen_recording_service_pb2_grpc import ScreenRecordingStub
from google.protobuf import empty_pb2
from grpc._channel import _InactiveRpcError

from emu.timing import eventually
from tests.test_utils import StreamingCall


@pytest.fixture
def screen_service(service):
    """A screen service fixture that will stop any active recording on test completion."""
    screen_service: ScreenRecordingStub = service(ScreenRecordingStub)
    screen_service.StopRecording(RecordingInfo())
    yield screen_service
    screen_service.StopRecording(RecordingInfo())


@pytest.mark.timeout(timeout=20, func_only=True)
@pytest.mark.flaky(reruns=3, reruns_delay=5)
@pytest.mark.graphics
def test_screen_record_sends_event(screen_service, tmp_path):
    stream = screen_service.ReceiveRecordingEvents(empty_pb2.Empty())
    info = RecordingInfo(width=120, height=120, file_name=str(tmp_path / "sample.webm"))

    def receives_an_update_event(recording_info):
        # We expect a notification that a recording event happened, with our
        # temporary file.
        return recording_info.file_name == info.file_name

    with StreamingCall(stream) as stream:
        screen_service.StartRecording(info)
        assert eventually(
            receives_an_update_event, stream
        ), "Did not receive a notification, even though I started recording"


@pytest.mark.timeout(timeout=20, func_only=True)
@pytest.mark.flaky(reruns=3, reruns_delay=5)
@pytest.mark.graphics
def test_screen_records_video(screen_service, animation_app, tmp_path):
    sample_webm = tmp_path / "sample.webm"
    info = RecordingInfo(width=120, height=120, file_name=str(sample_webm))
    screen_service.StartRecording(info)
    time.sleep(2)
    screen_service.StopRecording(info)

    assert sample_webm.exists()
    assert (
        sample_webm.stat().st_size > 1024
    ), "We should have recorded a series of frames"


@pytest.mark.timeout(timeout=20, func_only=True)
@pytest.mark.flaky(reruns=3, reruns_delay=5)
@pytest.mark.graphics
def test_can_only_record_once(screen_service, tmp_path):
    sample_webm = tmp_path / "sample.webm"
    info = RecordingInfo(width=120, height=120, file_name=str(sample_webm))
    screen_service.StartRecording(info)
    with pytest.raises(
        _InactiveRpcError, match=".*The recorder is not in a stopped state.*"
    ):
        # Our second record attempt should result in an error
        screen_service.StartRecording(info)


@pytest.mark.timeout(timeout=20, func_only=True)
@pytest.mark.flaky(reruns=3, reruns_delay=5)
@pytest.mark.graphics
def test_screen_records_video_in_webm(screen_service, animation_app, tmp_path):
    sample_webm = tmp_path / "sample.webm"
    info = RecordingInfo(width=120, height=120, file_name=str(sample_webm))
    screen_service.StartRecording(info)
    time.sleep(2)
    screen_service.StopRecording(info)

    with open(sample_webm, "rb") as file:
        header = file.read(4)

    assert (
        header == b"\x1A\x45\xDF\xA3"
    ), f'{header} != b"\x1A\x45\xDF\xA3", the magic WebM header'
