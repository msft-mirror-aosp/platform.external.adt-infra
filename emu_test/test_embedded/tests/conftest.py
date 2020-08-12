import os
import re

import pytest

from aemu.proto.emulator_controller_pb2 import KeyboardEvent
from emu.emulator import Emulator
from tests.test_utils import StreamingCall, time_to_str


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


# Workaround for
# https://docs.pytest.org/en/latest/deprecations.html#pytest-namespace
def pytest_configure():
    pytest.emulator = None


@pytest.fixture(scope="session", autouse=True)
@pytest.mark.timeout(60)
def startup_emulator(request, pytestconfig):
    """Starts the emulator and makes it globally accessible.

    Will timeout after 60s, or fail if it was not booted.
    """
    emu = Emulator(pytestconfig.getoption("emulator"))
    if pytestconfig.getoption("debug_emulator"):
        emu.first_running()
    else:
        emu.launch_like_studio()
        emu.adb(["kill-server"])
        emu.adb(["start-server"])
        assert emu.wait_for_boot()

    def stop_telnet_console():
        pytest.emulator.disconnect()

    def teardown_emulator():
        pytest.emulator.stop()

    pytest.emulator = emu
    request.addfinalizer(stop_telnet_console)
    if not pytestconfig.getoption("debug_emulator"):
        request.addfinalizer(teardown_emulator)

    emu.adb(["install", os.path.join(Emulator.here, "apk", "app-debug.apk")])

@pytest.fixture
def at_home():
    """Fixture to make sure the emulator returns to the home screen.

       Use this if you want to make sure the emulator returns to the
       home screen.
    """
    stub = pytest.emulator.get_emulator_controller()
    stub.sendKey(KeyboardEvent(key="GoHome", eventType=KeyboardEvent.keypress))
    yield
    stub.sendKey(KeyboardEvent(key="GoHome", eventType=KeyboardEvent.keypress))


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


@pytest.fixture
def animation_app():
    """Activates the animation apk.

    The apk will be closed upon completion, and you will return to home.
    """

    def _wait_for_launch(stream):
        """Waits until the timing entry has been written by our app."""
        TIMING_RE = re.compile(r".*Timing: (\d+), (\d+)")
        for line in iter(stream.get, None):
            m = TIMING_RE.match(line)
            if m:
                return int(m.group(1)), int(m.group(2))

    emu = pytest.emulator
    emu.adb(["logcat", "-c"])
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
        _wait_for_launch(stream)

    yield
    emu.adb(["shell", "am", "force-stop", "com.google.AnimateBox"])
    emu.get_emulator_controller().sendKey(
        KeyboardEvent(key="GoHome", eventType=KeyboardEvent.keypress)
    )
