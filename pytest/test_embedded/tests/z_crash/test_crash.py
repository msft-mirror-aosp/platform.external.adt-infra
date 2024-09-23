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
import asyncio
from hacks import load_tkinter
import pyautogui
import platform

from emu.process.command import Command
from emu.crashreporter import CrashReporter
from emu.emulator import BaseEmulator
from emu.timing import eventually
from emu.timing import wait_until
from functools import partial
from emu.emulator_exceptions import EmulatorNotFoundException
from emu.logging.log_handler import AsyncLogHandler


def get_crash_reporter(pytestconfig):
    exe = pytestconfig.getoption("emulator")
    emulator_directory = Path(exe).parent if exe else None
    return CrashReporter(
        emulator_directory,
        pytestconfig.getoption("symbols"),
        pytestconfig.getoption("grpc_services"),
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


async def nav_back(n):
    """Send the Shift+Tab (navigate back) hotkey 'n' times
    """
    while n > 0:
        pyautogui.hotkey('Shift', 'Tab')
        await asyncio.sleep(1)
        n -= 1

async def string_in_emulator_log(log: AsyncLogHandler, string, matched_line=[]):
    """Return 'True' if 'string' is observed in the emulator log
    """
    async for line in log:
        if string in line:
            matched_line.append(line)
            return True

async def restart_and_verify_crash_dialogue(avd):
    """ Restart the emulator and verify the crash report dialogue opened
    """
    try:
        await avd.restart(avd.launch_flags + ["-no-metrics"])
    except EmulatorNotFoundException as err:
        logging.info("EmulatorNotFoundException exception was ignored")

    # Crashpad annotations indicate the crash report dialogue appeared
    matched_line = []
    assert await eventually(
        partial(string_in_emulator_log, avd.log, "crashpad_annotations", matched_line),
        timeout=300
    ), "Couldn't verify the crash report dialogue opening."

    logging.info(f'The following crashpad annotation was matched: {matched_line[0]}')


@pytest.mark.skipos("all", "issue with crash retry_plugin. b/368319883")
@pytest.mark.async_timeout(600)
@pytest.mark.crash_flake(retries=0)
@pytest.mark.fast
@pytest.mark.skipos("win", "reason: Shift+Tab hotkey unreliable.")
async def test_crash_dont_send_report(avd, crash_reporter):
    """Verify user can reject/cancel sending emulator crash report.

    Args:
        avd (BaseEmulator): booted emulator fixture.
        crash_reporter: fixture to handle crash reports.

    Test Steps:
        1. Launch a new AVD.
        2. Cause a crash, by sending the console command 'adb emu crash'.
        3. Relaunch the AVD (Verify 1).
        4. Click "Show details"
        5. Click "Hide details", type some user comments.
        6. Press "Don’t Send" (Verify 2).

    Verification:
        1. Crash Report Dialogue Window should show up before relaunching the AVD,
           observed by the presence of crashpad annotations in the emulator log.
        2. The dialog disappears immediately, with the event being observed
           in the emulator log.
    """
    crashes = await crash(avd, crash_reporter)
    assert len(crashes) >= 1, "Couldn't crash the emulator."

    await restart_and_verify_crash_dialogue(avd)

    # Click “Show details”
    await nav_back(3)
    pyautogui.press('enter')
    await asyncio.sleep(2)

    # Click “Hide details”
    pyautogui.press('enter')

    # Type some user comments
    await nav_back(2)
    pyautogui.write('Emulator E2E testing: test_crash.py::test_crash_dont_send_report')
    await asyncio.sleep(2)

    async def dismiss_and_verify():
        # Press button “Don’t Send”
        async def _dismiss():
            await nav_back(1)
            if platform.system() == "Darwin":
                # Dialogue buttons are in reversed postion on macOS
                await nav_back(1)
            pyautogui.press('enter')
        # Check stdout for the 'No consent' message
        async def _verify():
            return await eventually(
                partial(string_in_emulator_log, avd.log, "No consent for crashreport"),
                timeout=120
            )
        res = await asyncio.gather(_dismiss(), _verify())
        return res[1]

    assert await dismiss_and_verify(), "Coudn't confirm the crash report rejection."

    logging.info("Dialogue window successfully dismissed")


@pytest.mark.skipos("all", "issue with crash retry_plugin. b/369204765")
@pytest.mark.async_timeout(600)
@pytest.mark.crash_flake(retries=0)
@pytest.mark.fast
@pytest.mark.skipos("win", "reason: Shift+Tab hotkey unreliable.")
async def test_crash_send_report(avd, crash_reporter):
    """Verify user can proceed with sending emulator crash report.

    Args:
        avd (BaseEmulator): booted emulator fixture.
        crash_reporter: fixture to handle crash reports.

    Test Steps:
        1. Launch a new AVD.
        2. Cause a crash, by sending the console command 'adb emu crash'.
        3. Relaunch the AVD (Verify 1).
        4. Click "Show details"
        5. Click "Hide details", type some user comments.
        6. Press "Send report" (Verify 2).

    Verification:
        1. Crash Report Dialogue Window should show up before relaunching the AVD,
           observed by the presence of crashpad annotations in the emulator log.
        2. The emulator loads details, uploads data, shows report id.
    """
    crashes = await crash(avd, crash_reporter)
    assert len(crashes) >= 1, "Couldn't crash the emulator."

    await restart_and_verify_crash_dialogue(avd)

    # Click “Show details”
    await nav_back(3)
    pyautogui.press('enter')
    await asyncio.sleep(2)

    # Click “Hide details”
    pyautogui.press('enter')

    # Type some user comments
    await nav_back(2)
    pyautogui.write('Emulator E2E testing: test_crash.py::test_crash_dont_send_report')
    await asyncio.sleep(2)

    async def confirm_and_verify():
        # Press button "Send report"
        async def _confirm():
            await nav_back(1)
            if platform.system() != "Darwin":
                # Dialogue buttons are in reversed order on macOS
                await nav_back(1)
            pyautogui.press('enter')

        # Verify the crash report submission.
        async def _verify():
            # Check attempt to send the crash report.
            assert await eventually(
                partial(string_in_emulator_log, avd.log, "Attempting to send crashreport"),
                timeout=120
            ), "There was no attempt to send the crash report."
            # Check crashr eport upload message.
            matched_line = []
            assert await eventually(
                partial(string_in_emulator_log, avd.log,
                        "is available remotely as", matched_line),
                timeout=120
            ), "The crash report upload couldn't be verified."
            report_id_message = re.sub(".*(Report.*)", "\\1", matched_line[0])
            logging.info(report_id_message)

        return await asyncio.gather(_confirm(), _verify())

    await confirm_and_verify()


@pytest.mark.fast
@pytest.mark.crash_flake(retries=0)
@pytest.mark.async_timeout(600)
@pytest.mark.skipos("win", "reason: Shift+Tab hotkey unreliable.")
@pytest.mark.skipos("mac", "reason: unshare not available.")
async def test_crash_without_internet(avd, crash_reporter):
    """Verify no exceptions are raised when sending a crash report without internet connectivity.

    Args:
        avd (BaseEmulator): booted emulator fixture.
        crash_reporter: fixture to handle crash reports.

    Test Steps:
        1. Launch a new AVD.
        2. Cause a crash, by sending the console command 'adb emu crash'.
        3. Disconnect internet access from host machine.
        3. Relaunch the AVD (Verify 1 and 2).

    Verification:
        1. No exceptions should be raised.
        2. The emulator loads details, dialog then disappears, indicated
           by a failure message in the emulator log.
    """
    crashes = await crash(avd, crash_reporter)
    assert len(crashes) >= 1, "Couldn't crash the emulator."

    # Unshare is used to launch an emulator process within an isolated network stack
    unshare_exec = shutil.which("unshare")
    if not unshare_exec:
        pytest.fail("unshare binary not found in PATH.")

    logging.info('Launching an emulator process in its own network namespace ...')
    args = [arg for arg in avd.cmd.cmd if arg != "-metrics-collection"]
    args = [unshare_exec, "--user", "-n"] + args + ["-no-snapshot-save"]
    cmd = await Command(args).run()
    await asyncio.sleep(5)

    async def send_and_verify():
        # Press button "Send report"
        async def _send_report():
            logging.info("Attempting to click the 'Send report' button.")
            await nav_back(1)
            if platform.system() != "Darwin":
                # Dialogue buttons are in reversed order on macOS
                await nav_back(1)
            pyautogui.press('enter')

        # Verify the crash report upload fails.
        async def _verify():
            # Verify attempt to send the crash report.
            res_attempt = await eventually(
                partial(string_in_emulator_log, cmd.handler,
                        "Attempting to send crashreport."),
                timeout=120
            )
            # Check crash report failure.
            res_verify = await eventually(
                partial(string_in_emulator_log, cmd.handler,
                        "Failed to send report."),
                timeout=120
            )
            return res_attempt, res_verify

        await _send_report()
        return await _verify()

    try:
        res_attempt, res_verify = await send_and_verify()
    except Exception as e:
        pytest.fail(f"An exception occurred: {e}")

    logging.info("Attempting to kill the emulator process.")
    await cmd.cancel()
    assert res_attempt, "There was no attempt to send the crash report."
    assert res_verify, "The crash report failure couldn't be verified."
