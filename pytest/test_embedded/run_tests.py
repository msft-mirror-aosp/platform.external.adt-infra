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
import tempfile
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


def _reader(pipe, logfn):
    try:
        with pipe:
            for line in iter(pipe.readline, b""):
                logfn(line[:-1].decode("utf-8").strip())
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


class PyRunner:
    """A utility class that helps to run Python commands and install packages within
    a specified repository."""

    def __init__(self, repo):
        self.repo = repo
        self.env = {
            "ANDROID_SDK_ROOT": str(ANDROID_SDK_ROOT),
            "ANDROID_HOME": str(ANDROID_SDK_ROOT),
        }
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
            self.pip_exe = tmpdir / ".venv" / "bin" / "pip3"
            self.env["VIRTUAL_ENV"] = str(tmpdir / ".venv")

        self.run(
            ["-m", "pip", "install", "--upgrade", "pip", "--index-url", f"{self.repo}"]
        )

    def run(
        self, args: [str], env: dict[str, str] = {}, timeout: int = 300, cwd=os.getcwd()
    ):
        """This method runs a Python command with the specified arguments, environment variables, and timeout.

        Args:
            args (str]): Set of arguments to give to python interpreter
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
            packages (str]): The set of packages to install
        """
        if platform.system() == "Windows":
            self.run(
                ["-m", "pip", "install", "--upgrade", "--index-url", f"{self.repo}"]
                + packages,
                timeout=300,
            )
        else:
            run(
                [self.pip_exe, "install", "--upgrade", "--index-url", f"{self.repo}"]
                + packages,
                timeout=300,
                extra_env=self.env,
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
        logging.error("Failed to apply xslt: %s to %s due to (%s)", xslt, source, err)


def run_tests(
    args,
    pyrun: PyRunner,
):
    """runs tests on an emulator. It installs necessary packages, restarts adb,
    runs pytest and converts the results to a junit xml and HTML files.

    Args:
        args (_type_): The arguments passed to the script. It is expected that it has a
            field emulator which is used to resolve the emulator.
        python_executable (Path):  The path to the Python executable that will be
            used to run the test and packages.
        pip_repository (Path):  The URL of the pip repository that will be used to
            install packages.
        tmpdir (Path): The path to the temporary directory where intermediate files will be stored.
        env: The additional envirornment
    """
    # sanity checks
    emulator = str(resolve_emulator(args.emulator))

    pyrun.pip_install([AEMU_GRPC, SNAPTOOL, HERE])
    restart_adb()

    logdir = Path(args.logdir) / "embedded_test" / "log"
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
                    "-x",
                    f"--junitxml={junit_test_results}",
                    # Boot times in windows can be 6 mins, so lets give us 20 minutes
                    # of testing time before we give up.
                    "--timeout=1200",
                    f"--log-file={args.logdir}/embedded_test/log/pytest.log",
                    f"--emulator={emulator}",
                    f"--android_avd_home={tmpdir}",
                    f"--android_home={ANDROID_SDK_ROOT}",
                ],
                cwd=HERE,
                env={
                    "ANDROID_EMU_ENABLE_CRASH_REPORTING": "YES",
                    "ANDROID_AVD_HOME": str(tmpdir),
                },
                timeout=1210,  # Give pytest a chance to "nicely" terminate everything.
            )
        finally:
            if junit_test_results.exists():
                apply_xslt(
                    python_exe=pyrun,
                    source=junit_test_results,
                    xslt=HERE / "cfg" / "liftSystemOut.xslt",
                    dest=Path(args.logdir) / "embedded_test" / "test_embedded_test.xml",
                )
                apply_xslt(
                    python_exe=pyrun,
                    source=junit_test_results,
                    xslt=HERE / "cfg" / "asHtml.xslt",
                    dest=Path(args.logdir) / "test_report.html",
                )


def main():
    parser = argparse.ArgumentParser(
        usage="A simple test launcher for the emulator e2e tests."
    )

    parser.add_argument(
        "-e",
        "--emulator",
        dest="emulator",
        help="Path to the emulator binary that is used for running the tests.",
    )

    parser.add_argument(
        "-s",
        "--session_dir",
        default=os.getcwd(),
        dest="session",
        help="Session directory used by the build bot, this is were all the .zip files can be found.",
    )

    parser.add_argument(
        "-l",
        "--logdir",
        default=Path(os.getcwd()),
        dest="logdir",
        help="The directory where the logs should be placed, defaults .",
    )

    parser.add_argument(
        "-g",
        "--generate",
        default=False,
        action="store_true",
        dest="generate",
        help="Use the devpi server to obtain all required packages.",
    )
    parser.add_argument(
        "--verbose",
        dest="verbose",
        default=False,
        action="store_true",
        help="Verbose logging",
    )

    args = parser.parse_args()

    lvl = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=lvl)

    if args.generate:
        repo = "http://localhost:3141/packages/stable"
    else:
        repo = AOSP_ROOT / "external" / "adt-infra" / "devpi" / "repo" / "simple"
        repo = f"file://{repo}"

    py_exe = PyRunner(repo)
    run_tests(args, pyrun=py_exe)


if __name__ == "__main__":
    try:
        main()
    finally:
        stop_adb()
