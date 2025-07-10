# Copyright 2024 - The Android Open Source Project
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

"""Test runner for use with the test zip archive.

This must be run within the virtual environment to function correctly.

Example:

$ ./.venv/bin/python3 run_from_zip.py ...
"""

import argparse
import logging
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
from typing import Dict, List, Optional

from emu.logging.log_handler import configure_logging

import test_runner

BASE_DIR = Path(__file__).parent.resolve()

OS_NAME = platform.system().lower()

# These build IDs should stay in sync with the versions checked into the source tree.
COMMAND_LINE_TOOLS_BID = "11076708"
COMMAND_LINE_TOOLS_TARGET = "studio-linux"
COMMAND_LINE_TOOLS_RESOURCE_MAP = {
    "darwin": "artifacts/commandlinetools_mac.zip",
    "linux": "artifacts/commandlinetools_linux.zip",
    "windows": "artifacts/commandlinetools_win.zip",
}

PLATFORM_TOOLS_BID = "11411520"
PLATFORM_TOOLS_TARGET_MAP = {
    "darwin": "sdk_mac",
    "linux": "sdk",
    "windows": "sdk",
}
PLATFORM_TOOLS_RESOURCE = f"sdk-repo-{OS_NAME}-platform-tools-{PLATFORM_TOOLS_BID}.zip"

if OS_NAME == "windows":
    PYTHON = BASE_DIR / ".venv" / "Scripts" / "python3.exe"
else:
    PYTHON = BASE_DIR / ".venv" / "bin" / "python3"


class FetcherFlagRequiredError(Exception):
    pass


def parse_arguments() -> argparse.Namespace:
    """Parses the command line arguments."""
    parser = argparse.ArgumentParser(
        usage="A simple launcher for the emulator e2e tests.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "-e",
        "--emulator",
        dest="emulator",
        required=True,
        help="Path to the emulator binary that is used for running the tests.",
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
        required=True,
        help="Path to the directory with breakpad symbols",
    )

    parser.add_argument(
        "--build_target",
        dest="build_target",
        help="The name of the build target",
        default="unknown-build-target",
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
        "--test_config",
        help="The test configuration file that describes which tests"
        + " should be run for each configuration",
        required=True,
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
        help="Path to the fetcher binary used for fetching system images.",
    )

    parser.add_argument(
        "--system_image_path",
        help="Optional path to use for the system image for all tests.",
    )

    parser.add_argument(
        "--android_home",
        help="Optional path to use for ANDROID_HOME.",
    )

    return parser.parse_args()


class VenvRunner:
    """PyRunner that assumes it is already running out of the virtualenv."""

    def __init__(self, android_home: Path):
        self.env = {
            "ANDROID_SDK_ROOT": str(android_home),
            "ANDROID_HOME": str(android_home),
            "PATH": f"{os.pathsep}{android_home / 'platform-tools'}"
            + f"{os.pathsep}{os.environ['PATH']}",
        }

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
            [sys.executable] + args,
            timeout=timeout,
            extra_env=emu_env,
            cwd=cwd,
            check_output=check_output,
        )


def create_android_home(fetcher: Path, base_dir: Path) -> Path:
    """Creates the ANDROID_HOME environment at base_dir/android_home."""
    android_home = base_dir.joinpath("android_home")
    android_home.mkdir()
    clt_resource = COMMAND_LINE_TOOLS_RESOURCE_MAP[OS_NAME]
    pt_target = PLATFORM_TOOLS_TARGET_MAP[OS_NAME]
    proc = subprocess.run(
        [
            fetcher,
            f"ab,{COMMAND_LINE_TOOLS_BID},{COMMAND_LINE_TOOLS_TARGET},{clt_resource}",
            f"ab,{PLATFORM_TOOLS_BID},{pt_target},{PLATFORM_TOOLS_RESOURCE}",
        ],
        check=True,
        capture_output=True,
        encoding="utf-8",
    )
    clt_out, pt_out = proc.stdout.strip().splitlines()
    android_home.joinpath("cmdline-tools").symlink_to(Path(clt_out) / "cmdline-tools")
    android_home.joinpath("platform-tools").symlink_to(Path(pt_out) / "platform-tools")
    android_home.joinpath("platforms").mkdir()
    return android_home


def main(args: argparse.Namespace) -> None:
    configure_logging(
        logging.DEBUG if args.verbose else logging.INFO,
        log_path=test_runner.get_log_path(Path(args.logdir)),
    )
    with tempfile.TemporaryDirectory() as tmp_dir:
        if not args.fetcher:
            if not args.android_home or not args.system_image_path:
                raise FetcherFlagRequiredError('--fetcher is required unless both --android_home '
                                               'and --system_image_path are specified')
            fetcher = None
            android_home = Path(args.android_home)
        else:
            fetcher = Path(args.fetcher)
            android_home = create_android_home(fetcher, Path(tmp_dir))

        pyrun = VenvRunner(android_home)
        tests_to_run = test_runner.get_tests_to_run(args.test_config, args.test_suite,
                                                    args.system_image_path)


        logging.info("Scheduling %d suites", len(tests_to_run))

        test_runner.run_tests(
            emulator=args.emulator,
            use_exceptions=False,
            logdir=args.logdir,
            symbol_path=args.symbols,
            build_target=args.build_target,
            pyrun=pyrun.run,
            tests_to_run=tests_to_run,
            collect=args.collect,
            fetcher=fetcher,
            android_home=android_home,
            grpc_services=BASE_DIR.joinpath("android-grpc"),
        )


if __name__ == "__main__":
    arguments = parse_arguments()
    main(arguments)
