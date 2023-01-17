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
import logging
import os
import shutil
import sys
from pathlib import Path

import pytest
from aemu.proto.emulator_controller_pb2 import (
    KeyboardEvent,
    ParameterValue,
    PhysicalModelValue,
)

from emu.apk import APP_DEBUG_APK
from emu.emulator import BaseEmulator, DebugEmulator, Emulator
from emu.utils import system_cpu
from tests.test_utils import wait_for_regex


def pytest_addoption(parser):
    """This parses the options that are passed in to pytest."""
    parser.addoption(
        "--emulator",
        action="store",
        default="/Users/jansene/src/emu/external/qemu/objs/emulator",
        # DO NOT SUBMIT
        # shutil.which(
        #     "emulator",
        #     Path(os.environ["ANDROID_HOME"] or os.environ["ANDROID_SDK_ROOT"] or ".")
        #     / "emulator"
        #     / "emulator",
        # ),
        help="The emulator used to run the integration tests against.",
    )
    parser.addoption(
        "--android_avd_home",
        action="store",
        default=str(Path.home() / ".android" / "avd"),
        help="The the path to the directory that contains all AVD-specific files,"
        "which mostly consist of very large disk images."
        "The default location is ~/.android/avd "
        "The tests will create and delete a set of avds needed to run the tests in this directory.",
    )
    parser.addoption(
        "--android_home",
        action="store",
        default=os.environ["ANDROID_HOME"] or os.environ["ANDROID_SDK_ROOT"],
        help="The path to the SDK installation directory. This should contain system-images and adb.",
    )
    parser.addoption(
        "--debug_emulator",
        action="store_true",
        help="Connect to the first available emulator for debugging. "
        "Use this if you have launched you own emulator and want to run the tests against that instance.",
    )
    parser.addoption(
        "--debug_emulator_log",
        action="store",
        help="A file that contains the emulator stdout/stderr."
        "This should point to a file containing the logs produced by the running emulator."
        "For example launching the emulator like <path-to-emulator>/emulator @31 | tee /tmp/log_file",
    )
    parser.addoption(
        "--stream_test_time",
        type=int,
        default=30,
        help="Number of seconds the frame perf test should last.",
    )


ALL_PLATFORMS = set("darwin linux win32".split())


def pytest_runtest_setup(item):
    """Only run the test if it is supported on the platform."""
    supported_platforms = ALL_PLATFORMS.intersection(
        mark.name for mark in item.iter_markers()
    )
    plat = sys.platform
    if supported_platforms and plat not in supported_platforms:
        pytest.skip("cannot run on platform {}".format(plat))


# Workaround for
# https://docs.pytest.org/en/latest/deprecations.html#pytest-namespace
def pytest_configure():
    pytest.emulator = None
    pytest.emulators = {}


def pytest_sessionfinish(session, exitstatus):
    """Stops and remove all running emulators at the end of all tests."""
    for name, emu in pytest.emulators.items():
        logging.info("Shutting down and removing %s", name)
        emu.disconnect()
        emu.stop()
        emu.delete()


# -------------------------------
# Session wide fixtures are below
# -------------------------------
@pytest.fixture(scope="module")
def emulator(request, pytestconfig) -> BaseEmulator:
    """Makes a configured emulator available

    Note: You usually don't need fixture, as it will be automatically provided
    if you use any of the dependent fixtures.

    See tests/snapshot/test_snaphshot_downloads.py for an example of how
    you could use this fixture to have fine-grained control of the emulator.

    This makes an emulator available with the following default configuration:
    {
        "api": "31",
        "tag.id": "google_apis",
        "cpu": system_cpu()
    }

    You can provide your own avd configuration, by defining the variable
    avd_config = { ... } in your test module (i.e. test_xx.py)

    The avd_config should contain a dictionary with all the values that you
    would like to override in the config.ini that should be generated.

    You should provide at least the following parameters:

    - "api": The api level of the emulator you wish to run
    - "tag.id": The tag of the system image that should be used.

    The abi will be derived from the platform of the current running system.
    For x64 this will be x86_64 and for M1 this will be arm64_v8a

    This information will be used to obtain the system image:

    "system-images;android-{};{};{}".format(api, tag, abi)

    using sdkmanager that ships with the android sdk.

    For example, the default configuration mentioned above will result in the
    installation of the following avd:

    sdkmanager "system-images;android-31;google_apis;arm64-v8a"

    A created avd will remain running until all the tests completed, this means
    that multiple emulators can be running during a test run.

    At the end of the test run all the created emulators, and associated avds
    will be deleted.
    """
    avd_config = {
        "api": "31",
        "tag.id": "google_apis",
        "cpu": system_cpu(),
    }
    avd_user_config = getattr(request.module, "avd_config", {})
    avd_config.update(avd_user_config)
    name = "{}_{}_{}".format(avd_config["api"], avd_config["tag.id"], avd_config["cpu"])

    if name not in pytest.emulators:
        logging.info("Launching %s", name)
        if pytestconfig.getoption("debug_emulator"):
            emu = DebugEmulator(
                android_home=Path(pytestconfig.getoption("android_home")),
                android_avd_home=Path(pytestconfig.getoption("android_avd_home")),
                logfile=pytestconfig.getoption("debug_emulator_log"),
            )
        else:
            emu = Emulator(
                android_home=Path(pytestconfig.getoption("android_home")),
                android_avd_home=Path(pytestconfig.getoption("android_avd_home")),
                exe=Path(pytestconfig.getoption("emulator")),
                avd_config=avd_config,
            )

        pytest.emulators[name] = emu

    logging.info("Got the emu object: %s!", pytest.emulators[name])
    return pytest.emulators[name]


