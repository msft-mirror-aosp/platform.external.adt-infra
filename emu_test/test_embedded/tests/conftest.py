import os
import re
import time

import pytest

from aemu.proto.emulator_controller_pb2 import (
    ImageFormat,
    KeyboardEvent,
    ParameterValue,
    PhysicalModelValue,
    Rotation,
)
from emu.emulator import Emulator


def pytest_addoption(parser):
    parser.addoption(
        "--emulator",
        action="store",
        default=os.path.join(
            os.environ.get("ANDROID_SDK_ROOT", "."), "emulator", "emulator"
        ),
        help="Launch the emulator using the given path.",
    )
    parser.addoption(
        "--test_dir",
        action="store",
        default=os.path.join(os.path.dirname(__file__), "..", "event_logger_apk"),
    )
    parser.addoption(
        "--debug_emulator",
        action="store_true",
        help="Connect to the first available emulator for debugging.",
    )
    parser.addoption(
        "--debug_emulator_log",
        action="store",
        help="A file that contains the emulator stdout/stderr",
    )
    parser.addoption(
        "--stream_test_time",
        type=int,
        default=10,
        help="Number of seconds the frame perf test should last.",
    )


# Workaround for
# https://docs.pytest.org/en/latest/deprecations.html#pytest-namespace
def pytest_configure():
    pytest.emulator = None


@pytest.fixture(scope="session", autouse=True)
@pytest.mark.timeout(600)
def startup_emulator(request, pytestconfig):
    """Starts the emulator and makes it globally accessible.

    Will timeout after 600s, or fail if it was not booted.
    """
    emu = Emulator(pytestconfig.getoption("emulator"))
    if pytestconfig.getoption("debug_emulator"):
        emu.first_running(pytestconfig.getoption("debug_emulator_log"))
    else:
        emu.launch_like_studio()

    # Make sure the emulator is booted.
    assert emu.wait_for_boot()
    pytest.emulator = emu

    def stop_telnet_console():
        pytest.emulator.disconnect()

    def teardown_emulator():
        pytest.emulator.stop()

    request.addfinalizer(stop_telnet_console)
    if not pytestconfig.getoption("debug_emulator"):
        request.addfinalizer(teardown_emulator)

    emu.check_adb()
    emu.adb(["install", os.path.join(Emulator.here, "apk", "app-debug.apk")])


def go_home():
    stub = pytest.emulator.get_emulator_controller()
    pytest.emulator.adb(["shell", "input", "keyevent", "KEYCODE_WAKEUP"])
    stub.sendKey(KeyboardEvent(key="GoHome", eventType=KeyboardEvent.keypress))
    stub.setPhysicalModel(
        PhysicalModelValue(
            target=PhysicalModelValue.ROTATION,
            value=ParameterValue(data=[0, 0, 0]),
        )
    )


@pytest.fixture
def at_home():
    """Fixture to make sure the emulator returns to the home screen and is in portrait mode.

    Use this if you want to make sure the emulator returns to the
    home screen.
    """
    go_home()
    yield
    go_home()


@pytest.fixture
def emulator_log():
    """Returns the emulator log.

    The log will be emptied first.
    """
    emu = pytest.emulator
    if emu.log:
        while not emu.log.empty():
            emu.log.get(False)
    return emu.log


def launch_animiation_app():
    def _wait_for_launch(stream, max_wait):
        """Waits until the timing entry has been written by our app."""
        TIMING_RE = re.compile(r".*Timing: (\d+), (\d+)")
        timeout = time.time() + max_wait
        for line in iter(stream.get, None):
            m = TIMING_RE.match(line)
            if timeout > time.time():
                return -1, -1

            if m:
                return int(m.group(1)), int(m.group(2))

    emu = pytest.emulator
    emu.adb(["logcat", "-c"])
    emu.adb(["shell", "input", "keyevent", "KEYCODE_WAKEUP"])
    emu.adb(["shell", "am", "force-stop", "com.google.AnimateBox"])
    with emu.adb_stream(["logcat", "-s", "aemu"]) as stream:
        emu.adb(
            [
                "shell",
                "am",
                "start",
                "-n",
                "com.google.AnimateBox/com.google.emu.MainActivity",
            ]
        )
        return _wait_for_launch(stream, 5) != -1, -1


@pytest.fixture
def animation_app():
    """Activates the animation apk.

    The apk will be closed upon completion, and you will return to home.
    """
    tries = 3
    while not launch_animiation_app() and tries > 0:
        tries = tries - 1

    yield

    pytest.emulator.adb(["shell", "am", "force-stop", "com.google.AnimateBox"])
    go_home()
