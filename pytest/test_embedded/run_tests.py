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
import argparse
import asyncio
import datetime
import json
import logging
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from queue import Queue
from threading import Lock, Thread, Timer
from typing import Dict, List, Optional
from zipfile import ZipFile, ZipInfo

# Note we are not part of the package!
from src.emu.crashreporter import CrashReporter
from src.emu.logging.log_handler import configure_logging

OS_NAME = platform.system().lower()
EMU_TEST_DIR = Path(os.path.dirname(__file__)).absolute()
AOSP_ROOT = EMU_TEST_DIR.parents[3]
SDK_EMULATOR = (
    AOSP_ROOT / "prebuilts" / "android-emulator-build" / "system-images" / OS_NAME
)
JDK_ROOT = AOSP_ROOT / "prebuilts" / "studio" / "jdk" / "jdk17"
ANDROID_SDK_ROOT = SDK_EMULATOR

AEMU_GRPC = (
    AOSP_ROOT
    / "external"
    / "qemu"
    / "android"
    / "android-grpc"
    / "python"
    / "aemu-grpc"
)
SNAPTOOL = (
    AOSP_ROOT / "external" / "qemu" / "android" / "android-grpc" / "python" / "snaptool"
)
NETSIM_GRPC = AOSP_ROOT / "tools" / "netsim" / "testing" / "netsim-grpc"
HERE = AOSP_ROOT / "external" / "adt-infra" / "pytest" / "test_embedded"
ADB = ANDROID_SDK_ROOT / "platform-tools" / "adb"

PYTHON_DIR = AOSP_ROOT / "prebuilts" / "python" / f"{OS_NAME}-x86"
if OS_NAME != "windows":
    PYTHON = PYTHON_DIR / "bin" / "python3"
else:
    PYTHON = PYTHON_DIR / "python.exe"
    ADB = ADB.with_suffix(".exe")

# Path to all the gRPC services
GRPC_SERVICES = AOSP_ROOT / "external" / "qemu" / "android" / "android-grpc"


class NoXServer(Exception):
    pass


class BuildDirectoryNotFound(Exception):
    pass


class JavaNotFound(Exception):
    pass


class AdbNotFound(Exception):
    pass


class NoTestResultsProduced(Exception):
    pass


class CommandFailure(Exception):
    pass


class UnitTestFailure(Exception):
    pass


class ZipFileWithAttr(ZipFile):
    """Python does not set the file attributes properly."""

    def _extract_member(self, member, targetpath, pwd):
        if not isinstance(member, ZipInfo):
            member = self.getinfo(member)

        targetpath = super()._extract_member(member, targetpath, pwd)

        attr = member.external_attr >> 16
        if attr != 0:
            os.chmod(targetpath, attr)
        return targetpath


class AdbServer:
    def __init__(self, pyrun):
        self.pyrun = pyrun

    def __enter__(self):
        self.pyrun.run(
            ["-m", "emu.process.kill_emulator", "-p", "adb"], check_output=False
        )
        run([ADB, "start-server"], timeout=60)

    def __exit__(self, exc_type, exc_val, exc_tb):
        run([ADB, "kill-server"], timeout=60)
        self.pyrun.run(
            ["-m", "emu.process.kill_emulator", "-p", "adb"], check_output=False
        )


def _reader(pipe, logfn):
    try:
        for line in iter(pipe.readline, ""):
            try:
                logfn(line[:-1].strip())
            except Exception as err:
                logfn("Unable to log line due to: %s", err)
    finally:
        pass