@pytest.mark.timeout(600)
@pytest.fixture
def avd(emulator: BaseEmulator) -> BaseEmulator:
    """Makes a booted emulator accessible and with the animation apk installed.

    An emulator gets 600 seconds to boot up.


    Args:
        emulator (BaseEmulator): Test fixture that provides the configured emulator.

    Returns:
        BaseEmulator: A successfully booted emulator.
    """

    assert emulator
    if not emulator.is_alive():
        emulator.launch(flags=[])

    # Make sure the emulator is booted in at least 10 minutes.
    # (Note, boot times can be *REALLY* slow on windows gce..)
    assert emulator.wait_for_boot(600)

    emulator.install_apk(APP_DEBUG_APK.absolute())
    return emulator


def go_home(avd: BaseEmulator):
    """It does the following:

    1. Wakes up the emulator by sending a WAKEUP
    2. Press the android home key (The circle button)
    3. Rotate the phone to 0,0,0

    Usage:

    def my_test(go_home):
        assert(...)
    """
    assert avd.is_alive()

    stub = avd.description.get_emulator_controller()
    avd.adb.run(["shell", "input", "keyevent", "KEYCODE_WAKEUP"])
    stub.sendKey(KeyboardEvent(key="GoHome", eventType=KeyboardEvent.keypress))
    stub.setPhysicalModel(
        PhysicalModelValue(
            target=PhysicalModelValue.ROTATION,
            value=ParameterValue(data=[0, 0, 0]),
        )
    )


@pytest.fixture
def at_home(avd: BaseEmulator):
    """This calls the go_home fixture before running the test,
    and after running the test.

    This makes sure that the emulator ends up in a known state
    after the test.

    Usage:

    def test_goes_home(go_home):
        assert(...)
    """
    assert avd.is_alive()

    go_home(avd)
    yield
    go_home(avd)


@pytest.fixture
def emulator_log(avd: BaseEmulator):
    """Returns the emulator log as a Queue (https://docs.python.org/3/library/queue.html)
    This contains the output seen on the console when the emulator is launched.

    The queue (log) will be emptied first.

    Usage:

    def test_logs_line(emulator_log):
        line = emulator_log.get(block=True, timeout=1.5)
        assert line == 'INFO    | Started GRPC server at 127.0.0.1:8554, security: Local, auth: none'
    """
    assert avd.is_alive()

    if avd.log:
        while not avd.log.empty():
            avd.log.get(False)
    return avd.log


def launch_animiation_app(avd: BaseEmulator):
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
    assert avd.is_alive()

    avd.adb.run(["logcat", "-c"])
    avd.adb.run(["shell", "input", "keyevent", "KEYCODE_WAKEUP"])
    avd.adb.run(["shell", "am", "force-stop", "com.google.AnimateBox"])
    with avd.adb.stream(["logcat", "-s", "aemu"]) as stream:
        avd.adb.run(
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
def emulator_controller(avd: BaseEmulator):
    """A grpc stub to the emulator controller.

    Usage:

    def test_sample(emulator_controller):
        response = emulator_controller.getStatus(empty_pb2.Empty())
        assert response.booted
    """
    assert avd.is_alive()

    ctrl = avd.description.get_emulator_controller()
    return ctrl


@pytest.fixture
def animation_app(avd: BaseEmulator):
    """Activates the animation app that displays a rotating triangle.

     The app does the following things:

     1. Show a rotating triangle (60 fps)
     2. Show a white box in the corner.
     3. Write every received key event to logcat.

    The app will be stopped at the end of the test, and will return
    the emulator to the home screen.

    Usage:

    def test_sample(animation_app, emulator_controller):
        emulator_controller.getScreenshot(ImageFormat(format=ImageFormat.PNG, width=180, height=180))

    """
    assert avd.is_alive()

    tries = 3
    while not launch_animiation_app(avd) and tries > 0:
        tries = tries - 1

    assert tries >= 0, "Unable to successfully launch the animation app."
    yield

    avd.adb.run(["shell", "am", "force-stop", "com.google.AnimateBox"])
    go_home(avd)


@pytest.fixture
def adb(avd: BaseEmulator):
    """Function that invokes the adb executable with the given parameters.

    Usage:

    def test_sample(adb):
        adb(["emu", "rotate"])
    """
    assert avd.is_alive()

    return avd.adb.run


@pytest.fixture
def telnet(avd: BaseEmulator):
    """Access to the telnet console of the current emulator.

    Usage:

    def test_sample(telnet):
        telnet.send("event text")
    """
    assert avd.is_alive()

    return avd.console()
