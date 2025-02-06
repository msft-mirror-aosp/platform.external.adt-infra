# Copyright 2022 - The Android Open Source Project
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
import asyncio
import datetime
import json
import logging
import os
import platform
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from threading import Lock, Thread, Timer
from typing import Callable, Dict, List, Optional, Tuple

# Allow running from either in or out of the virtualenv.
try:
    from emu.crashreporter import CrashReporter
except ImportError:
    from src.emu.crashreporter import CrashReporter

OS_NAME = platform.system().lower()
HERE = Path(os.path.dirname(__file__)).absolute()


class CommandFailure(Exception):
    pass


class NoTestResultsProduced(Exception):
    pass


class UnitTestFailure(Exception):
    pass


def run_tests(
    emulator: str,
    use_exceptions: bool,
    logdir: Path,
    symbol_path: Path,
    build_target: str,
    pyrun: Callable,
    tests_to_run,
    collect: bool,
    fetcher: Optional[Path],
    android_home: Path,
    grpc_services: Path,
):
    """
    Runs tests on an emulator, installs necessary packages, restarts adb,
    runs pytest, and generates JUnit XML and HTML reports.

    Args:
        emulator (str): Path to the emulator binary.
        use_exceptions (bool): Whether to raise exceptions on pytest failures.
        logdir (Path): Directory where logs will be written.
        symbol_path (Path): Optional path to symbols related to the emulator.
        build_target (str): Name of the build target.
        pyrun (Callable): Python execution callable for running commands.
        tests_to_run (str, dict): Test suite(s) configuration to run.
        collect (bool): If True, collect test lists instead of running tests.
        fetcher (Optional[Path]): Optional path to fetcher binary.
        android_home (Path): Path to ANDROID_HOME/ANDROID_SDK_ROOT.
        grpc_services (Path): Path to GRPC services proto files.

    Returns:
        None
    """
    emulator = str(resolve_emulator(emulator))
    logdir = Path(logdir)
    adb = resolve_adb_path(android_home)
    result_xmls, skip_reports = run_test_suites(
        emulator,
        use_exceptions,
        logdir,
        symbol_path,
        build_target,
        pyrun,
        tests_to_run,
        collect,
        fetcher,
        android_home,
        adb,
        grpc_services,
    )
    generate_reports(logdir, pyrun, result_xmls, skip_reports, collect)


def resolve_adb_path(android_home: Path) -> Path:
    """
    Resolves the path to the adb binary, adding the '.exe' extension if on Windows.

    Args:
        android_home (Path): Path to the Android SDK.

    Returns:
        Path: The resolved path to the adb binary.
    """
    adb = android_home / "platform-tools" / "adb"
    return adb.with_suffix(".exe") if OS_NAME == "windows" else adb


def run_test_suites(
    emulator: str,
    use_exceptions: bool,
    logdir: Path,
    symbol_path: Path,
    build_target: str,
    pyrun: Callable,
    tests_to_run,
    collect: bool,
    fetcher: Optional[Path],
    android_home: Path,
    adb: Path,
    grpc_services: Path,
) -> tuple[list, list]:
    """
    Runs test suites on the emulator, logging the results and handling multiple groups if configured.

    Args:
        emulator (str): Path to the emulator binary.
        use_exceptions (bool): Whether to raise exceptions on pytest failures.
        logdir (Path): Directory where logs will be written.
        symbol_path (Path): Optional path to symbols related to the emulator.
        build_target (str): Name of the build target.
        pyrun (Callable): Python execution callable for running commands.
        tests_to_run (str, dict): Test suite(s) configuration to run.
        collect (bool): If True, collect test lists instead of running tests.
        fetcher (Optional[Path]): Optional path to fetcher binary.
        android_home (Path): Path to ANDROID_HOME/ANDROID_SDK_ROOT.
        adb (Path): Path to adb binary.
        grpc_services (Path): Path to GRPC services proto files.

    Returns:
        tuple[list, list]: A tuple containing lists of result XMLs and skip report paths.
    """
    result_xmls = []
    skip_reports = []

    for name, cfg in tests_to_run:
        avd_configs = json.dumps(cfg.get("avd_configs", []))
        max_groups = cfg.get("maxGroups", 1)
        for group in range(1, max_groups + 1):
            pytest_flags = prepare_pytest_flags(
                cfg["pytest_flags"], max_groups, group, name
            )
            suite = f"{name}_{group}_of_{max_groups}" if max_groups > 1 else name
            test_log_dir = setup_test_log_dir(logdir, suite)

            with AdbServer(pyrun, adb), tempfile.TemporaryDirectory() as tmpdir:
                logging.info("Running %s (%s)", suite, cfg["description"])
                res = run_single_suite(
                    emulator,
                    use_exceptions,
                    test_log_dir,
                    symbol_path,
                    tmpdir,
                    build_target,
                    pyrun,
                    pytest_flags,
                    avd_configs,
                    collect,
                    suite,
                    fetcher,
                    android_home,
                    adb,
                    grpc_services,
                )
                result_xmls.append(res)
                skip_reports.append(test_log_dir.joinpath(suite + "_skip.xml"))

    return result_xmls, skip_reports


