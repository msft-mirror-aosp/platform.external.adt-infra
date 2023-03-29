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
import platform
import re
import sys
from typing import List

import pytest

from emu.crashreporter import CrashReporter
from emu.emulator import BaseEmulator
from emu.timing import wait_until


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
    assert any([crash_re.match(x) for x in minidump.splitlines()])


def crash(emulator: BaseEmulator, crash_reporter: CrashReporter):
    # Launch the emulator if needed.
    if not emulator.is_alive():
        emulator.launch()

    assert emulator.is_alive()

    crash_count = len(crash_reporter.crashes())
    assert emulator.console().send("crash")

    # Wait until the emulator is alive
    assert wait_until(emulator.is_alive)

    def crash_detected():
        return crash_count < len(crash_reporter.crashes())

    assert wait_until(crash_detected)

    return crash_reporter.crashes()


@pytest.mark.e2e
@pytest.mark.timeout(timeout=60, func_only=True)
@pytest.mark.skipif(platform.processor() == "i386", reason="b/275642912")
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
@pytest.mark.skipif(sys.platform == "win32", reason="b/275577019")
def test_crash_can_decode_symbols(emulator: BaseEmulator, crash_reporter):
    if not crash_reporter.available():
        pytest.skip("No crash reporter available, let's not crash the emulator")

    if not crash_reporter.has_symbols():
        pytest.skip("No symbols available, let's not crash the emulator")

    crashes = crash(emulator, crash_reporter)
    dump = crash_reporter.dump_crash(crashes[0])
    check_minidump(dump)
