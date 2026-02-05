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
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional
from zipfile import ZipFile, ZipInfo

# Note we are not part of the package!
from src.emu.logging.log_handler import configure_logging

import test_runner
from git import Git

OS_NAME = platform.system().lower()
HERE = Path(os.path.dirname(__file__)).absolute()
AOSP_ROOT = HERE.parents[3]
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

PYTHON_DIR = AOSP_ROOT / "prebuilts" / "python" / f"{OS_NAME}-x86"
if OS_NAME != "windows":
    PYTHON = PYTHON_DIR / "bin" / "python3"
else:
    PYTHON = PYTHON_DIR / "python.exe"

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


class GitOpenFiles(Exception):
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


class TemporaryEmulatorDeploy:
    """Deploys the emulator from the build directory, cleaning it up after usage."""

    def __init__(self, build_dir):
        self.build_dir = Path(build_dir)
        self.tmp = tempfile.TemporaryDirectory()

        if not self.build_dir.exists():
            raise BuildDirectoryNotFound(
                f"{self.build_dir} does not exist, are you launching the scripts from {AOSP_ROOT}?"
            )

    def _find_dist_zip(self, type: str, dist_regex: Optional[str] = None) -> Optional[Path]:
        if not dist_regex:
            dist_regex = (
                r"sdk-repo-(linux|linux_aarch64|darwin|darwin_aarch64|windows)-"
                f"{type}"
                r"-((standalone-|P?)\d+).zip"
            )

        logging.info("Looking for %s", dist_regex)
        valid_target = re.compile(dist_regex)
        for option in self.build_dir.glob("*.zip"):
            groups = valid_target.findall(option.name)
            logging.info("Considering %s: (%s)", option, groups)
            if groups:
                return option

        return None

    def __enter__(self):
        # Extract the emulator
        emu_master_dev = Path(self.tmp.name) / "emu-master-dev"
        emu_master_dev.mkdir(parents=True, exist_ok=True)
        emu_zip = self._find_dist_zip("emulator")
        if not emu_zip:
            raise FileNotFoundError(f"No file matching emulator was found in {self.build_dir}")

        sdk_repo = ZipFileWithAttr(emu_zip)
        logging.info("Extracting %s to %s", sdk_repo.filename, emu_master_dev)
        sdk_repo.extractall(path=emu_master_dev)

        # Extract symbols.
        symbol_path = Path(self.tmp.name) / "symbols"
        symzip = self._find_dist_zip("emulator-symbols")
        if symzip:
            logging.info("Extracting %s to %s", symzip, emu_master_dev)
            symbols = ZipFileWithAttr(symzip)
            symbols.extractall(path=symbol_path)

        # Extract fishtank.
        fishtank_path = None
        fishtank_regex = (
            r"FISHTANK-sdk-repo-(linux|linux_aarch64|darwin|darwin_aarch64|windows)-"
            r"emu-((standalone-|P?)\d+).zip"
        )
        fishtank_zip = self._find_dist_zip("", dist_regex=fishtank_regex)
        if fishtank_zip:
            fishtank_path = Path(self.tmp.name) / "fishtank-dist"
            logging.info("Extracting %s to %s", fishtank_zip, fishtank_path)
            fishtank = ZipFileWithAttr(fishtank_zip)
            fishtank.extractall(path=fishtank_path)

        return (
            shutil.which("emulator", path=emu_master_dev / "emulator"),
            symbol_path,
            shutil.which("fishtank", path=fishtank_path / "fishtank"),
        )

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

        Returns:
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
        self.run(["-m", "pip", "install", "--upgrade"] + packages, timeout=900)

    def run(
        self,
        args: List[str],
        env: Optional[Dict[str, str]] = None,
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
        if env:
            emu_env.update(env)
            logging.info("Using %s from %s", emu_env, self.env)
        return test_runner.run(
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
            test_runner.run(
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
        test_runner.run(
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


def parse_arguments():
    parser = argparse.ArgumentParser(
        usage="A simple test launcher for the emulator e2e tests.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--local_run",
        default=False,
        dest="local_run",
        action="store_true",
        help="Queue the run in 'local' mode, so that assets and dependencies will be searched for locally "
        + ", as opposed to the infrastructure configured path.",
    )

    parser.add_argument(
        "-e",
        "--emulator",
        dest="emulator",
        help="Path to the emulator binary that is used for running the tests. "
        + "Cannot be used in combination with the --build_dir flag",
    )

    parser.add_argument(
        "--fishtank",
        dest="fishtank",
        help="Path to the fishtank binary that is used for running the tests. "
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
        "-p",
        "--presubmit",
        nargs="*",
        help="Run tests against tests that were changed in the given commit, or set of files.",
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
        help=argparse.SUPPRESS,  # Suppress -v/--verbose from help
    )

    parser.add_argument(
        "--log-level",
        dest="log_level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level. Overrides --verbose.",
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
        default=HERE / "cfg" / f"emulator_{OS_NAME}_tests.json",
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

    parser.add_argument(
        "--system_image_path",
        help="Optional path to use for the system image for all tests.",
    )

    args = parser.parse_args()
    log_level = logging.DEBUG if args.verbose else logging.INFO
    if args.log_level:
        log_level = getattr(logging, args.log_level)
    configure_logging(
        log_level,
        log_path=test_runner.get_log_path(Path(args.logdir)),
    )

    if args.generate:
        if not args.virtual_env_dir:
            raise ValueError(
                "You must provide a virtual environment directory (-d/--directory)"
            )
        AospPyRunner("http://localhost:3141/packages/stable", args.virtual_env_dir)
        venv = Path(args.virtual_env_dir) / ".venv"
        print(
            f"Virtal environment installed in {venv}. Please run the activate script."
        )
        print(
            "Note that you might have to run `pip download <package>` multiple times."
        )
        sys.exit(0)

    if args.build_dir and args.emulator:
        raise ValueError("Use either --build_dir or --emulator flag, not both.")

    if not args.build_dir and not args.emulator:
        raise ValueError("You must provide either --build_dir or --emulator flag.")

    return args


def create_pyrunner(
    local_python: bool, virtual_env_dir: str, log_level: int
) -> PyRunner:
    """Creates a PyRunner object, installing the needed pip packages."""
    repo = AOSP_ROOT / "external" / "adt-infra" / "devpi" / "repo" / "simple"

    # Windows cannot handle the file:// url prefix properly (Due to C:\), so
    # we omit it
    if platform.system() != "Windows":
        repo = f"file://{repo}"

    py_exe = PyRunner() if local_python else AospPyRunner(repo, virtual_env_dir)
    verbose_flags = ["-vvv"] if log_level == logging.DEBUG else []
    py_exe.pip_install(verbose_flags + [AEMU_GRPC, SNAPTOOL, NETSIM_GRPC, HERE])
    return py_exe


def main(args):
    if args.presubmit:
        # We are doing a presubmit run
        git = Git()
        changes = []
        for file_or_sha in args.presubmit:
            if git.is_valid_git_commit(file_or_sha):
                changes += git.changed_files(file_or_sha)
            else:
                changes.append(Path(file_or_sha))

        tests = Path("pytest/test_embedded/tests")
        short = Path("tests")
        changes = [
            x.name
            for x in changes
            if (x.is_relative_to(tests) or x.is_relative_to(short))
            and x.name.endswith(".py")
        ]

        if not changes:
            logging.info("No tests where changed, no need to run presubmit.")
            exit(0)

        os.environ["PYTEST_ADDOPTS"] = " ".join([f"-k {test}" for test in changes])
        logging.info(
            "Adding '%s' to PYTEST_ADDOPTS to run specific tests.",
            os.environ["PYTEST_ADDOPTS"],
        )

    py_exe = create_pyrunner(
        args.local_python, args.virtual_env_dir, logging.getLogger().getEffectiveLevel()
    )
    tests_to_run = test_runner.get_tests_to_run(args.test_config, args.test_suite,
                                                args.system_image_path)

    logging.info("Scheduling %d suites", len(tests_to_run))
    if args.build_dir:
        with TemporaryEmulatorDeploy(args.build_dir) as (emulator, symbols, fishtank):
            test_runner.run_tests(
                emulator=emulator,
                use_exceptions=args.use_exceptions,
                logdir=args.logdir,
                symbol_path=symbols,
                build_target=args.build_target,
                pyrun=py_exe.run,
                tests_to_run=tests_to_run,
                collect=args.collect,
                fetcher=args.fetcher,
                android_home=ANDROID_SDK_ROOT,
                grpc_services=GRPC_SERVICES,
                local_run=args.local_run,
                fishtank=fishtank,
            )
    else:
        test_runner.run_tests(
            emulator=args.emulator,
            use_exceptions=args.use_exceptions,
            logdir=args.logdir,
            symbol_path=args.symbols,
            build_target=args.build_target,
            pyrun=py_exe.run,
            tests_to_run=tests_to_run,
            collect=args.collect,
            fetcher=args.fetcher,
            android_home=ANDROID_SDK_ROOT,
            grpc_services=GRPC_SERVICES,
            local_run=args.local_run,
            fishtank=args.fishtank,
        )


if __name__ == "__main__":
    arguments = parse_arguments()
    try:
        main(arguments)
    except KeyboardInterrupt:
        logging.critical("Terminated by user")
        sys.exit(1)
    except test_runner.UnitTestFailure as utf:
        logging.error("Test failure: %s", str(utf))
        sys.exit(1)
    except Exception as exc:
        if arguments.verbose:
            logging.error("Failure during execution", exc_info=exc)
        else:
            logging.error("Failure during execution: %s", str(exc))
        sys.exit(1)