def _log_proc(proc):
    """Logs the output of the given process."""
    q = Queue()
    for args in [[proc.stdout, logging.info], [proc.stderr, logging.error]]:
        Thread(target=_reader, args=args).start()


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

    logging.info(
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


class TemporaryEmulatorDeploy:
    """Deploys the emulator from the build directory, cleaning it up after usage."""

    def __init__(self, build_dir):
        self.build_dir = Path(build_dir)
        self.tmp = tempfile.TemporaryDirectory()

        if not self.build_dir.exists():
            raise BuildDirectoryNotFound(
                f"{self.build_dir} does not exist, are you launching the scripts from {AOSP_ROOT}?"
            )

    def _find_dist_zip(self, type: str) -> Path:
        dist_regex = (
            r"sdk-repo-(linux|linux_aarch64|darwin|darwin_aarch64|windows)-"
            f"{type}"
            r"-((standalone-|P?)\d+).zip"
        )
        logging.info("Looking for %s", dist_regex)
        valid_target = re.compile(dist_regex)
        for option in self.build_dir.glob("*.zip"):
            groups = valid_target.findall(str(option))
            logging.info("Considering %s: (%s)", option, groups)
            if groups:
                return option

        raise FileNotFoundError(f"No file matching {type} was found.")

    def __enter__(self):
        # Extract the emulator
        emu_master_dev = Path(self.tmp.name) / "emu-master-dev"
        emu_master_dev.mkdir(parents=True, exist_ok=True)
        sdk_repo = ZipFileWithAttr(self._find_dist_zip("emulator"))
        logging.info("Extracting %s to %s", sdk_repo.filename, emu_master_dev)
        sdk_repo.extractall(path=emu_master_dev)

        # Extract symbols.
        symbol_path = Path(self.tmp.name) / "symbols"
        symzip = self._find_dist_zip("emulator-symbols")
        if symzip:
            logging.info("Extracting %s to %s", symzip, emu_master_dev)
            symbols = ZipFileWithAttr(symzip)
            symbols.extractall(path=symbol_path)

        return shutil.which("emulator", path=emu_master_dev / "emulator"), symbol_path

    def __exit__(self, exc_type, exc_value, tb):
        self.tmp.__exit__(exc_type, exc_value, tb)


class PyRunner:
    """PyRunner

    A class that provides a convenient way to run python commands.
    It sets up the environment with the required variables,
    installs packages using pip, and runs the specified command
    with the given arguments and environment variables.

    Attributes:
        env (dict[str, str]): Environment variables for the command.
        This includes ANDROID_SDK_ROOT, ANDROID_HOME, and
        JAVA_HOME. If the platform is Linux, DISPLAY will also be included.

        py_exe (str): The path to the python interpreter.
    """

    def __init__(self):
        """Initialize PyRunner with the environment variables required
        for running the Python command.

        The environment variables include `ANDROID_SDK_ROOT`, `ANDROID_HOME` and `JAVA_HOME`.
        If the platform is Linux,  an attempt will be made to find or
        launch a vnc server and set its display as the value for the `DISPLAY`
        environment variable.
        """
        self.env = {
            "ANDROID_SDK_ROOT": str(ANDROID_SDK_ROOT),
            "ANDROID_HOME": str(ANDROID_SDK_ROOT),
            "JAVA_HOME": self._get_java_home(),
            # Make sure adb and java are on the path.
            "PATH": f"{self._get_jdk_path()}"
            + f"{os.pathsep}{ANDROID_SDK_ROOT / 'platform-tools'}"
            + f"{os.pathsep}{os.environ['PATH']}",
        }
        self.py_exe = shutil.which("python")
        if not shutil.which("adb", path=self.env["PATH"]):
            raise AdbNotFound(f"Unable to find adb on the path: {self.env['PATH']}")

        if platform.system() == "Linux":
            try:
                self.env["DISPLAY"] = self._get_X_Display()
            except NoXServer as xerr:
                if "NO_VNC_LAUNCH" in os.environ:
                    logging.warning(
                        "No X server available (%s), skipping vnc launch since NO_VNC_LAUNCH is set",
                        xerr,
                    )
                else:
                    logging.warning(
                        "No X server available (%s), attempting to launch a vnc server",
                        xerr,
                    )
                    subprocess.check_call("vncserver")
                    self.env["DISPLAY"] = self._get_X_Display()

        logging.info("Using environment: %s", self.env)

    def _get_jdk_path(self):
        """Gets the path to java + javac from AOSP"""
        jdk_map = {
            "windows": JDK_ROOT / "win" / "bin",
            "linux": JDK_ROOT / "linux" / "bin",
            "darwin-arm64": JDK_ROOT / "mac-arm64" / "Contents" / "Home" / "bin",
            "darwin-x86_64": JDK_ROOT / "mac" / "Contents" / "Home" / "bin",
        }
        jdk = jdk_map.get(OS_NAME, None)
        if OS_NAME == "darwin":
            jdk = jdk_map.get(f"{OS_NAME}-{platform.machine()}")
        return f"{jdk}"

    def _get_java_home(self):
        """Retrieves the path to the Java home directory from the active Java interpreter.

        Returns:
            str: Path to the Java home directory

        Raises:
            JavaNotFound: If no `java` interpreter is found on the system path.
        """
        jdk = self._get_jdk_path()
        java = shutil.which("java", path=jdk)
        if not java:
            raise JavaNotFound(
                f"No `java` interpreter on the path ({jdk}). Java is required for "
                + "creating the APK's used by the test."
            )

        is_windows = platform.system() == "Windows"
        status = subprocess.run(
            [java, "-XshowSettings:properties", "-version"],
            encoding="utf-8",
            capture_output=True,
            shell=is_windows,
            check=True,
        )
        java_home = [
            line.strip() for line in status.stderr.splitlines() if "java.home" in line
        ][0]

        return java_home.split("=")[1].strip()

    def _is_x_running(self, display: str) -> bool:
        """Checks if X server is running on specific display

        Args:
          display (str): the display name

        Return:
          bool: True if X is running, False otherwise
        """
        return (
            subprocess.run(["xset", "-display", display, "-q"], check=False).returncode
            == 0
        )

    def _get_X_Display(self) -> str:
        """Finds a working DISPLAY environment variable that is backed by a working
        X Server. This can launch a VNCServer if needed.

        Raises:
            NoXServer: If no working X server can be found.

        Returns:
            str: Value for the DISPLAY environment variable (i.e. ":XDISPLAY")
        """
        xdir = Path("/tmp/.X11-unix")
        if not xdir.exists():
            raise NoXServer(
                f"The directory {xdir} does not exist, no X server available."
            )

        for xdisplay in xdir.glob("X*"):
            display = f":{xdisplay.name[1:]}"
            logging.info("Checking to see if X11 is available at DISPLAY=%s", display)
            if self._is_x_running(display):
                return display

        raise NoXServer("Unable to find a working XServer")

    def pip_install(self, packages: [str]):
        """installs the specified packages using pip"

        Args:
            packages ([str]): The set of packages to install
        """
        self.run(["-m", "pip", "install", "-v", "--upgrade"] + packages)

    def run(
        self,
        args: List[str],
        env: Dict[str, str] = {},
        timeout: int = 300,
        cwd: str = os.getcwd(),
        check_output: bool = True,
    ) -> int:
        """Runs a Python command with the specified arguments, environment variables, and timeout.

        Args:
            args (List[str]): Set of arguments to give to the Python interpreter.
            env (Dict[str, str]): Optional environment variables to use.
            timeout (int): Optional timeout in seconds to apply to the command execution.
            cwd (str): The working directory to use for the command execution.
            check_output (bool): Set to True if a non-zero exit code should raise an exception.

        Returns:
            int: The exit code of the process.
        """
        emu_env = self.env.copy()
        emu_env.update(env)
        if env:
            logging.info("Using %s from %s", emu_env, self.env)
        return run(
            [self.py_exe] + args,
            timeout=timeout,
            extra_env=emu_env,
            cwd=cwd,
            check_output=check_output,
        )


class AospPyRunner(PyRunner):
    """AospPyRunner is a PyRunner that uses the Python interpreter that is in AOSP

    This python interpreter does not have SSL and hence has a series of limitations.
    This runner tries to minimize the impact of these limitations, by:

    - Creating a virtual environment in posix
    - Patch the windows interpreter to work with the pytests.
    """

    def __init__(self, repo, in_directory=None):
        super().__init__()
        self.repo = repo
        self.in_directory = in_directory
        if not in_directory:
            self.tmp = tempfile.TemporaryDirectory()
            self.in_directory = self.tmp.name

        if platform.system() == "Windows":
            self._fixup_windows_py3_dll()
            run(
                [
                    PYTHON,
                    AOSP_ROOT / "external" / "adt-infra" / "devpi" / "get-pip.py",
                    "--no-wheel",
                    "--no-setuptools",
                    "--index-url",
                    f"{repo}",
                ],
            )
            self.py_exe = PYTHON
            self.run(
                [
                    "-m",
                    "pip",
                    "install",
                    "--upgrade",
                    "virtualenv",
                    "--index-url",
                    f"{self.repo}",
                ]
            )
            self.env["PYTHONPATH"] = str(HERE / "src" / "hacks")
            virtualenv = "virtualenv"
        else:
            virtualenv = "venv"

        tmpdir = Path(self.in_directory)
        run(
            [
                PYTHON,
                "-m",
                virtualenv,
                tmpdir / ".venv",
            ],
            extra_env=self.env,
        )

        with open(tmpdir / ".venv" / "pip.ini", "w", encoding="utf-8") as fp:
            fp.write(
                f"""
[global]
index-url = {repo}
extra-index-url = http://localhost:3141/packages/staging
timeout = 2
retries = 0
"""
            )

        if platform.system() == "Windows":
            self.py_exe = tmpdir / ".venv" / "Scripts" / "python"
        else:
            self.py_exe = tmpdir / ".venv" / "bin" / "python"

        self.env["VIRTUAL_ENV"] = str(tmpdir / ".venv")

        self.run(
            [
                "-m",
                "pip",
                "install",
                "--upgrade",
                "pip",
                "wheel",
                "setuptools",
                "--index-url",
                f"{self.repo}",
            ]
        )

    def _fixup_windows_py3_dll(self):
        # Fixup incorrect dll in windows see b/265843618.
        py310dll = PYTHON_DIR / "python310.dll"
        py3dll = PYTHON_DIR / "Python3.dll"
        assert (
            py310dll
        ).exists(), (
            "python310.dll does not exist, did you upgrade the python interpreter?"
        )
        if not py3dll.exists():
            py3dll.symlink_to(py310dll)

    def pip_install(self, packages: [str]):
        """installs the specified packages using pip"

        Args:
            packages ([str]): The set of packages to install
        """
        super().pip_install(["--index-url", f"{self.repo}"] + packages)


def apply_xslt(python_exe: PyRunner, source: Path, xslt: Path, dest: Path):
    """Applies a specified XSLT file to an XML file and saves the result to a specified
    destination.


    Args:
        python_exe (PyRunner): The path to the Python executable that will be used
                to run the transform script.
        source (Path): The path to the Python executable that will be used to run
                the transform script.
        xslt (Path): The path to the XSLT file that will be used to transform
                the XML file.
        dest (Path): The path to the destination file where the result of the
                transformation will be saved.
    """
    try:
        python_exe.run(
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


def merge_results(python_exe: PyRunner, sources: [Path], dest: Path):
    try:
        python_exe.run(
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


async def collect_crash_reports(emulator: str, symbol_path: Path, logdir: Path):
    emulator_directory = Path(emulator).parent if emulator else None
    crash_report = CrashReporter(emulator_directory, symbol_path, GRPC_SERVICES)

    # Write them to disk
    await crash_report.write_reports_to_disk(logdir)

    # And report them..
    await crash_report.report_crashes()

    # After reporting them we will have ids, lets print them and remove them.
    await crash_report.report_crashes()
    await crash_report.clear()


def run_single_suite(
    emulator: str,
    use_exceptions: bool,
    logdir: Path,
    symbol_path: Path,
    tmpdir: str,
    build_target: str,
    pyrun: PyRunner,
    pytest_flags: list[str],
    avd_configs: list[str],
    collect: bool,
    name: str,
    fetcher: Optional[Path],
):
    if collect:
        pytest_flags.append("--setup-plan")
    if fetcher:
        pytest_flags.append(f"--fetcher={fetcher}")

    junit_test_results = Path(logdir) / f"{name}.xml"
    exit_code = 1
    try:
        exit_code = pyrun.run(
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
                f"--android_home={ANDROID_SDK_ROOT}",
            ]
            + pytest_flags,
            cwd=HERE,
            env={
                "ANDROID_EMU_ENABLE_CRASH_REPORTING": "YES",
                "ANDROID_AVD_HOME": str(tmpdir),
                "PYTEST_ADDOPTS": os.getenv("PYTEST_ADDOPTS") or "",
            },
            # Give pytest a chance to "nicely" terminate everything.
            timeout=2800 if platform.system() != "Windows" else 3200,
            check_output=False,
        )
    except subprocess.TimeoutExpired as timeout_exception:
        logging.info(
            "The test suite %s timed out after %s seconds",
            name,
            timeout_exception.timeout,
        )
        # Force the emulator to crash when the test suite timesout.
        run([ADB, "emu", "crash"], timeout=300)

    finally:
        # Let's see if we can collect crash reports..
        asyncio.run(collect_crash_reports(emulator, symbol_path, logdir))

        # Forcefully terminate all emulator processess
        pyrun.run(["-m", "emu.process.kill_emulator"], check_output=False)

        if not junit_test_results.exists():
            raise NoTestResultsProduced(
                f"We expected a junit report in {junit_test_results}."
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


def run_tests(
    emulator: str,
    use_exceptions: bool,
    logdir: Path,
    verbose: bool,
    symbol_path: Path,
    build_target: str,
    pyrun: PyRunner,
    tests_to_run,
    collect: bool,
    fetcher: Optional[Path],
):
    """runs tests on an emulator. It installs necessary packages, restarts adb,
    runs pytest and converts the results to a junit xml and HTML files.

    Args:

        emulator (str):       Path to the emulator binary
        use_exceptions(bool): True if an excpetion should be raised on pytest failures.
        symbol_path(Path):    Optional path to the symbols that belong with this emulator.
        logdir (Path):        The directory where all the logs will be written to
        verbose: (bool):      True if we should be (very) verbose.
        pyrun (PyRunner):     The python runner used to run python.
        tests_to_run (str, dict):
        collect: (bool):      True if the list of tests should be collected, not run.
    """
    # sanity checks
    verbose = ["-vvv"] if verbose else []
    emulator = str(resolve_emulator(emulator))
    logging.info(
        "Checking to see if PYTEST_ADDOPTS is available for running tests: %s",
        os.getenv("PYTEST_ADDOPTS"),
    )

    crash_retry = HERE.parent / "crash_retry"

    pyrun.pip_install(verbose + [AEMU_GRPC, SNAPTOOL, NETSIM_GRPC, HERE, crash_retry])

    logdir = Path(logdir)

    result_xmls = []
    skip_reports = []
    for name, cfg in tests_to_run:
        test_log_dir = logdir / name
        test_log_dir.mkdir(exist_ok=True, parents=True)
        with AdbServer(pyrun):
            with tempfile.TemporaryDirectory() as tmpdir:
                pytest_flags = cfg["pytest_flags"]
                avd_configs = json.dumps(cfg["avd_configs"])
                logging.info("Running %s (%s)", name, cfg["description"])
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
                    name,
                    fetcher,
                )
                result_xmls.append(res)
                skip_reports.append(test_log_dir.joinpath(name + "_skip.xml"))

    if collect:
        result = Path(logdir) / "COLLECT-embedded_test.xml"
    else:
        result = Path(logdir) / "TEST-embedded_test.xml"
    merge_results(python_exe=pyrun, sources=result_xmls, dest=result)
    xml_skip_report = Path(logdir) / "skipped_tests.xml"
    merge_skip_reports(python_exe=pyrun, sources=skip_reports, dest=xml_skip_report)
    apply_xslt(
        python_exe=pyrun,
        source=result,
        xslt=HERE / "cfg" / "asHtml.xslt",
        dest=Path(logdir) / "test_report.html",
    )
    apply_xslt(
        python_exe=pyrun,
        source=result,
        xslt=HERE / "cfg" / "liftSystemOut.xslt",
        dest=result,
    )
    apply_xslt(
        python_exe=pyrun,
        source=xml_skip_report,
        xslt=HERE / "cfg" / "skippedTests.xslt",
        dest=xml_skip_report.with_suffix(".html"),
    )


def merge_skip_reports(python_exe: PyRunner, sources: [Path], dest: Path):
    """Run the standalone skip report module

    Args:
        python_exe (PyRunner): The python runner used to run python.
        sources ([Path]): List of xml skip reports that are to be merged.
        dest (Path): The (optional) output file where the result will be written to.
    """
    try:
        python_exe.run(
            [
                "-m",
                f"emuxml.merge_skip_reports",
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


def parse_arguments():
    parser = argparse.ArgumentParser(
        usage="A simple test launcher for the emulator e2e tests.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "-e",
        "--emulator",
        dest="emulator",
        help="Path to the emulator binary that is used for running the tests. "
        + "Cannot be used in combination with the --build_dir flag",
    )

    parser.add_argument(
        "-b",
        "--build_dir",
        dest="build_dir",
        help="The directory where the emulator distributions can be found. "
        + "On the buildbots this is usually out/prebuilt_cached/builds. "
        + "Cannot be used in combination with the --emulator flag",
    )

    parser.add_argument(
        "-l",
        "--logdir",
        default=Path(os.getcwd()) / "testlogs",
        dest="logdir",
        help="The directory where the logs should be placed. "
        + "On the build bots this should be dist_dir/testlogs.",
    )

    parser.add_argument(
        "--symbols",
        dest="symbols",
        help="Path to the directory with breakpad symbols",
    )

    parser.add_argument(
        "--build_target",
        dest="build_target",
        help="The name of the build target",
        default="unknown-build-target",
    )

    parser.add_argument(
        "-d",
        "--directory",
        dest="virtual_env_dir",
        help="Path to the directory where to create the virtual environment"
        + ", omit to use a temporary directory",
    )

    parser.add_argument(
        "-g",
        "--generate",
        default=False,
        action="store_true",
        dest="generate",
        help="Create a virtual environment."
        + "This requires you to launch the devpi server found in "
        + f"{AOSP_ROOT / 'external' / 'adt_infra' / 'devpi'}."
        + "You can use this to obtain additional dependencies through pip download.",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        dest="verbose",
        default=False,
        action="store_true",
        help="Enable verbose logging",
    )

    parser.add_argument(
        "--no-aosp",
        action="store_true",
        dest="local_python",
        default=False,
        help="Use the current python interpreter v.s. the one in AOSP."
        + " You should only use this for debugging.",
    )

    parser.add_argument(
        "--failures_as_errors",
        dest="use_exceptions",
        default=False,
        action="store_true",
        help="Treat test failures as errors. Test failures will raise an "
        "exception when this flag is present.",
    )

    parser.add_argument(
        "--test_config",
        default=EMU_TEST_DIR / "cfg" / f"emulator_{OS_NAME}_tests.json",
        help="The test configuration file that describes which tests"
        + " should be run for each configuration",
    )

    parser.add_argument(
        "--test_suite",
        default=".*",
        help="Regex which will be used to determine which test suite to run",
    )

    parser.add_argument(
        "--collect-only",
        default=False,
        action="store_true",
        dest="collect",
        help="collect the list of tests, but do not run them",
    )

    parser.add_argument(
        "--fetcher",
        help="Optional path to the fetcher binary. If set this will be used "
        "for fetching system images.",
    )

    args = parser.parse_args()
    logdir = Path(args.logdir)
    logdir.mkdir(exist_ok=True, parents=True)
    log_name = '.'.join((os.path.basename(sys.argv[0]),
                         datetime.datetime.now().strftime('%Y%m%d-%H%M%S'), 'log'))
    configure_logging(logging.DEBUG if args.verbose else logging.INFO,
                      log_path=logdir.joinpath(log_name))

    if args.generate:
        if not args.virtual_env_dir:
            raise ValueError(
                "You must provide a virtual environment directory (-d/--directory)"
            )
        py_exe = AospPyRunner(
            "http://localhost:3141/packages/stable", args.virtual_env_dir
        )
        venv = Path(args.virtual_env_dir) / ".venv"
        print(f"Virtal environment installed in {venv}. Please run the activate script.")
        print("Note that you might have to run `pip download <package>` multiple times.")
        sys.exit(0)

    if args.build_dir and args.emulator:
        raise ValueError("Use either --build_dir or --emulator flag, not both.")

    if not args.build_dir and not args.emulator:
        raise ValueError("You must provide either --build_dir or --emulator flag.")

    return args


def main(args):
    if args.generate:
        repo = "http://localhost:3141/packages/stable"
    else:
        repo = AOSP_ROOT / "external" / "adt-infra" / "devpi" / "repo" / "simple"

        # Windows cannot handle the file:// url prefix properly (Due to C:\), so
        # we omit it
        if platform.system() != "Windows":
            repo = f"file://{repo}"

    py_exe = (
        PyRunner() if args.local_python else AospPyRunner(repo, args.virtual_env_dir)
    )

    with open(args.test_config, "r", encoding="utf-8") as file:
        test_cfg = json.load(file)

    tests_to_run = [
        (name, test_cfg[name])
        for name in test_cfg
        if (re.match(args.test_suite, name) and test_cfg[name]["status"] == "enabled")
    ]
    if not tests_to_run:
        raise NoTestResultsProduced(f"No enabled test suite matching {args.test_suite}")

    logging.info("Scheduling %d suites", len(tests_to_run))
    if args.build_dir:
        with TemporaryEmulatorDeploy(args.build_dir) as (emulator, symbols):
            run_tests(
                emulator=emulator,
                use_exceptions=args.use_exceptions,
                logdir=args.logdir,
                verbose=args.verbose,
                symbol_path=symbols,
                build_target=args.build_target,
                pyrun=py_exe,
                tests_to_run=tests_to_run,
                collect=args.collect,
                fetcher=args.fetcher,
            )
    else:
        run_tests(
            emulator=args.emulator,
            use_exceptions=args.use_exceptions,
            logdir=args.logdir,
            verbose=args.verbose,
            symbol_path=args.symbols,
            build_target=args.build_target,
            pyrun=py_exe,
            tests_to_run=tests_to_run,
            collect=args.collect,
            fetcher=args.fetcher,
        )


if __name__ == "__main__":
    arguments = parse_arguments()
    try:
        main(arguments)
    except KeyboardInterrupt:
        logging.critical("Terminated by user")
        sys.exit(1)
    except UnitTestFailure as utf:
        logging.error("Test failure: %s", str(utf))
        sys.exit(1)
    except Exception as exc:
        if arguments.verbose:
            logging.error("Failure during execution", exc_info=exc)
        else:
            logging.error("Failure during execution: %s", str(exc))
        sys.exit(1)