def prepare_pytest_flags(pytest_flags, max_groups: int, group: int, name: str) -> list:
    """Prepares the pytest flags for a specific test group, adding group-specific options if necessary."""
    flags = list(pytest_flags)
    if max_groups > 1:
        flags += [f"--group-number={group}", f"--max-groups={max_groups}"]
    return flags


def setup_test_log_dir(logdir: Path, suite: str) -> Path:
    """Sets up the directory for storing test logs for a given suite."""
    test_log_dir = logdir / suite
    test_log_dir.mkdir(exist_ok=True, parents=True)
    return test_log_dir


def generate_reports(
    logdir: Path, pyrun: Callable, result_xmls: list, skip_reports: list, collect: bool
):
    """
    Generates XML and HTML reports for the test results and skipped tests.

    Args:
        logdir (Path): Directory where reports will be written.
        pyrun (Callable): Python execution callable for running commands.
        result_xmls (list): List of paths to result XML files.
        skip_reports (list): List of paths to skip report files.
        collect (bool): If True, generate collection XML instead of test results.

    Returns:
        None
    """
    result = logdir / (
        "COLLECT-embedded_test.xml" if collect else "TEST-embedded_test.xml"
    )
    merge_results(pyrun, result_xmls, result)

    xml_skip_report = logdir / "skipped_tests.xml"
    merge_skip_reports(pyrun, skip_reports, xml_skip_report)

    apply_xslt(pyrun, result, HERE / "cfg" / "liftSystemOut.xslt", result)
    apply_xslt(
        pyrun, result, HERE / "cfg" / "asMaterialHtml.xslt", logdir / "test_report.html"
    )
    apply_xslt(
        pyrun,
        xml_skip_report,
        HERE / "cfg" / "skippedTests.xslt",
        xml_skip_report.with_suffix(".html"),
    )


def run_single_suite(
    emulator: str,
    use_exceptions: bool,
    logdir: Path,
    symbol_path: Path,
    tmpdir: str,
    build_target: str,
    pyrun: Callable,
    pytest_flags: list[str],
    avd_configs: list[str],
    collect: bool,
    name: str,
    fetcher: Optional[Path],
    android_home: Path,
    adb: Path,
    grpc_services: Path,
):
    if collect:
        pytest_flags.append("--setup-plan")
    if fetcher:
        pytest_flags.append(f"--fetcher={fetcher}")

    junit_test_results = Path(logdir) / f"{name}.xml"
    exit_code = 1
    try:
        exit_code = pyrun(
            [
                "-m",
                "pytest",
                "-vv",
                "-x" if use_exceptions else "",
                f"--junitxml={junit_test_results}",
                f"--log-file={logdir}/{name}.log",
                f"--emulator={emulator}",
                f"--symbols={symbol_path}",
                "--avd_configs",
                avd_configs,
                f"--android_avd_home={tmpdir}",
                f"--build_target={build_target}",
                f"--android_home={android_home}",
                f"--grpc_services={grpc_services}",
                "--record_screen",
            ]
            + pytest_flags,
            cwd=HERE,
            env={
                "ANDROID_EMU_ENABLE_CRASH_REPORTING": "YES",
                "ANDROID_AVD_HOME": str(tmpdir),
                "PYTEST_ADDOPTS": os.getenv("PYTEST_ADDOPTS") or "",
            },
            # Give pytest a chance to "nicely" terminate everything (4 hours).
            timeout=14400,
            check_output=False,
        )
    except subprocess.TimeoutExpired as timeout_exception:
        logging.info(
            "The test suite %s timed out after %s seconds",
            name,
            timeout_exception.timeout,
        )
        # Force the emulator to crash when the test suite timesout.
        run([adb, "emu", "crash"], timeout=300)

    finally:
        # Let's see if we can collect crash reports..
        asyncio.run(collect_crash_reports(emulator, symbol_path, logdir, grpc_services))

        # Forcefully terminate all emulator processess
        pyrun(
            ["-m", "emu.process.kill_emulator", "--log-level", "WARNING"],
            check_output=False,
        )

        if not junit_test_results.exists():
            raise NoTestResultsProduced(
                f"We expected a junit report in {junit_test_results}."
            )

        # Create a html report of the suite, this will end up in the
        # test_suite archive.
        apply_xslt(
            python_exe=pyrun,
            source=junit_test_results,
            xslt=HERE / "cfg" / "asMaterialHtml.xslt",
            dest=Path(logdir) / f"{name}.html",
        )

        # Let's exit with a message that contains the first failure
        # This way we can have it show up as part of the snippet we display
        # on our build bots
        # See https://docs.pytest.org/en/7.1.x/reference/exit-codes.html for
        # the status codes.
        if exit_code == 1 and use_exceptions:
            failure_file = Path(logdir) / "fail.txt"
            apply_xslt(
                python_exe=pyrun,
                source=junit_test_results,
                xslt=HERE / "cfg" / "asFirstFailureText.xslt",
                dest=failure_file,
            )
            with open(failure_file, "r", encoding="utf-8") as failure:
                raise UnitTestFailure(failure.read())

    return junit_test_results


