# -*- coding: utf-8 -*-
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
import platform
import time
import threading
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
from emu.crashreporter import CrashReporter
from emu.utils import system_cpu


OS_NAME = platform.system().lower()
AOSP_ROOT = Path(os.path.dirname(__file__)).absolute().parents[4]
SDK_EMULATOR = (
    AOSP_ROOT / "prebuilts" / "android-emulator-build" / "system-images" / OS_NAME
)


def pytest_addoption(parser):
    """This parses the options that are passed in to pytest."""
    parser.addoption(
        "--emulator",
        action="store",
        help="The emulator used to run the integration tests against.",
    )
    parser.addoption(
        "--symbols",
        action="store",
        help="Location where the breakpad symbols that belong to this emulator can be found.",
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
        default=os.environ.get("ANDROID_HOME")
        or os.environ.get("ANDROID_SDK_ROOT")
        or SDK_EMULATOR,
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
    parser.addoption(
        "--avd_keep",
        action="store_true",
        help="Do not delete the created avds. Useful if you need to debug snapshot related issues.",
    )


ALL_PLATFORMS = set("darwin linux win32".split())


def log_thread_error(args):
    """
    Logs an unhandled exception in a thread.

    Args:
        args: The arguments passed to the excepthook.

    Returns:
        None.
    """
    exctype, value, traceback, thread = args
    logging.error(
        "Unhandled exception in thread: %s",
        thread.name,
        exc_info=(exctype, value, traceback),
    )


threading.excepthook = log_thread_error


def pytest_runtest_setup(item: pytest.Item) -> None:
    """
    Check whether the test is supported on the platform and log the setup information
    for the test.

    Args:
        item (pytest.Item): The test item.
    """
    supported_platforms = ALL_PLATFORMS.intersection(
        mark.name for mark in item.iter_markers()
    )
    plat = sys.platform
    if supported_platforms and plat not in supported_platforms:
        pytest.skip(f"cannot run {item.name} on platform {plat}")

    logging.info("=============== Setup: %s ===============", item.name)


def pytest_runtest_teardown(item: pytest.Item) -> None:
    """
    Log the teardown information for the test.

    Args:
        item (pytest.Item): The test item.
    """
    logging.info("=============== Teardown: %s ===============", item.name)


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    """
    Log the result of the test.

    Args:
        report (pytest.TestReport): The test report.
    """
    if report.when == "call":
        logging.info(
            "-----------> %s completed: %s <-----------", report.nodeid, report.outcome
        )


# Workaround for
# https://docs.pytest.org/en/latest/deprecations.html#pytest-namespace
def pytest_configure(config):
    """Configure pytest, this method is run before any tests is run."""
    pytest.emulator = None
    pytest.emulators = {}


def pytest_sessionfinish(
    session,
    exitstatus,
):
    """Stops and remove all running emulators at the end of all tests."""
    for name, emu in pytest.emulators.items():
        logging.info("Shutting down and removing %s", name)
        emu.disconnect()
        emu.stop()
        if not session.config.getoption("avd_keep"):
            emu.delete()


def get_crash_reporter(pytestconfig):
    exe = pytestconfig.getoption("emulator")
    emulator_directory = Path(exe).parent if exe else None
    return CrashReporter(emulator_directory, pytestconfig.getoption("symbols"))


@pytest.fixture(autouse=True)
def crash_reporter(pytestconfig):
    """A fixture to handle crash reports in the emulator.

    This fixture returns the crash reporter associated with the emulator,
    which can be used to list, print, upload, and delete crash reports.
    The scope of the fixture is session and it is
    automatically used in all test functions.

    The fixture also writes the crash reports to disk if the `log_file` option is
    provided. If not, it lists all the crashes instead.

    Note: This fixtures is automatically attached to every test
    that is running.

    Args:
        pytestconfig (object): Pytest configuration object

    Yields:
        CrashReporter: An instance of the CrashReporter class
    """
    log_file = pytestconfig.getoption("--log-file")
    crash_report = get_crash_reporter(pytestconfig)
    crash_report.clear()
    yield crash_report

    # Report crashes on the log
    crash_report.list_crashes()
    if log_file and Path(log_file).exists():
        log_dir = Path(log_file).parent
        crash_report.write_reports_to_disk(log_dir)

    crash_report.clear()


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
        "avd.ini.displayname": "°º¤ø,¸¸,ø¤º°`°º¤ø, UTF-8 ¸,ø¤°º¤ø,¸¸,ø¤º°`°º¤ø,¸",
        "device.name": "Pixel2",
    }
    avd_user_config = getattr(request.module, "avd_config", {})
    avd_config.update(avd_user_config)
    name = f"{avd_config['api']}_{avd_config['tag.id']}_{avd_config['cpu']}_{avd_config['device.name']}"

    if name not in pytest.emulators:
        if pytestconfig.getoption("debug_emulator") or not pytestconfig.getoption(
            "emulator"
        ):
            emu = DebugEmulator(
                android_home=Path(pytestconfig.getoption("android_home")),
                android_avd_home=Path(pytestconfig.getoption("android_avd_home")),
                logfile=pytestconfig.getoption("debug_emulator_log"),
            )
        else:
            logging.info("Launching %s", name)
            exe = Path(pytestconfig.getoption("emulator"))
            emu = Emulator(
                android_home=Path(pytestconfig.getoption("android_home")),
                android_avd_home=Path(pytestconfig.getoption("android_avd_home")),
                exe=exe,
                avd_config=avd_config,
            )

        emu.symbols = pytestconfig.getoption("symbols")
        pytest.emulators[name] = emu

    return pytest.emulators[name]


