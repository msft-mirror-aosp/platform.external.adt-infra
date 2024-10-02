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
import asyncio
import json
import logging
import os
import platform
import re
import sys
import threading
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from emu.process.command import Command
from aemu.proto.emulator_controller_pb2 import ImageFormat
from aemu.proto.emulator_controller_pb2_grpc import EmulatorControllerStub

from emu.apk import APP_DEBUG_APK, APP_MOBLY_APK
from emu.emulator import BaseEmulator, DebugEmulator, Emulator
from emu.images.convert import save_image
from emu.utils import system_cpu
from snippet_uiautomator import uiautomator
from mobly import asserts

OS_NAME = platform.system().lower()
HERE = Path(os.path.dirname(__file__)).absolute()
if len(HERE.parents) > 4:
    AOSP_ROOT = HERE.parents[4]
    SDK_EMULATOR = (
        AOSP_ROOT / "prebuilts" / "android-emulator-build" / "system-images" / OS_NAME
    )
else:
    SDK_EMULATOR = ""


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
        "--avd_configs",
        default="{}",
        help="A list of JSON snippets that contains the avd configuration that should be used to run this test",
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
    parser.addoption(
        "--fetcher",
        action="store",
        help="Optional path to the fetcher binary. If set this will be used for fetching system images.",
    )
    parser.addoption(
        "--grpc_services",
        action="store",
        help="The path to all the grpc services.",
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


def pytest_logger_config(logger_config):
    loggers = ["root", "adb", "emulator"]
    for i in range(0, 10):
        loggers += [f"emu-{i}", f"emu-{i}-adb", f"emu-{i}-con", f"emu-{i}-logcat"]

    logger_config.add_loggers(loggers, stdout_level="info")
    logger_config.split_by_outcome()


def pytest_logger_logsdir(config):
    log_file = config.getoption("--log-file")
    if log_file:
        return Path(log_file).parent

    return Path.cwd() / "results"


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

    item.user_properties.append(("flaky", "flaky" in item.keywords))

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

    # Register the 'flaky' marker
    config.addinivalue_line(
        "markers",
        "flaky: "
        "Set a test as flaky, and exclude it from test failures on the dashboard.",
    )


def pytest_sessionfinish(
    session,
    exitstatus,
):
    """Stops and remove all running emulators at the end of all tests."""
    for name, emu in pytest.emulators.items():
        logging.info("Shutting down and removing %s", name)
        asyncio.run(emu.stop())
        if not session.config.getoption("avd_keep"):
            emu.delete()


@pytest.fixture(scope="module")
@pytest.mark.async_timeout(200)
async def emulator(request, pytestconfig) -> BaseEmulator:
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
    avd_configs = json.loads(pytestconfig.getoption("avd_configs"))
    return await manage_emulator(
        request, pytestconfig, avd_configs[0] if avd_configs else {}, "emu-0"
    )


@pytest.fixture(scope="module")
async def emulators(request, pytestconfig) -> list[BaseEmulator]:
    """Makes multiple configured emulators available

    This fixture supports using multiple emulators and launches all configs
    inside avd_configs.

    'AvdId' field in each avd_config is required to distinguish between identical avds.

    Refer to emulator's docstring for implementation details on each emulator.
    """
    emulators = []
    avd_configs = json.loads(pytestconfig.getoption("avd_configs"))
    log_id = 0
    # Put a placeholder avd_config if none defined
    if not avd_configs:
        avd_configs.append({})
    for avd_config in avd_configs:
        emulators.append(await manage_emulator(request, pytestconfig, avd_config, f"emu-{log_id}"))
        log_id += 1
    return emulators


async def manage_emulator(request, pytestconfig, avd_param_config, log_id) -> BaseEmulator:
    """Configure and launch an emulator

    Args:
        request: Provide information on the executing test function.
        pytestconfig: pytest configuration information of the current test
        avd_pram_config: avd_config of the emulator specified by cfg files

    Returns:
        BaseEmulator: A successfully booted emulator with the debug apk installed.
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

    avd_config.update(avd_param_config)
    name = f"{avd_config['api']}_{avd_config['tag.id']}_{avd_config['cpu']}_{avd_config['device.name']}"
    if "AvdId" in avd_config:
        name += f"_{avd_config['AvdId']}"
    logging.info("--> Setting up emulator using avd config:%s", avd_config)

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
            fetcher = pytestconfig.getoption("fetcher")
            emu = Emulator(
                android_home=Path(pytestconfig.getoption("android_home")),
                android_avd_home=Path(pytestconfig.getoption("android_avd_home")),
                exe=exe,
                avd_config=avd_config,
                fetcher=Path(fetcher) if fetcher else None,
                log_id=log_id
            )

        emu.symbols = pytestconfig.getoption("symbols")
        emu.launch_flags = avd_config.get("launch_flags", [])
        pytest.emulators[name] = emu

    emu = pytest.emulators[name]

    if emu.is_alive():
        await emu.stop()

    return emu


@pytest.fixture(scope="module")
@pytest.mark.async_timeout(200)
async def avd_launcher(emulator: BaseEmulator) -> BaseEmulator:
    """Makes a booted emulator accessible and with the animation apk installed.

    Note that the following holds:

    - This fixture has module scope, meaning an emulator will be launched only once
      per package

    - The emulator will be (re-)started if needed.

    Args:
        emulator (BaseEmulator): Test fixture that provides the configured emulator.

    Returns:
        BaseEmulator: A successfully booted emulator with the debug apk installed.
    """
    return await anext(manage_avd(emulator))


@pytest.fixture(scope="function")
@pytest.mark.async_timeout(200)
async def avd(avd_launcher: BaseEmulator) -> BaseEmulator:
    """Makes a booted emulator accessible and with the animation apk installed.

    This fixture has function scope, which will make sure the emulator will be
    restarted if it has crashed. A new emulator will be brought up once for each
    module.

    The emulator will be (re-)started if needed.

    Args:
        avd_launcher (BaseEmulator): Test fixture that provides the configured emulator.

    Returns:
        BaseEmulator: A successfully booted emulator with the debug apk installed.
    """
    if not avd_launcher.is_alive():
        logging.info("--> Restarting emulator")
        await avd_launcher.restart(avd_launcher.launch_flags)
        assert await avd_launcher.wait_for_boot()
    else:
        logging.info("--> Reusing emulator")
    return avd_launcher


@pytest.fixture(scope="module")
@pytest.mark.async_timeout(200)
async def avds(emulators: list[BaseEmulator]) -> list[BaseEmulator]:
    """Makes booted emulators accessible and with the animation apk installed.

    Note that the following holds:

    - This fixture has module scope, meaning an emulator will be launched only once
      per package

    - The emulator(s) will be (re-)started if needed.

    Args:
        emulators (list[BaseEmulator]): Test fixture that provides the configured emulator.

    Returns:
        List of BaseEmulator: Successfully booted emulators with the debug apk installed.
    """
    return await asyncio.gather(
        *[anext(manage_avd(emulator)) for emulator in emulators]
    )


async def manage_avd(emulator) -> BaseEmulator:
    """Helper to manage a booted emulator and make it available for avd and avds fixtures.

    Args:
        emulator (BaseEmulator): Test fixture that provides the configured emulator.

    Returns:
        BaseEmulator: A successfully booted emulator with the debug apk installed.
    """
    await emulator.restart(emulator.launch_flags)
    adb_log_cmd = Command(
        [emulator.adb.adb_binary, "-s", emulator.adb.name, "logcat"],
        logging.getLogger(emulator.log_id + "-logcat"),
    )
    await adb_log_cmd.run()

    assert await emulator.wait_for_boot()
    logging.info("The emulator has finished booting")

    # Note install appears to fail at times, b/324920328
    installed = await emulator.install_apk(
        APP_DEBUG_APK.absolute(), "com.google.AnimateBox"
    )
    if not installed:
        logging.warning(
            "The animation app failed to install, this can cause unexpected failures"
        )
    installed = await emulator.install_apk(
        APP_MOBLY_APK.absolute(), "com.google.android.mobly.snippet.bundled"
    )
    if not installed:
        logging.warning(
            "The mobly snippets failed to install, this can cause unexpected failures"
        )

    await emulator.reset_state()

    logging.info("--> yielding emulator")
    yield emulator

    logging.info("<-- teardown emulator")
    # Stop the emulator.
    adb_log_cmd.cancel()
    await emulator.stop()
    logging.info("=== completed emulator")


@pytest.fixture
async def emulator_log(avd: BaseEmulator):
    """Returns the emulator log as a Queue (https://docs.python.org/3/library/queue.html)
    This contains the output seen on the console when the emulator is launched.

    The queue (log) will be emptied first.

    Usage:

    def test_logs_line(emulator_log):
        async for line in emulator_log:
           assert line == 'INFO    | Started GRPC server at 127.0.0.1:8554, security: Local, auth: none'
    """
    logging.info("--> emulator_log")
    assert avd.is_alive()

    if avd.log:
        avd.log.readlines()
    return avd.log


async def launch_animation_app(avd: BaseEmulator):
    """Launches the debug animation app.

    This launches the animation app that ships with this library and
    waits until it has launched. It will:

    - Clear out logcat (Do not rely on this!, it is best effort)
    - Wake-up the emulator (by sending the wakup code)
    - Force stop any existing running animation app
    - Start the activity
    - Wait for the welcome message to appear on logcat.
    """
    logging.info("--> launch_animation_app")
    assert avd.is_alive()
    assert await avd.stop_activity("com.google.AnimateBox")

    await avd.adb.clear_logcat()
    assert await avd.start_activity(
        "com.google.AnimateBox/com.google.emu.MainActivity", params=None
    )

    async def wait_for_started():
        async with await avd.adb.logcat(tag="aemu") as stream:
            logging.info("Waiting for --STARTED-- in logcat stream.")
            async for line in stream:
                if "--STARTED--" in line:
                    return True

    try:
        return await asyncio.wait_for(wait_for_started(), timeout=5)
    except asyncio.TimeoutError:
        logging.warning("No --STARTED-- tag seen.")
        return False


@pytest.fixture
def emulator_controller(avd: BaseEmulator):
    """A grpc stub to the emulator controller.

    Usage:

    def test_sample(emulator_controller):
        response = await emulator_controller.getStatus(empty_pb2.Empty())
        assert response.booted
    """
    assert avd.is_alive()

    ctrl = EmulatorControllerStub(avd.channel)
    return ctrl


@pytest.fixture
def service(avd: BaseEmulator):
    """An async grpc stub to the emulator of the given type

    Usage:

    def test_sample(service):
        stub = service(SensorServiceStub)
        stub.method_call
    """

    def service(klazz):
        channel = avd.description.get_async_grpc_channel(
            [("emulator.security", "token")]
        )
        return klazz(channel)

    return service


@pytest.fixture
@pytest.mark.async_timeout(90)
async def animation_app(avd: BaseEmulator):
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
    logging.info("--> animation_app")
    assert avd.is_alive()

    await avd.reset_state()
    tries = 3
    while not await launch_animation_app(avd) and tries > 0:
        await asyncio.sleep(1)
        tries = tries - 1

    assert tries >= 0, "Unable to successfully launch the animation app."
    logging.info("--> yielding animation_app")
    yield

    logging.info("<-- teardown animation_app")
    await avd.stop_activity("com.google.AnimateBox")
    await avd.reset_state()
    logging.info("=== finalized animation_app")


@pytest.fixture
@pytest.mark.async_timeout(200)
async def coldboot_animation_app(avd: BaseEmulator):
    """Similar to animation_app, but do it with cold boot"""
    logging.info("--> coldboot_animation_app")
    await avd.stop()
    assert await avd.launch(flags=["-no-snapshot-load"])
    assert await avd.wait_for_boot()

    assert avd.is_alive()

    # sleep a few seconds so that system ui have updated
    # time, lte signal and so on; we are doing a cold boot
    # and this extra seconds seems reasonable
    await asyncio.sleep(10)

    tries = 3
    while not await launch_animation_app(avd) and tries > 0:
        await asyncio.sleep(1)
        tries = tries - 1

    assert tries >= 0, "Unable to successfully launch the animation app."
    logging.info("--> yielding coldboot_animation_app")
    yield
    logging.info("<-- teardown coldboot_animation_app")
    await avd.stop_activity("com.google.AnimateBox")
    logging.info("== finalized coldboot_animation_app")


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
async def telnet(avd: BaseEmulator):
    """Access to the telnet console of the current emulator.

    Usage:

    def test_sample(telnet):
        telnet.send("event text")
    """
    assert avd.is_alive()
    return await avd.console()


@pytest.fixture
async def at_home(avd: BaseEmulator):
    logging.info("--> setup at_home")
    await avd.reset_state()
    logging.info("--> yield at_home")
    yield
    logging.info("<-- teardown at_home")

    await avd.reset_state()
    logging.info("=== finalized at_home")


@pytest.fixture
def mobly(avd: BaseEmulator):
    def mobly_package(package: str):
        return avd.mobly(package)

    return mobly_package


@pytest.fixture
def mbs(mobly):
    return mobly("mbs")


@pytest.fixture(scope="function")
async def ad_ui(avd: BaseEmulator):
    """
    Register the Snippet UiAutomator service and get the AndroidDevice ui.
    This is used to operate UI actions on an Android device.

    Usage:

    def test_sample(ad_ui):
        ad_ui(text='OK').click()
    """
    ad = avd.mobly_device.get_device()
    ad.services.register(
        uiautomator.ANDROID_SERVICE_NAME, uiautomator.UiAutomatorService
    )
    yield ad.ui

    ad.services.unregister(uiautomator.ANDROID_SERVICE_NAME)
    asserts.assert_false(
        hasattr(ad, uiautomator.PUBLIC_SERVICE_NAME),
        "Failed to remove Python wrapper",
    )
    asserts.assert_false(
        hasattr(ad, uiautomator.HIDDEN_SERVICE_NAME),
        "Failed to remove snippet client",
    )


@pytest.fixture
def log_adb_interactions():
    """
    A fixture to configure logging for the ADB interactions.

    This fixture sets the logging level for the "ppadb" module to DEBUG before the test begins.
    You can use this to analyze if there are strange things happening with ADB interactions.

    """
    logging.getLogger("adb").setLevel(logging.DEBUG)
    yield
    logging.getLogger("adb").setLevel(logging.CRITICAL)


@pytest.fixture(scope="session")
def log_directory(pytestconfig):
    """Get the directory from value of the --log-file option, or the current working directory."""
    log_file = pytestconfig.getoption("--log-file")
    if log_file:
        return Path(log_file).parent

    return Path.cwd()


@pytest.fixture
async def get_screenshot(emulator_controller, log_directory, request):
    async def do_get_screenshot(
        image_format: ImageFormat = None, screenshot_dir: str = ""
    ):
        """Get a screenshot from the emulator and save it to a file.

        Args:
            image_format: The format of the screenshot image. Defaults to 'ImageFormat()'
            screenshot_dir: Screenshot directory. Defaults to '<log_directory> / screenshots'

        Returns:
            A tuple of the raw screenshot image and the Pillow image object.
        """
        image_format = image_format or ImageFormat()
        screenshot_dir = Path(screenshot_dir) or Path(log_directory) / "screenshots"
        img = await emulator_controller.getScreenshot(image_format)
        test_name = request.node.nodeid.split("::")[-1]
        file_name = re.sub(r"[\\/\{\}:]", "_", test_name)
        pillow_image = save_image(img, screenshot_dir.absolute(), file_name)
        return img, pillow_image

    return do_get_screenshot


@pytest.fixture
async def stream_screenshot(emulator_controller, log_directory, request):
    async def streaming_img_call(image_format: ImageFormat):
        test_name = request.node.nodeid.split("::")[-1]
        screenshot_dir = Path(log_directory) / "screenshots"
        screenshot_dir.mkdir(parents=True, exist_ok=True)

        stream = emulator_controller.streamScreenshot(image_format)
        async for img in stream:
            save_image(img, screenshot_dir, test_name)
            yield img

    return streaming_img_call


@pytest.fixture
async def qrcode_png(avd):
    """A fixture that access a PNG image with a pre-encoded QR code
    Args:
        avd (BaseEmulator): Fixture that gives access to the configured emulator.
    Returns:
        An instance of the Qrcode class. The class attributes are:
        src (str): The path of the source PNG image.
        path (str): Destination path of the PNG image on the emulator.
        payload (str): The pre-encoded payload of the QR code image.
        The 'show' method can be used to display the image on the display
        identified by the 'display_id' argument (by default, the primary display).
    """

    class Qrcode:
        """A class to push a PNG QRcode with a given payload to /sdcard/Downloads"""

        def __init__(self, src: str, payload: str):
            self.src = src
            self.payload = payload
            self.path = Path("/sdcard/Downloads") / self.src.name

        async def _push(self):
            logging.info(f"Pushing '{self.src}' to '{self.path}'")
            await avd.adb.push(self.src, self.path)

        async def show(self, display_id=0):
            """Show the PNG image on display with id <display_id>"""
            await avd.stop_activity("com.google.android.apps.photos")
            await avd.start_activity(
                "com.google.android.apps.photos/.pager.HostPhotoPagerActivity",
                params=f'-a android.intent.action.VIEW -W -d file://{self.path} -t "image/PNG"'
                + (f" --display {display_id}" if display_id != 0 else ""),
            )
            logging.info(f"Launched the QR code PNG image on display '{display_id}'")

    src = (
        Path(__file__).parents[1]
        / "cfg"
        / "qrcode_uzNYdXGMb0kW7qXDejO0niE6liaPm1m0.png"
    )
    payload = "uzNYdXGMb0kW7qXDejO0niE6liaPm1m0"

    qrcode = Qrcode(src, payload)
    await qrcode._push()
    return qrcode


@pytest.fixture
async def qrcodes_mp4(avd):
    """A fixture that gives access to a MP4 video containing a series of QR codes.

    The fixture pushes a 15-second MP4 video to /sdcard/Downloads, displaying a
    series of three images with QR codes, each one shown for 5 seconds.

    Args:
        avd (BaseEmulator): Fixture that gives access to the configured emulator.

    Returns:
        An instance of the Qrcodes class. The class attributes are:

        src (str): The path of the source video file.
        path (str): The path of the video on the emulator.
        payloads (list): The pre-encoded payloads of the QR codes displayed
                         in the video.

        The 'play' method can be used to play the mp4 video on the display
        identified by the 'display_id' argument (by default, the primary display).

    Notes:
        The deqr package along with pillow can be used to decode a screenshot
        containing a QR code.
    """

    class Qrcodes:
        """A class to handle a MP4 video with pre-encoded QRcodes"""

        def __init__(self, src: str, payloads: list):
            self.src = src
            self.payloads = payloads
            self.path = Path("/sdcard/Downloads") / self.src.name

        async def _push(self):
            logging.info(f"Pushing '{self.src}' to '{self.path}'")
            await avd.adb.push(self.src, self.path)

        async def play(self, display_id=0):
            await avd.stop_activity("com.google.android.apps.photos")
            await avd.start_activity(
                "com.google.android.apps.photos/.pager.HostPhotoPagerActivity",
                params=f'-a android.intent.action.VIEW -d file://{self.path} -t "video/*"'
                + (f" --display {display_id}" if display_id != 0 else ""),
            )
            logging.info(f"Started QR codes video on display '{display_id}'")

    src_video = Path(__file__).parents[1] / "cfg" / "qrcodes.mp4"
    payloads = [
        "uzNYdXGMb0kW7qXDejO0niE6liaPm1m0",
        "W6fEti4U7ImHU1mxBXkLpOehomty7mTM",
        "tAdFTEYPzbOw6qXBR1jyvzFohsx1gfdz",
    ]

    qrcodes = Qrcodes(src_video, payloads)
    await qrcodes._push()
    return qrcodes


@pytest.fixture(scope="session", autouse=True)
def generate_skip_report(skipped_tests, log_directory):
    """Generate a xml report containing the tests currently skipped on each platform.

    Args:
        skipped_tests: Fixture that provides the skipped tests by platform.
        log_directory: Pytest's internal request fixture with test function information.
    """
    xml_report_filepath = log_directory.joinpath(log_directory.name + "_skip.xml")
    if xml_report_filepath.exists():
        # Avoid the fixture running on every re-run (pytest b/#51)
        # https://github.com/pytest-dev/pytest-rerunfailures/issues/51
        return
    xml_testsuite = ET.Element("testsuite")
    xml_testsuite.set("name", log_directory.name)
    xml_platforms = ET.SubElement(xml_testsuite, "platforms")
    fullname_map = {
        "win": "Windows",
        "linux": "Linux",
        "mac": "Mac Intel",
        "m1": "Mac M1",
        "all": "All platforms",
    }
    for os_, tests in skipped_tests.items():
        xml_platform = ET.SubElement(xml_platforms, "platform")
        xml_platform.set("name", os_)
        xml_platform.set("fullname", fullname_map.get(os_, "Unknown"))
        for test in tests:
            xml_test = ET.SubElement(xml_platform, "test")
            for property in ["name", "reason", "nodeid"]:
                xml_test_child = ET.SubElement(xml_test, property)
                xml_test_child.text = str(test[property])

    xml_tree = ET.ElementTree(xml_testsuite)
    xml_tree.write(xml_report_filepath, xml_declaration=True, encoding="utf-8")
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
        reason = " ".join(marker.name)
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
    avd_configs = json.loads(request.config.getoption("avd_configs"))
    for avd_config in avd_configs:
        for key, property in avd_config.items():
            record_testsuite_property(key, property)
