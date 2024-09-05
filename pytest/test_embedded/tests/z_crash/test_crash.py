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
import logging
import re
from typing import List

from emu.crashreporter import CrashReporter
from pathlib import Path
import pytest
import os
from emu.crashreporter import CrashReporter
from emu.emulator import BaseEmulator
from emu.timing import wait_until


AOSP_ROOT = Path(os.path.dirname(__file__)).absolute().parents[5]
# Path to all the gRPC services
GRPC_SERVICES = AOSP_ROOT / "external" / "qemu" / "android" / "android-grpc"


def get_crash_reporter(pytestconfig):
    exe = pytestconfig.getoption("emulator")
    emulator_directory = Path(exe).parent if exe else None
    return CrashReporter(
        emulator_directory,
        pytestconfig.getoption("symbols"),
        GRPC_SERVICES,
    )


@pytest.fixture
async def crash_reporter(pytestconfig):
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
    logging.info("--> seting up crash reporter")
    await crash_report.clear()
    yield crash_report
    # await crash_report.clear()


def is_sublist(minidump: List[str], compiled_regexes: List[re.Pattern]) -> bool:
    """
    Returns True if the list of compiled regular expressions in `compiled_regexes` matches
    substrings in the list `minidump` in the same order they appear in
    `compiled_regexes`.

    Args:
        minidump (List[str]): The list of strings to search for matches.
        compiled_regexes (List[re.Pattern]): The list of compiled regular expression patterns
            to search for in `minidump`.

    Returns:
        bool: True if all regular expressions in `compiled_regexes` match substrings in
            `minidump` in the same order they appear in `compiled_regexes`.
    """
    i, j = 0, 0  # i: index in minidump, j: index in compiled_regexes
    while i < len(minidump) and j < len(compiled_regexes):
        if compiled_regexes[j].match(minidump[i]):
            logging.info("Found %s", minidump[i].strip())
            j += 1
        i += 1

    return j == len(compiled_regexes)


def minidump_has_symbols(minidump):
    # Note that our symbols might have mangled C++
    # functions, which can be mangled differently from compiler
    # to compiler. Furthermore some platforms are optimizing better than others
    # making functions disappear.
    IMMEDIATE_CRASH = [
        re.compile(reg, re.M)
        for reg in [
            r".*.*!.*GenerateDumpAndDie.*",
            r".*.*!.*crashhandler_die.*",
            r".*.*!.*crash\(\).*",
            r".*.*!.*do_crash.*",
            r".*.*!.*control_client_do_command.*",
            r".*.*!.*control_client_read.*",
        ]
    ]

    # We will only look for a single symbol, as the stack order can
    # vary slightly from system to system
    #  assert is_sublist(minidump.splitlines(), IMMEDIATE_CRASH)

    # If we are able to decode a single function, than we can decode them
    # all. We assume the method do_crash has been called.
    crash_re = re.compile(r".*.*!.*do_crash.*", re.M)
    return any([crash_re.match(x) for x in minidump.splitlines()])


async def crash(emulator: BaseEmulator, crash_reporter: CrashReporter):
    # Launch the emulator if needed.
    if not emulator.is_alive():
        await emulator.launch()

    assert emulator.is_alive()

    crash_count = len(await crash_reporter.crashes())
    assert await emulator.adb.run(["emu", "crash"])

    # Wait until the emulator is gone
    def emulator_dead():
        return not emulator.is_alive()

    assert await wait_until(emulator_dead)

    async def crash_detected():
        crashes = await crash_reporter.crashes()
        return crash_count < len(crashes)

    assert await wait_until(crash_detected)

    return await crash_reporter.crashes()


@pytest.mark.e2e
@pytest.mark.boot
@pytest.mark.fast
@pytest.mark.flaky  # b/278266218 flaky on linux_x64-gfxstream.
async def test_crash_the_emulator(emulator: BaseEmulator, crash_reporter):
    """Make sure the emulator can crash, and produces a report.

    Note, this test is placed in the z_crash directory to have it run last.
    """
    assert not emulator.is_alive()

    if not crash_reporter.available():
        pytest.skip("No crash reporter available, let's not crash the emulator")

    # Do not run if we have existing crashes!
    # This likely means the emulator went down in another test.
    assert len(await crash_reporter.crashes()) == 0, "We have existing crash data!"

    crashes = await crash(emulator, crash_reporter)

    # We should have at least one new crash.
    assert len(crashes) >= 1


@pytest.mark.e2e
@pytest.mark.boot
@pytest.mark.skipos("win", "Symbol decoding works differently on windows (b/305990645)")
async def test_crash_can_decode_symbols(emulator: BaseEmulator, crash_reporter):
    """Make sure that there are symbols in the crashes reported by the emulator.

    This makes sure that we produced symbols, so that if we have crash reports
    we can decode them on our crash server.
    """
    assert not emulator.is_alive()

    if not crash_reporter.available():
        pytest.skip("No crash reporter available, let's not crash the emulator")

    if not await crash_reporter.has_symbols():
        pytest.skip("No symbols available, let's not crash the emulator")

    crashes = await crash(emulator, crash_reporter)
    assert any(
        [minidump_has_symbols(await crash_reporter.dump_crash(c)) for c in crashes]
    ), "None of the crash reports have decoded symbols"
