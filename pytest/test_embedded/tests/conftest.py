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
import re
import sys
import json
import threading
import time
from pathlib import Path

import pytest
from aemu.proto.emulator_controller_pb2 import ImageFormat

from emu.apk import APP_DEBUG_APK, APP_MOBLY_APK
from emu.crashreporter import CrashReporter
from emu.emulator import BaseEmulator, DebugEmulator, Emulator
from emu.images.convert import save_image
from emu.utils import system_cpu
from tests.test_utils import StreamingCall
import xml.etree.ElementTree as ET

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
        "--avd_config",
        default="{}",
        help="A JSON snippet that contains the avd configuration that should be used to run this test",
    )
    parser.addoption(
        "--emulator_launch_flags",
        default="[]",
        help="A JSON snippet that contains the avd configuration that should be used to run this test",
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
    parser.addoption(
        "--build_target",
        action="store",
        help="The build target name.",
    )


ALL_PLATFORMS = set("darwin linux win32".split())

SKIPOS_PLATFORMS = "win linux mac m1 all".split()


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
    Check whether the test is supported on the platform, handle
    custom markers and log the setup information.

    Args:
        item (pytest.Item): The test item.
    """
    supported_platforms = ALL_PLATFORMS.intersection(
        mark.name for mark in item.iter_markers()
    )
    plat = sys.platform
    if supported_platforms and plat not in supported_platforms:
        pytest.skip(f"cannot run {item.name} on platform {plat}")

    # Handle the 'skipos' marker.
    markers = [marker for marker in item.iter_markers() if marker.name in "skipos"]
    for marker in markers:
        if len(marker.args) == 0:
            pytest.exit("The 'skipos' marker needs at least one argument.")
        platforms = marker.args[0].lower()
        platforms = platforms.replace(" ", "").split(",")

        for plat in platforms:
            if plat == pytest.os or plat == "all":
                if len(marker.args) > 1:
                    pytest.skip(marker.args[1])
                elif "reason" in marker.kwargs:
                    pytest.skip(marker.kwargs["reason"])
                else:
                    pytest.skip()

    # Process the 'timeout_win' marker
    timeout_win = item.get_closest_marker("timeout_win")
    if timeout_win and pytest.os == "win":
        timeout_win_sec = (
            timeout_win.args[0]
            if timeout_win.args
            else timeout_win.kwargs.get("timeout")
        )
        func_only = timeout_win.kwargs.get("func_only", True)
        # Remove existing timeout marker
        timeout = [
            m
            for m, marker in enumerate(item.iter_markers())
            if marker.name == "timeout"
        ]
        if timeout:
            item.own_markers.pop(timeout[0])

        item.add_marker(
            pytest.mark.timeout(timeout=timeout_win_sec, func_only=func_only)
        )

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
    pytest.system = platform.system()
    pytest.processor = platform.processor()

    # Register the 'skipos' marker.
    config.addinivalue_line(
        "markers",
        (
            "skipos(platform, reason=None): "
            "skip the given test for the given platform. "
            "Valid platform values and systems are: "
            "'win' (Windows), 'linux' (Linux), 'mac' (macOS), "
            "'m1' (macOS aarch64). "
            "Multiple OS values are accepted, such as 'win, linux'. "
            "To skip the test in all platforms, use the 'all' option."
        ),
    )
    os_map = {
        "Windows": "win",
        "Linux": "linux",
        "Darwin": "m1" if pytest.processor == "arm" else "mac",
    }
    # Current skipos platform
    pytest.os = os_map.get(pytest.system, "unknown")

    # Register the 'timeout_win' marker
    config.addinivalue_line(
        "markers",
        "timeout_win(timeout): "
        "Set a timeout for Windows platforms (overrides an existing timeout).",
    )


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

    cfg = pytestconfig.getoption("avd_config")
    logging.info("Using avd config:%s", cfg)
    avd_param_config = json.loads(cfg)
    avd_config.update(avd_param_config)
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
def avd(emulator: BaseEmulator, request, pytestconfig) -> BaseEmulator:
    """Makes a booted emulator accessible and with the animation apk installed.

    Note that the following holds:

    - This fixture has module scope, meaning an emulator will be launched only once
      per package

    - The emulator will be (re-)started if needed.

    Args:
        emulator (BaseEmulator): Test fixture that provides the configured emulator.
        request: Provide information on the executing test function.

    Returns:
        BaseEmulator: A successfully booted emulator with the debug apk installed.
    """
    emulator_launch_flags = json.loads(pytestconfig.getoption("emulator_launch_flags"))
    emulator.restart(emulator_launch_flags)

    # Make sure the emulator is booted in at least 10 minutes.
    # (Note, boot times can be *REALLY* slow on windows gce..)
    assert emulator.wait_for_boot(timeout=600)

    assert emulator.install_apk(APP_DEBUG_APK.absolute(), "com.google.AnimateBox")
    assert emulator.install_apk(
        APP_MOBLY_APK.absolute(), "com.google.android.mobly.snippet.bundled"
    )
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
        avd.log.readlines()
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
        assert avd.start_activity(
            "com.google.AnimateBox/com.google.emu.MainActivity", params=None
        )
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


@pytest.fixture
def mbs(avd: BaseEmulator):
    avd.mobly().load_snippet(
        name="mbs", package="com.google.android.mobly.snippet.bundled"
    )
    return avd.mobly().mbs


@pytest.fixture(scope="session")
def log_directory(pytestconfig):
    """Get the directory from value of the --log-file option, or the current working directory."""
    log_file = pytestconfig.getoption("--log-file")
    if log_file:
        return Path(log_file).parent

    return Path.cwd()


@pytest.fixture
def get_screenshot(emulator_controller, log_directory, request):
    def do_get_screenshot(image_format: ImageFormat):
        """Get a screenshot from the emulator and save it to a file.

        Args:
            image_format: The format of the screenshot image.

        Returns:
            A tuple of the raw screenshot image and the Pillow image object.
        """
        screenshot_dir = Path(log_directory) / "screenshots"
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        img = emulator_controller.getScreenshot(image_format)
        file_name = re.sub(r"[\\/\{\}:]", "_", request.node.nodeid)
        pillow_image = save_image(img, screenshot_dir.absolute(), file_name)
        return img, pillow_image

    return do_get_screenshot


@pytest.fixture
def stream_screenshot(emulator_controller, log_directory, request):
    class StreamingImageCall(StreamingCall):
        def __init__(self, image_format: ImageFormat):
            super().__init__(emulator_controller.streamScreenshot(image_format))
            self.test_name = re.sub(r"[\\/\{\}:]", "_", request.node.nodeid)
            self.screenshot_dir = Path(log_directory) / "screenshots"
            self.screenshot_dir.mkdir(parents=True, exist_ok=True)

        def _enqueue(self, incoming_message):
            save_image(incoming_message, self.screenshot_dir, self.test_name)
            self._queue.put(incoming_message)

    def streaming_img_call(image_format: ImageFormat):
        return StreamingImageCall(image_format)

    return streaming_img_call


@pytest.fixture(scope="session", autouse=True)
def generate_skip_report(skipped_tests, log_directory):
    """Generate a xml report containing the tests currently skipped on each platform.

    Args:
        skipped_tests: Fixture that provides the skipped tests by platform.
        log_directory: Pytest's internal request fixture with test function information.
    """
    xml_report_filepath = log_directory.joinpath(log_directory.name + '_skip.xml')
    if xml_report_filepath.exists():
        # Avoid the fixture running on every re-run (pytest b/#51)
        # https://github.com/pytest-dev/pytest-rerunfailures/issues/51
        return
    xml_testsuite = ET.Element('testsuite')
    xml_testsuite.set('name', log_directory.name)
    xml_platforms = ET.SubElement(xml_testsuite, 'platforms')
    fullname_map = {"win": "Windows", "linux": "Linux", "mac": "Mac Intel",
                     "m1": "Mac M1", "all": "All platforms"}
    for os_, tests in skipped_tests.items():
        xml_platform = ET.SubElement(xml_platforms, 'platform')
        xml_platform.set('name', os_)
        xml_platform.set('fullname', fullname_map.get(os_, 'Unknown'))
        for test in tests:
            xml_test = ET.SubElement(xml_platform, 'test')
            for property in ['name', 'reason', 'nodeid']:
                xml_test_child = ET.SubElement(xml_test, property)
                xml_test_child.text = str(test[property])

    xml_tree = ET.ElementTree(xml_testsuite)
    xml_tree.write(xml_report_filepath, xml_declaration=True, encoding='utf-8')
    logging.info(f"Generated skipped tests file '{xml_report_filepath}'")


@pytest.fixture(scope="session")
def skipped_tests(request):
    """Collect the tests currently skipped on each platform.

    Args:
        request: Pytest's internal request fixture with test function information.

    Returns:
        A dictionary with the lists of tests skipped by each platform.
    """
    session = request.node
    all_skip_markers = ["skip", "skipos", "darwin", "linux", "win32"]
    skipped_tests = dict([(os_, []) for os_ in [pytest.os] + SKIPOS_PLATFORMS])

    for test in session.items:
        skip_markers = [
            marker for marker in test.own_markers if marker.name in all_skip_markers
        ]
        for marker in skip_markers:
            platforms, reason = get_skipped_platforms(marker)
            skip_data = {"name": test.name, "nodeid": test.nodeid, "reason": reason}
            for plat in platforms:
                skipped_tests[plat].append(skip_data)

    return skipped_tests


def get_skipped_platforms(marker):
    """Return the platforms filtered by a given skip marker.

    Note: The following markers are accepted: skip, skipos, darwin, linux
          and win32. The marker `skipif` is currently not considered.

    Args:
        marker: a pytest skip marker.

    Returns:
        (list[str], str): a tuple containing the list of platforms filtered
                          by the marker, as well as the skip reason.
    """
    reason = marker.kwargs.get("reason", "n/a")
    filtered_platforms = []

    if marker.name in ["darwin", "linux", "win32"]:
        os_ = marker.name.replace("darwin", "mac").replace("win32", "win")
        reason = " ".join(marker.name, "only")
        filtered_platforms = list(set(SKIPOS_PLATFORMS) - set([os_, "all"]))
    elif marker.name == "skip":
        reason = marker.args[0] if len(marker.args) else reason
        filtered_platforms = ["all"]
    elif marker.name == "skipos":
        os_ = marker.args[0]
        reason = marker.args[1] if len(marker.args) > 1 else reason
        filtered_platforms = [os_]

    return (filtered_platforms, reason)


@pytest.fixture(scope="session", autouse=True)
def add_junitxml_properties(request, record_testsuite_property):
    """Add new properties to the testsuite junitxml report

    The properties include the api level and tag id

    Args:
        request: FixtureRequest
        record_testsuite_property: Callable[[str, object], None]
    """
    if request.node.testsfailed > 0:
        return
    avd_config = json.loads(request.config.getoption('avd_config'))
    for key, property in avd_config.items():
        record_testsuite_property(key, property)