def get_tests_to_run(test_config: str, test_suite: str,
                     system_image_path: str = '') -> List[Tuple[str, Dict]]:
    """Gets the list of tests to run."""
    with open(test_config, "r", encoding="utf-8") as file:
        test_cfg = json.load(file)

    tests_to_run = [
        (name, test_cfg[name])
        for name in test_cfg
        if (re.match(test_suite, name) and test_cfg[name]["status"] == "enabled")
    ]
    if not tests_to_run:
        raise NoTestResultsProduced(f"No enabled test suite matching {test_suite}")
    # Override the system image if one was specified.
    if system_image_path:
        for _, cfg in tests_to_run:
            for avd_cfg in cfg.get("avd_configs", ()):
                avd_cfg["image.sysdir.1"] = system_image_path
    return tests_to_run


def get_log_path(logdir: Path) -> Path:
    """Returns the path to the log file, creating any needed directories."""
    logdir.mkdir(exist_ok=True, parents=True)
    log_name = ".".join(
        (
            os.path.basename(sys.argv[0]),
            datetime.datetime.now().strftime("%Y%m%d-%H%M%S"),
            "log",
        )
    )
    return logdir.joinpath(log_name)


class AdbServer:
    def __init__(self, pyrun, adb):
        self.pyrun = pyrun
        self.adb = adb

    def __enter__(self):
        self.pyrun(
            ["-m", "emu.process.kill_emulator", "-p", "adb", "--log-level", "WARNING"],
            check_output=False,
        )
        run([self.adb, "start-server"], timeout=60)

    def __exit__(self, exc_type, exc_val, exc_tb):
        run([self.adb, "kill-server"], timeout=60)
        self.pyrun(
            ["-m", "emu.process.kill_emulator", "-p", "adb", "--log-level", "WARNING"],
            check_output=False,
        )


def merge_results(python_exe: Callable, sources: [Path], dest: Path):
    try:
        python_exe(
            [
                "-m",
                "emuxml.merge_results",
                "--single",
                "--out",
                dest,
            ]
            + [str(x) for x in sources],
            timeout=10,
        )
    except Exception as err:
        logging.warning(
            "Failed to merge results: %s to %s due to (%s)", sources, dest, err
        )


def merge_skip_reports(python_exe: Callable, sources: [Path], dest: Path):
    """Run the standalone skip report module

    Args:
        python_exe (Callable): The callable used to run python.
        sources ([Path]): List of xml skip reports that are to be merged.
        dest (Path): The (optional) output file where the result will be written to.
    """
    try:
        python_exe(
            [
                "-m",
                "emuxml.merge_skip_reports",
                "--out",
                dest,
                "--cfg",
                HERE / "cfg",
            ]
            + [str(x) for x in sources],
            timeout=10,
        )
    except Exception as err:
        logging.warning(
            "Failed to merge skip reports: %s to %s due to (%s)", sources, dest, err
        )


def apply_xslt(python_exe: Callable, source: Path, xslt: Path, dest: Path):
    """Applies a specified XSLT file to an XML file and saves the result to a specified
    destination.


    Args:
        python_exe (Callable): Callable that runs Python that will be used
                to run the transform script.
        source (Path): The path to the Python executable that will be used to run
                the transform script.
        xslt (Path): The path to the XSLT file that will be used to transform
                the XML file.
        dest (Path): The path to the destination file where the result of the
                transformation will be saved.
    """
    try:
        python_exe(
            [
                "-m",
                "emuxml.transform",
                "--xml",
                source,
                "--xsl",
                xslt,
                "--out",
                dest,
            ],
            timeout=10,
        )
    except Exception as err:
        logging.warning("Failed to apply xslt: %s to %s due to (%s)", xslt, source, err)


