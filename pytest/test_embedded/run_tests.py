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
import logging
import os
import platform
import subprocess
import shutil
import sys
import tempfile
from zipfile import ZipFile, ZipInfo
from pathlib import Path
from queue import Queue
from threading import Thread

OS_NAME = platform.system().lower()
EMU_TEST_DIR = Path(os.path.dirname(__file__)).absolute()
AOSP_ROOT = EMU_TEST_DIR.parents[3]
SDK_EMULATOR = (
    AOSP_ROOT / "prebuilts" / "android-emulator-build" / "system-images" / OS_NAME
)
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
HERE = AOSP_ROOT / "external" / "adt-infra" / "pytest" / "test_embedded"
ADB = ANDROID_SDK_ROOT / "platform-tools" / "adb"

PYTHON_DIR = AOSP_ROOT / "prebuilts" / "python" / f"{OS_NAME}-x86"
if OS_NAME != "windows":
    PYTHON = PYTHON_DIR / "bin" / "python3"
else:
    PYTHON = PYTHON_DIR / "python.exe"
    ADB = ADB.with_suffix(".exe")


class NoXServer(Exception):
    pass


class BuildDirectoryNotFound(Exception):
    pass


class JavaNotFound(Exception):
    pass


class NoTestResultsProduced(Exception):
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

    return q


def run(cmd, cwd=None, extra_env=None, timeout=1200):
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

    _log_proc(proc)
    try:
        proc.wait(timeout=timeout)
        if proc.returncode != 0:
            raise Exception("Failed to run %s - %s" % (" ".join(cmd), proc.returncode))
    except subprocess.TimeoutExpired as te:
        logging.error(
            "The command %s timed out after %s seconds, terminating",
            " ".join(cmd),
            te.timeout,
        )
        proc.terminate()


def stop_adb():
    """Stops adb by calling kill-server"""
    run([ADB, "kill-server"], timeout=60)


