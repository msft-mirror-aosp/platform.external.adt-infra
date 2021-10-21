# Copyright 2020 The Android Open Source Project
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
from grpc import RpcError, StatusCode
from aemu.proto.emulator_controller_pb2 import (
    DisplayConfiguration,
    DisplayConfigurations,
)
from google.protobuf import empty_pb2

_EMPTY_ = empty_pb2.Empty()


@pytest.fixture
def no_displays():
    """Fixture to make sure the emulator has no multi displays configured.

    Use this if you want to make sure the emulator has no secondary displays
    """
    stub = pytest.emulator.get_emulator_controller()
    pytest.emulator.adb(["shell", "input", "keyevent", "KEYCODE_WAKEUP"])
    stub.setDisplayConfigurations(DisplayConfigurations(displays=[]))
    yield
    stub.setDisplayConfigurations(DisplayConfigurations(displays=[]))


@pytest.mark.e2e
def test_multidisplay_none(no_displays):
    """Erasing displays leaves nothing behind."""
    emu = pytest.emulator.get_emulator_controller()
    cfg = emu.setDisplayConfigurations(DisplayConfigurations(displays=[]))

    # We only have the default display
    assert len(cfg.displays) == 1


@pytest.mark.e2e
def test_multidisplay_multiple(no_displays):
    """Adding a display should work."""
    emu = pytest.emulator.get_emulator_controller()
    cfg = emu.setDisplayConfigurations(
        DisplayConfigurations(
            displays=[
                DisplayConfiguration(width=720, height=1280, dpi=213, display=2),
            ]
        )
    )

    assert len(cfg.displays) == 2
    assert cfg.displays[1].display == 2
    assert cfg.displays[1].dpi == 213
    assert cfg.displays[1].width == 720
    assert cfg.displays[1].height == 1280


@pytest.mark.e2e
def test_multidisplay_multiple_error(no_displays):
    """A failure should not modify the status."""
    emu = pytest.emulator.get_emulator_controller()
    cfg = emu.setDisplayConfigurations(
        DisplayConfigurations(
            displays=[
                DisplayConfiguration(width=720, height=1280, dpi=213, display=2),
            ]
        )
    )

    # We should have the default display, and 1 other.
    assert len(cfg.displays) == 2

    # Incorrectly modifying a display configuration should fail and leave the existing one intact
    with pytest.raises(RpcError) as exc_info:
        cfg = emu.setDisplayConfigurations(
            DisplayConfigurations(
                displays=[
                    DisplayConfiguration(
                        width=99720, height=991280, dpi=213, display=1
                    ),
                ]
            )
        )
    assert exc_info.value.code() == StatusCode.INVALID_ARGUMENT

    # The failure leaves the displays untouched.
    cfg = emu.getDisplayConfigurations(_EMPTY_)
    assert len(cfg.displays) == 2
    assert cfg.displays[1].display == 2
    assert cfg.displays[1].dpi == 213
    assert cfg.displays[1].width == 720
    assert cfg.displays[1].height == 1280


@pytest.mark.e2e
def test_multidisplay_get_after_set(no_displays):
    """Adding a display should work."""
    emu = pytest.emulator.get_emulator_controller()
    cfg = emu.setDisplayConfigurations(
        DisplayConfigurations(
            displays=[
                DisplayConfiguration(width=720, height=1280, dpi=213, display=2),
            ]
        )
    )

    cfg2 = emu.getDisplayConfigurations(_EMPTY_)
    assert cfg == cfg2


@pytest.mark.e2e
def test_multidisplay_double_ids_error(no_displays):
    """Adding the same display twice should result in an error."""
    emu = pytest.emulator.get_emulator_controller()
    with pytest.raises(RpcError) as exc_info:
        emu.setDisplayConfigurations(
            DisplayConfigurations(
                displays=[
                    DisplayConfiguration(width=720, height=1280, dpi=213, display=2),
                    DisplayConfiguration(width=1080, height=1920, dpi=213, display=2),
                ]
            )
        )
    assert exc_info.value.code() == StatusCode.INVALID_ARGUMENT


@pytest.mark.e2e
def test_multidisplay_can_configure_four(no_displays):
    """This tests makes sure that a total of 4 displays can be configured.

    Adding 3 additional displays, should return a total of 4.
    """
    resolutions = [(720, 1280), (1080, 1920), (3840, 2160)]
    displays = [
        DisplayConfiguration(width=x[0], height=x[1], dpi=213, display=idx + 1)
        for idx, x in enumerate(resolutions)
    ]
    emu = pytest.emulator.get_emulator_controller()
    cfg = emu.setDisplayConfigurations(DisplayConfigurations(displays=displays))

    # All screens have been made available.
    assert all([x in cfg.displays for x in displays])

    # We have default screen, + the ones we added.
    assert len(cfg.displays) == len(displays) + 1


@pytest.mark.e2e
def test_multidisplay_error_too_many(no_displays):
    """Adding too many displays should raise an exception."""
    emu = pytest.emulator.get_emulator_controller()
    resolutions = [(720, 1280), (1080, 1920), (3840, 2160), (900, 900)]
    displays = [
        DisplayConfiguration(width=x[0], height=x[1], dpi=213, display=idx + 1)
        for idx, x in enumerate(resolutions)
    ]
    with pytest.raises(RpcError):
        emu.setDisplayConfigurations(DisplayConfigurations(displays=displays))