@pytest.mark.timeout(600)
@pytest.fixture(scope="module")
def avd(emulator: BaseEmulator, request) -> BaseEmulator:
    """Makes a booted emulator accessible and with the animation apk installed.

    Note that the following holds:

    - This fixture has module scope, meaning an emulator will be launched only once
      per package

    - The emulator will be (re-)started if needed.

    - You can provide the "param" property on the request to provide additional
      flags to the emulator during re-start.

    Args:
        emulator (BaseEmulator): Test fixture that provides the configured emulator.
        request: Provide information on the executing test function.

    Returns:
        BaseEmulator: A successfully booted emulator with the debug apk installed.
    """
    if hasattr(request, "param"):
        emulator.restart([request.param])
    else:
        emulator.restart([])

    # Make sure the emulator is booted in at least 10 minutes.
    # (Note, boot times can be *REALLY* slow on windows gce..)
    assert emulator.wait_for_boot(timeout=600)

    assert emulator.install_apk(APP_DEBUG_APK.absolute(), "com.google.AnimateBox")
    emulator.reset_state()

    yield emulator

    # Stop the emulator.
    emulator.stop()


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

    It will wait for at most 10 seconds before continuing.
    """
    assert avd.is_alive()
    assert avd.stop_activity("com.google.AnimateBox")
    with avd.adb.logcat(tag="aemu", clear=True, timeout=10) as stream:
        assert avd.start_activity("com.google.AnimateBox/com.google.emu.MainActivity")
        for line in stream:
            if "--STARTED--" in line:
                return True

    logging.warning("The animation app has not been launched.")
    return False


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
def service(avd: BaseEmulator):
    """A grpc stub to the emulator of the given type

    Usage:

    def test_sample(service):
        stub = service(SensorServiceStub)
        stub.method_call
    """

    def service(klazz):
        channel = avd.description.get_grpc_channel()
        return klazz(channel)

    return service


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

    avd.reset_state()
    tries = 3
    while not launch_animiation_app(avd) and tries > 0:
        time.sleep(1)
        tries = tries - 1

    assert tries >= 0, "Unable to successfully launch the animation app."
    yield

    avd.stop_activity("com.google.AnimateBox")
    avd.reset_state()


@pytest.fixture
def coldboot_animation_app(avd: BaseEmulator):
    """Similar to animation_app, but do it with cold boot"""
    avd.stop()
    assert avd.launch(flags=["-no-snapshot-load"])
    assert avd.wait_for_boot(timeout=600)

    assert avd.is_alive()

    # sleep a few seconds so that system ui have updated
    # time, lte signal and so on; we are doing a cold boot
    # and this extra seconds seems reasonable
    time.sleep(10)

    tries = 3
    while not launch_animiation_app(avd) and tries > 0:
        time.sleep(1)
        tries = tries - 1

    assert tries >= 0, "Unable to successfully launch the animation app."
    yield

    avd.stop_activity("com.google.AnimateBox")


@pytest.fixture
def adb_shell(avd: BaseEmulator):
    """Function that invokes the adb executable with the given parameters.

    Usage:

    def test_sample(adb_shell):
        adb_shell("input keyevnet KEYCODE_WAKEUP")
    """
    assert avd.is_alive()
    return avd.adb.shell


@pytest.fixture
def telnet(avd: BaseEmulator):
    """Access to the telnet console of the current emulator.

    Usage:

    def test_sample(telnet):
        telnet.send("event text")
    """
    assert avd.is_alive()
    return avd.console()


@pytest.fixture
def at_home(avd: BaseEmulator):
    avd.reset_state()
    yield
    avd.reset_state()
