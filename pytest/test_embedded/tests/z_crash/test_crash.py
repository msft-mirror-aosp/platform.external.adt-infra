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
import re
import time
from pathlib import Path

import pytest
import logging
from typing import List

from emu.crashreporter import CrashReporter
from emu.emulator import BaseEmulator


def get_crash_reporter(pytestconfig):
    exe = pytestconfig.getoption("emulator")
    emulator_directory = Path(exe).parent if exe else None
    return CrashReporter(emulator_directory, pytestconfig.getoption("symbols"))


@pytest.fixture
def crash_reporter(pytestconfig):
    """A fixture to handle crash reports in the emulator.

    This fixture returns the crash reporter associated with the emulator,
    which can be used to list, print, upload, and delete crash reports.
    The scope of the fixture is session and it is
    automatically used in all test functions.

    The fixture also writes the crash reports to disk if the `log_file` option is
    provided. If not, it lists all the crashes instead.

    Args:
        pytestconfig (object): Pytest configuration object

    Yields:
        CrashReporter: An instance of the CrashReporter class
    """
    crash_report = get_crash_reporter(pytestconfig)
    crash_report.clear()
    yield crash_report
    crash_report.clear()


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


def check_minidump(minidump):
    # 1. Immediate. Note that our symbols might have mangled C++
    # functions, which can be mangled differently from compiler
    # to compiler, so we just look for some readable names.
    IMMEDIATE_CRASH = [
        re.compile(reg, re.M)
        for reg in [
            r".*0.*!.*GenerateDumpAndDie.*",
            r".*1*!.*GenerateDumpAndDie.*",
            r".*2.*!.*crashhandler_die.*",
            r".*3.*!.*crash\(\).*",
            r".*4.*!.*do_crash.*",
            r".*5.*!.*control_client_do_command.*",
            r".*6.*!.*control_client_read.*",
        ]
    ]

    assert is_sublist(minidump.splitlines(), IMMEDIATE_CRASH)


def crash(emulator: BaseEmulator, crash_reporter: CrashReporter):
    # Launch the emulator if needed.
    if not emulator.is_alive():
        emulator.launch()

    assert emulator.is_alive()

    emulator.console().send("crash")

    # Give the reporter a chance to collect a report.
    while emulator.is_alive():
        time.sleep(1)

    return crash_reporter.crashes()


@pytest.mark.e2e
@pytest.mark.timeout(timeout=60, func_only=True)
def test_crash_the_emulator(emulator: BaseEmulator, crash_reporter):
    """Make sure the emulator can crash, and produces a report.

    Note, this test is placed in the z_crash directory to have it run last.
    """
    if not crash_reporter.available():
        pytest.skip("No crash reporter available, let's not crash the emulator")

    # Do not run if we have existing crashes!
    # This likely means the emulator went down in another test.
    assert len(crash_reporter.crashes()) == 0, "We have existing crash data!"

    crashes = crash(emulator, crash_reporter)

    # We should have one new crash.
    assert len(crashes) == 1


@pytest.mark.e2e
@pytest.mark.timeout(timeout=60, func_only=True)
def test_crash_can_decode_symbols(emulator: BaseEmulator, crash_reporter):
    if not crash_reporter.available():
        pytest.skip("No crash reporter available, let's not crash the emulator")

    if not crash_reporter.has_symbols():
        pytest.skip("No symbols available, let's not crash the emulator")

    crashes = crash(emulator, crash_reporter)
    dump = crash_reporter.dump_crash(crashes[0])
    check_minidump(dump)
