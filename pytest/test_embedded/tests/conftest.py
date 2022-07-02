# Copyright 2022 The Android Open Source Project
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

"""
This contains a set of text fixtures that can be used when creating pytests.
(see https://docs.pytest.org/en/6.2.x/fixture.html)

A fixture initialize test functions.  They provide a fixed baseline so that tests
execute reliably and produce consistent, repeatable, results. Initialization may
setup services, state, or other operating environments.

The fixtures below can be used to bring the emulator to a certain state, or to
provide access to parts of the emulator.
"""
import os
import pytest
import sys

from aemu.proto.emulator_controller_pb2 import (
    KeyboardEvent,
    ParameterValue,
    PhysicalModelValue,
    Rotation,
)
from emu.emulator import Emulator

from tests.test_utils import wait_for_regex


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
        default=30,
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

    Startup is run before any test is run, and will do the following:

    1. Create a Pixel2 avd if it does not exist.
    2. Launch the emulator, unless the -debug_emulator flag is present
    3. Install the app-debug.apk
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
    """It does the following:

    1. Wakes up the emulator by sending a WAKEUP
    2. Press the android home key (The circle button)
    3. Rotate the phone to 0,0,0

    Usage:

    def my_test(go_home):
        assert(...)
    """
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
    """This calls the go_home fixture before running the test,
    and after running the test.

    This makes sure that the emulator ends up in a known state
    after the test.

    Usage:

    def test_goes_home(go_home):
      assert(...)
    """
    go_home()
    yield
    go_home()


@pytest.fixture
def emulator_log():
    """Returns the emulator log as a Queue (https://docs.python.org/3/library/queue.html)
    This contains the output seen on the console when the emulator is launched.

    The queue (log) will be emptied first.

    Usage:

    def test_logs_line(emulator_log):
     line = emulator_log.get(block=True, timeout=1.5)
     assert line == 'INFO    | Started GRPC server at 127.0.0.1:8554, security: Local, auth: none'
    """
    emu = pytest.emulator
    if emu.log:
        while not emu.log.empty():
            emu.log.get(False)
    return emu.log


def launch_animiation_app():
    """Launches the debug animation app.

    This launches the animation app that ships with this library and
    waits until it has launched. It will:

    - Clear out logcat
    - Wake-up the emulator (by sending the wakup code)
    - Force stop any existing running animation app
    - Start the activity
    - Wait for the welcome message to appear on logcat.

    It will wait for at most 5 seconds before continuing.
    """
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
        return wait_for_regex(stream, r".*Timing: (\d+), (\d+)", 5)


@pytest.fixture
def emulator_controller():
    """A grpc stub to the emulator controller.

    Usage:

    def test_sample(emulator_controller):
       response = emu_controller.getStatus(empty_pb2.Empty())
       assert response.booted
    """
    return pytest.emulator.get_emulator_controller()


@pytest.fixture
def animation_app():
    """Activates the animation app that displays a rotating triangle.

     The app does the following things:

     1. Show a rotating triangle (60 fps)
     2. Show a white box in the corner.
     3. Write every received key event to logcat.

    The app will be stopped at the end of the test, and will return
    the emulator to the home screen.

    Usage:

     def test_sample(animation_app, emu_controller):
       emu_controller.getScreenshot(ImageFormat(format=ImageFormat.PNG, width=180, height=180))

    """
    tries = 3
    while not launch_animiation_app() and tries > 0:
        tries = tries - 1

    assert tries >= 0, "Unable to successfully launch the animation app."
    yield

    pytest.emulator.adb(["shell", "am", "force-stop", "com.google.AnimateBox"])
    go_home()


@pytest.fixture
def adb():
    """Function that invokes the adb executable with the given parameters.
    
       Usage:

    def test_sample(adb):
       adb(["emu", "rotate"])
       assert response.booted
    """
    return pytest.emulator.adb

@pytest.fixture
def telnet():
    """Access to the telnet console of the current emulator.
    
       Usage:

    def test_sample(telnet):
       telnet.send("event text")
    """
    return pytest.emulator.get_telnet()

ALL_PLATFORMS = set("darwin linux win32".split())

def pytest_runtest_setup(item):
    """Only run the test if it is supported on the platform."""
    supported_platforms = ALL_PLATFORMS.intersection(
        mark.name for mark in item.iter_markers()
    )
    plat = sys.platform
    if supported_platforms and plat not in supported_platforms:
        pytest.skip("cannot run on platform {}".format(plat))