async def collect_crash_reports(
    emulator: str, symbol_path: Path, logdir: Path, grpc_services: Path
):
    emulator_directory = Path(emulator).parent if emulator else None
    crash_report = CrashReporter(emulator_directory, symbol_path, grpc_services)

    # Write them to disk
    await crash_report.write_reports_to_disk(logdir)

    # And report them..
    await crash_report.report_crashes()

    # After reporting them we will have ids, lets print them and remove them.
    await crash_report.report_crashes()
    await crash_report.clear()


def resolve_emulator(emulator: str) -> Path:
    """Tries to resolve the emulator path."""
    emu = Path(emulator)
    if emu.exists():
        return emu

    # Ok, maybe we are missing an extension?
    emu = emu.with_suffix(".exe")
    if emu.exists():
        return emu

    assert False, (
        f"{emulator} points to a non existent path (are you passing the right path to"
        + " the --emulator flag?"
    )


def run(cmd, cwd=None, extra_env=None, timeout=1200, check_output=True):
    """Runs a command in the shell. It takes in a command to execute,
    a working directory where the command will be executed,
    environment variables and a timeout value.

    Args:
        cmd (_type_): A list of strings representing the command and its arguments
                that will be executed in the shell.
        cwd (_type_, optional):  The working directory where the command will be
                executed. If not provided, the current working directory will be used.
        extra_env (_type_, optional): A dictionary of extra environment variables that
                will be added to the environment before running the command.
        timeout (int, optional): The maximum time (in seconds) to wait for the command
                to finish before it is terminated. Defaults to 1200.
        check_output (bool): True if an exception should be raised of the return code != 0

    Returns:
        exitcode

    Raises:
        Exception: Raises an exception if the command fails to execute.
    """
    if not cwd:
        cwd = os.getcwd()
    cwd = os.path.abspath(cwd)

    cmd = [str(c) for c in cmd]

    # We need to use a shell under windows, to set environment parameters.
    # otherwise we don't, since we will experience cmake invocation errors.
    use_shell = platform.system() == "Windows"
    local_env = os.environ.copy()
    if extra_env:
        local_env.update(extra_env)

    logging.warning(
        "Running: %s in %s for at most %s seconds with %s",
        " ".join(cmd),
        cwd,
        timeout,
        extra_env,
    )
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=cwd,
        shell=use_shell,  # Needed on windows
        env=local_env,
        encoding="utf-8",
    )
    # On windows, proc.wait() has been observed failing to ever timeout. To work around
    # this we handle timeouts in a separate thread.
    watcher = ProcWatcher(timeout, proc)

    _log_proc(proc)
    try:
        proc.wait()
    finally:
        timed_out = watcher.check_timeout()

    if timed_out:
        logging.error(
            "The command %s timed out after %s seconds, terminating",
            " ".join(cmd),
            timeout,
        )
        raise subprocess.TimeoutExpired(cmd, timeout)

    if proc.returncode != 0 and check_output:
        raise CommandFailure(
            f"Failed to run {' '.join(cmd)}, exit code: {proc.returncode}"
        )
    else:
        return proc.returncode


class ProcWatcher:
    """Process timeout watcher."""

    def __init__(self, timeout: int, proc: subprocess.Popen):
        self._lock = Lock()
        self._proc = proc
        self._timed_out = None
        self._timer = Timer(timeout, self._handle_timeout)
        self._timer.start()

    def _handle_timeout(self):
        with self._lock:
            # Avoid a race between the process exiting and timeout triggering.
            if self._timed_out is not None:
                return
            self._timed_out = True

        if OS_NAME == "windows":
            run(
                ["taskkill.exe", "/F", "/T", "/PID", str(self._proc.pid)],
                check_output=False,
            )
        else:
            self._proc.terminate()

    def check_timeout(self):
        """Cancels the internal timer and returns whether the timeout was reached."""
        self._timer.cancel()
        with self._lock:
            if self._timed_out is None:
                self._timed_out = False
            return self._timed_out


def _log_proc(proc):
    """Logs the output of the given process."""
    for args in [[proc.stdout, logging.info], [proc.stderr, logging.error]]:
        Thread(target=_reader, args=args).start()


def _reader(pipe, logfn):
    try:
        for line in iter(pipe.readline, ""):
            try:
                logfn(line[:-1].strip())
            except Exception as err:
                logfn("Unable to log line due to: %s", err)
    finally:
        pass
