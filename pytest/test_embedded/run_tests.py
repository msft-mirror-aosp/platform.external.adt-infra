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
import sys
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


def run(cmd, cwd=None, extra_env=None):
    if not cwd:
        cwd = os.getcwd()
    cwd = os.path.abspath(cwd)

    cmd = [str(c) for c in cmd]

    # We need to use a shell under windows, to set environment parameters.
    # otherwise we don't, since we will experience cmake invocation errors.
    use_shell = platform.system() == "Windows"
    local_env = os.environ
    if extra_env:
        local_env.update(extra_env)

    logging.info("Running: %s in %s", " ".join(cmd), cwd)
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=cwd,
        shell=use_shell,  # Needed on windows, otherwise the environment won't propagate.
        env=local_env,
    )

    _log_proc(proc)
    proc.wait()
    if proc.returncode != 0:
        raise Exception("Failed to run %s - %s" % (" ".join(cmd), proc.returncode))


def stop_adb():
    """Stops adb by calling kill-server"""
    run([ADB, "kill-server"])


def restart_adb():
    """Restarts adb, by stopping the server and restarting it."""
    stop_adb()
    run([ADB, "start-server"])


def resolve_emulator(emulator: str) -> Path:
    """Tries to resolve the emulator path."""
    emu = Path(emulator)
    if emu.exists():
        return emu

    # Ok, maybe we are missing an extension?
    emu = emu.with_suffix(".exe")
    if emu.exists():
        return emu

    assert (
        False
    ), "f{emulator} poinst to a non existent path (are you passing the right path to the --emulator flag?)"


def apply_xslt(source: Path, xslt: Path, dest: Path):
    try:
        run(
            [
                PYTHON,
                f"{HERE}/src/xml/transform.py",
                "--xml",
                source,
                "--xsl",
                xslt,
                "--out",
                dest,
            ]
        )
    except:
        logging.error("Failed to apply xslt: %s to %s")


def run_under_windows(args):
    if args.generate:
        repo = "http://localhost:3141/packages/stable"
    else:
        repo = AOSP_ROOT / "external" / "adt-infra" / "devpi" / "repo" / "simple"

    # sanity checks
    emulator = resolve_emulator(args.emulator)

    # Install pip, because of course we don't have it in windows
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

    run(
        [
            PYTHON,
            "-m",
            "pip",
            "install",
            "--upgrade",
            "--index-url",
            f"{repo}",
            AEMU_GRPC,
            SNAPTOOL,
        ],
    )
    run(
        [
            PYTHON,
            "-m",
            "pip",
            "install",
            "--upgrade",
            "--index-url",
            f"{repo}",
            "-e",
            HERE,
        ],
    )
    restart_adb()

    session_dir = Path(args.session) / "embedded_test" / "log"
    session_dir.mkdir(exist_ok=True, parents=True)
    with tempfile.TemporaryDirectory() as tmpdirname:
        junit_test_results = Path(tmpdirname) / "test_unit.xml"
        try:
            run(
                [
                    PYTHON,
                    "-m",
                    "pytest",
                    "-vv",
                    "-m",
                    "not perf",
                    f"--junitxml={junit_test_results}",
                    # Boot times in windows can be 6 mins, so lets give us 20 minutes
                    # of testing time before we give up.
                    "--timeout=1200",
                    f"--log-file={args.session}/embedded_test/log/pytest.log",
                    f"--emulator={emulator}",
                    f"--android_avd_home={tmpdirname}",
                    f"--android_home={ANDROID_SDK_ROOT}",
                ],
                cwd=HERE,
                extra_env={
                    "ANDROID_SDK_ROOT": str(ANDROID_SDK_ROOT),
                    "ANDROID_HOME": str(ANDROID_SDK_ROOT),
                    "ANDROID_EMU_ENABLE_CRASH_REPORTING": "YES",
                    "ANDROID_AVD_HOME": tmpdirname,
                },
            )
        finally:
            if junit_test_results.exists():
                apply_xslt(
                    source=junit_test_results,
                    xslt=HERE / "cfg" / "liftSystemOut.xslt",
                    dest=Path(args.session)
                    / "embedded_test"
                    / "test_embedded_test.xml",
                )
                apply_xslt(
                    source=junit_test_results,
                    xslt=HERE / "cfg" / "asHtml.xslt",
                    dest=Path(args.session) / "test_report.html",
                )


def run_under_posix():
    """Runs the run_tests.sh"""
    run([Path(HERE) / "run_tests.sh"] + sys.argv[1:], HERE)


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

    if platform.system() == "Windows":
        run_under_windows(args)
    else:
        run_under_posix()


if __name__ == "__main__":
    try:
        main()
    finally:
        stop_adb()