def restart_adb():
    """Restarts adb, by stopping the server and restarting it."""
    stop_adb()
    run([ADB, "start-server"], timeout=60)


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
        "f{emulator} poinst to a non existent path (are you passing the right path to"
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

    def _find_dist_zip(self, type: str):
        valid_targets = {
            "linux": ["linux", "linux_aarch64"],
            "darwin": [
                "darwin_aarch64",
                "darwin",
            ],
            "windows": ["windows"],
        }
        for target in valid_targets[OS_NAME]:
            for option in self.build_dir.glob(f"sdk-repo-{target}-{type}-*.zip"):
                return option

    def __enter__(self):
        # Extract the emulator
        emu_master_dev = Path(self.tmp.name) / "emu-master-dev"
        emu_master_dev.mkdir(parents=True, exist_ok=True)
        sdk_repo = ZipFileWithAttr(self._find_dist_zip("emulator"))
        logging.info("Extracting %s to %s", sdk_repo.filename, emu_master_dev)
        sdk_repo.extractall(path=emu_master_dev)

        # Extract symbols.
        symbol_path = Path(self.tmp.name) / "symbols"
        symzip = self._find_dist_zip("breakpad-symbols")
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
        }
        self.py_exe = shutil.which("python")
        if platform.system() == "Linux":
            try:
                display = self._get_X_Display()
            except NoXServer as xerr:
                logging.warning(
                    "No X server available (%s), attemtping to launch a vnc server",
                    xerr,
                )
                subprocess.check_call("vncserver")
                display = self._get_X_Display()

            self.env["DISPLAY"] = display

    def _get_java_home(self):
        """Retrieves the path to the Java home directory from the active Java interpreter.

        Returns:
            str: Path to the Java home directory

        Raises:
            JavaNotFound: If no `java` interpreter is found on the system path.
        """
        if not shutil.which("java"):
            raise JavaNotFound(
                "No `java` interpreter on the path. Java is required for "
                + "creating the APK's used by the test."
            )

        is_windows = platform.system() == "Windows"
        status = subprocess.run(
            ["java", "-XshowSettings:properties", "-version"],
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
            subprocess.run(
                ["xset", "-display", display, "-q"],
            ).returncode
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
        self.run(["-m", "pip", "install", "--upgrade"] + packages)

    def run(
        self, args: [str], env: dict[str, str] = {}, timeout: int = 300, cwd=os.getcwd()
    ):
        """This method runs a Python command with the specified arguments, environment variables, and timeout.

        Args:
            args ([str]): Set of arguments to give to python interpreter
            env (dict[str, str]): Optional environment to use
            timeout (int): Optional timeout in seconds to use.
        """
        emu_env = self.env.copy()
        emu_env.update(env)
        logging.info("Using %s from %s", emu_env, self.env)
        run(
            [self.py_exe] + args,
            timeout=timeout,
            extra_env=emu_env,
            cwd=cwd,
        )


class AospPyRunner(PyRunner):
    """AospPyRunner is a PyRunner that uses the Python interpreter that is in AOSP

    This python interpreter does not have SSL and hence has a series of limitations.
    This runner tries to minimize the impact of these limitations, by:

    - Creating a virtual environment in posix
    - Patch the windows interpreter to work with the pytests.
    """

    def __init__(self, repo):
        super().__init__()
        self.repo = repo
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
        else:
            self.tmp = tempfile.TemporaryDirectory()
            tmpdir = Path(self.tmp.name)
            run(
                [
                    PYTHON,
                    "-m",
                    "venv",
                    tmpdir / ".venv",
                ],
            )

            self.py_exe = tmpdir / ".venv" / "bin" / "python"
            self.env["VIRTUAL_ENV"] = str(tmpdir / ".venv")

        self.run(
            ["-m", "pip", "install", "--upgrade", "pip", "--index-url", f"{self.repo}"]
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
        if platform.system() == "Windows":
            super().pip_install(
                [
                    "--user",
                    "--upgrade",
                    "--index-url",
                    f"{self.repo}",
                ]
                + packages
            )
        else:
            super().pip_install(
                ["--index-url", f"{self.repo}"] + packages,
            )


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
                f"{HERE}/src/xml/transform.py",
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


def run_tests(
    emulator: str,
    use_exceptions: bool,
    logdir: Path,
    verbose: bool,
    symbol_path: Path,
    pyrun: PyRunner,
):
    """runs tests on an emulator. It installs necessary packages, restarts adb,
    runs pytest and converts the results to a junit xml and HTML files.

    Args:

        emulator (str):    Path to the emulator binary
        use_exceptions(bool): True if an excpetion should be raised on pytest failures.
        symbol_path(Path): Optional path to the symbols that belong with this emulator.
        logdir (Path):     The directory where all the logs will be written to
        verbose: (bool):   True if we should be (very) verbose.
        pyrun (PyRunner):  The python runner used to run python.
    """
    # sanity checks
    verbose = ["-vvv"] if verbose else []
    emulator = str(resolve_emulator(emulator))

    pyrun.pip_install(verbose + [AEMU_GRPC, SNAPTOOL, HERE])
    restart_adb()

    logdir = Path(logdir) / "embedded_test" / "log"
    logdir.mkdir(exist_ok=True, parents=True)
    with tempfile.TemporaryDirectory() as tmpdir:
        junit_test_results = Path(tmpdir) / "test_unit.xml"
        try:
            pyrun.run(
                [
                    "-m",
                    "pytest",
                    "-vv",
                    "-m",
                    "not perf",
                    f"--junitxml={junit_test_results}",
                    # Boot times in windows can be >6 mins, and we are booting several times!
                    # We will give us at most 45 minutes.
                    "--timeout=2700",
                    f"--log-file={logdir}/pytest.log",
                    f"--emulator={emulator}",
                    f"--symbols={symbol_path}",
                    f"--android_avd_home={tmpdir}",
                    f"--android_home={ANDROID_SDK_ROOT}",
                ],
                cwd=HERE,
                env={
                    "ANDROID_EMU_ENABLE_CRASH_REPORTING": "YES",
                    "ANDROID_AVD_HOME": str(tmpdir),
                },
                timeout=2800,  # Give pytest a chance to "nicely" terminate everything.
            )
        except:
            # Forward any exceptions in case we did not produce an
            # junit result.
            if use_exceptions or not junit_test_results.exists():
                raise
        finally:
            if not junit_test_results.exists():
                raise NoTestResultsProduced(f"We expected a junit report in {junit_test_results}.")
            else:
                apply_xslt(
                    python_exe=pyrun,
                    source=junit_test_results,
                    xslt=HERE / "cfg" / "liftSystemOut.xslt",
                    dest=Path(logdir) / "test_embedded_test.xml",
                )
                apply_xslt(
                    python_exe=pyrun,
                    source=junit_test_results,
                    xslt=HERE / "cfg" / "asHtml.xslt",
                    dest=Path(logdir) / "test_report.html",
                )


def main():
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
        "-s",
        "--session_dir",
        dest="unused",
        help="** DEPRECATED **. Use --build_dir or --emulator in combination "
        + "with --logdir. This parameter will be removed soon.",
    )

    parser.add_argument(
        "-l",
        "--logdir",
        default=Path(os.getcwd()),
        dest="logdir",
        help="The directory where the logs should be placed. "
        + "On the build bots this should be dist_dir/testlogs.",
    )

    parser.add_argument(
        "--symbols",
        dest="symbols",
        help="Path to the directory or zipfile with breakpad symbols",
    )

    parser.add_argument(
        "-g",
        "--generate",
        default=False,
        action="store_true",
        dest="generate",
        help="Use the devpi server to obtain all required packages. "
        + "This requires you to launch the devpi server found in "
        + f"{AOSP_ROOT / 'external' / 'adt_infra' / 'devpi'}",
    )

    parser.add_argument(
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
        help="Use the current python interpreter v.s. the one in AOSP. You should only use this for debugging.",
    )

    parser.add_argument(
        "--failures_as_errors",
        dest="use_exceptions",
        default=False,
        action="store_true",
        help="Treat test failures as errors. Test failures will raise an "
        "exception when this flag is present.",
    )

    args = parser.parse_args()

    lvl = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(format="%(asctime)s %(message)s", datefmt="%H:%M:%S", level=lvl)

    if args.build_dir and args.emulator:
        raise Exception("Use either --build_dir or --emulator not both.")

    if args.generate:
        repo = "http://localhost:3141/packages/stable"
    else:
        repo = AOSP_ROOT / "external" / "adt-infra" / "devpi" / "repo" / "simple"

        # Windows cannot handle the file:// url prefix properly (Due to C:\), so
        # we omit it
        if platform.system() != "Windows":
            repo = f"file://{repo}"

    py_exe = PyRunner() if args.local_python else AospPyRunner(repo)

    if args.build_dir:
        with TemporaryEmulatorDeploy(args.build_dir) as (emulator, symbols):
            run_tests(
                emulator=emulator,
                use_exceptions=args.use_exceptions,
                logdir=args.logdir,
                verbose=args.verbose,
                symbol_path=symbols,
                pyrun=py_exe,
            )
    else:
        run_tests(
            emulator=args.emulator,
            use_exceptions=args.use_exceptions,
            logdir=args.logdir,
            verbose=args.verbose,
            symbol_path=args.symbols,
            pyrun=py_exe,
        )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.critical("Terminated by user")
        sys.exit(1)
    except Exception as exc:
        logging.critical("Failure during execution", exc_info=exc)
        sys.exit(1)
    finally:
        stop_adb()
