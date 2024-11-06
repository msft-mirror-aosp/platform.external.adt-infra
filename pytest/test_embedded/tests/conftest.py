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
import hashlib
import json
import logging
import os
import platform
import sys
import threading
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

# This makes all the fixtures globally available
# Do not remove these!
from tests.fixtures.apk_fixtures import *
from tests.fixtures.benchmark_event_fixtures import *
from tests.fixtures.emulator_fixtures import *
from tests.fixtures.emulator_settings_fixtures import *
from tests.fixtures.grpc_fixtures import *
from tests.fixtures.mobly_fixtures import *
from tests.fixtures.qrcode_fixtures import *
from tests.fixtures.screen_recording_fixtures import *

OS_NAME = platform.system().lower()
HERE = Path(os.path.dirname(__file__)).absolute()
if len(HERE.parents) > 4:
    AOSP_ROOT = HERE.parents[4]
    SDK_EMULATOR = (
        AOSP_ROOT / "prebuilts" / "android-emulator-build" / "system-images" / OS_NAME
    )
else:
    SDK_EMULATOR = ""

# Set of exceptions for which we will attempt a rerun if the flaky marker
# has been set to 0 (or is absent). These exceptions are all related to emulator
# configuration.
RETRY_ON_EXCEPTIONS = [
    "EmulatorFailedToBootException",
    "EmulatorDiedException",
    "EmulatorNotFoundException",
    "FailedToInstallApkException",
    "EmulatorException",
]


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
        "--group-number",
        action="store",
        type=int,
        help="Run tests belonging to the specified group (1-based).",
    )
    parser.addoption(
        "--max-groups",
        action="store",
        type=int,
        help="Total number of test groups for sharding.",
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
        "--emulator-failure-retries",
        action="store_true",
        help=f"Number of times we wish to retry in case of emulator configuration failures. Currently the following exceptions will cause a retry: {', '.join(RETRY_ON_EXCEPTIONS)}",
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


def modifyitems_for_sharding(session, config, items):
    """
    Pytest hook to modify the list of test items to be executed.

    This hook implements test sharding based on module names. It allows
    distributing tests across multiple workers by assigning each worker
    a specific group number.

    Args:
        session: The pytest session object.
        config: The pytest config object.
        items: The list of test items to be executed.

    Raises:
        ValueError: If the group number is invalid (greater than max groups or zero).
    """
    group = config.getoption("--group-number")
    max_groups = config.getoption("--max-groups")

    if group is None or max_groups is None:
        return  # No sharding needed

    if group > max_groups:
        raise ValueError("The group number should be less or equal than max-groups!")
    if group == 0:
        raise ValueError("The group number should be more than 0! (did you mean 1?)")

    # Adjust for 1-based shard index
    group = int(group) - 1
    max_groups = int(max_groups)

    slow_items = []
    normal_items = []
    for item in items:
        if item.get_closest_marker("slow") is not None:
            slow_items.append(item)
        else:
            normal_items.append(item)

    # Update the items list to only include the selected tests
    items[:] = slow_items[group::max_groups] + normal_items[group::max_groups]


def modifyitems_for_retry(session, config, items):
    """
    Modify test items to enable retries for specific exceptions.

    This function iterates through the test items and adds a `flaky` marker
    to each item, configuring it to retry tests that encounter any of the
    exceptions listed in `retry_exceptions`.

    Normally the retry_exceptions are set to exceptions related to emulator
    configuration.

    If an item already has a `flaky` marker with `reruns` set to 0, it
    overrides the marker to enable retries for the specified exceptions.

    Args:
        session: The pytest session object.
        config: The pytest config object.
        items: The list of test items to modify.
    """
    retries = config.getoption("--emulator-failure-retries") or 2

    for item in items:
        rerun_marker = item.get_closest_marker("flaky")
        if not rerun_marker:
            rerun_marker = pytest.mark.flaky(
                delay=1, reruns=retries, only_rerun=RETRY_ON_EXCEPTIONS
            )
            item.add_marker(rerun_marker)
            continue

        # Override existing item with exception for which we are willing to retry.
        if "reruns" in rerun_marker.kwargs and rerun_marker.kwargs["reruns"] == 0:
            rerun_marker.kwargs["only_rerun"] = RETRY_ON_EXCEPTIONS
            rerun_marker.kwargs["reruns"] = retries


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(session, config, items):
    modifyitems_for_retry(session, config, items)
    modifyitems_for_sharding(session, config, items)


@pytest.fixture(scope="session")
def log_directory(pytestconfig):
    """Get the directory from value of the --log-file option, or the current working directory."""
    log_file = pytestconfig.getoption("--log-file")
    if log_file:
        return Path(log_file).parent

    return Path.cwd()
