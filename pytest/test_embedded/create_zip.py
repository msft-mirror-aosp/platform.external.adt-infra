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

"""Script to create a zip file of the End to End tests."""

import argparse
import logging
import pathlib
import tempfile
import time
from typing import Iterable, Optional
import zipfile

import run_tests
from src.emu.logging.log_handler import configure_logging


COPY_PATHS = (
    run_tests.HERE / "tests",
    run_tests.HERE / "cfg",
    run_tests.HERE / "test_runner.py",
    run_tests.HERE / "run_from_zip.py",
    run_tests.HERE / "pytest.ini",
)


def parse_arguments() -> argparse.Namespace:
    """Parses the command line arguments."""
    parser = argparse.ArgumentParser(
        usage="Creates a zip file for launching tests.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "-d",
        "--dest",
        help="Path to create the zip file in",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        dest="verbose",
        default=False,
        action="store_true",
        help="Enable verbose logging",
    )

    return parser.parse_args()


def _handle_symlink(
    zipf: zipfile.ZipFile,
    base: pathlib.Path,
    path: pathlib.Path,
    symlink_src: pathlib.Path,
) -> None:
    """Handles adding a symlink to the zipfile.

    If path is an absolute symlink that is relative to symlink_src, it will be altered to be
    relative to a directory of the same name in top level of the zip.

    Args:
      zipf: Zipfile object to add symlink to.
      base: Local path this file is relative to.
      path: Absolute path to the symlink.
      symlink_src: Local path an absolute symlink must be based in.
    """
    link = path.readlink()
    # Remove the windows unicode prefix if present as it breaks path comparison.
    if link.parts[0].startswith("\\\\?\\"):
        link = pathlib.Path(link.parts[0][4:], *link.parts[1:])
    if link.is_absolute() and not link.is_relative_to(symlink_src):
        logging.error("Symlink %s is not relative to %s", link, symlink_src)
        return

    rel_path = path.relative_to(base)
    zi = zipfile.ZipInfo(str(rel_path), time.localtime()[:6])
    zi.create_system = 3
    # NOTE: This is unix file mode (stat.S_IFLNK | 0o755) << 16.
    zi.external_attr = 2716663808

    if link.is_absolute():
        # Relative path to the top of the zip.
        to_parent = pathlib.Path(*[".."] * len(rel_path.parent.parts))
        zip_link = to_parent.joinpath(symlink_src.name, link.relative_to(symlink_src))
    else:
        zip_link = link  # Relative links do not need an update.
    zipf.writestr(zi, str(zip_link))

    logging.info("Archiving symlink: %s -> %s", path, zip_link)


def _zip_files(
    zipf: zipfile.ZipFile,
    base: pathlib.Path,
    paths: Iterable[pathlib.Path],
    symlink_src: Optional[pathlib.Path],
) -> None:
    """Add all the files in paths to zipf with archive paths relative to base."""
    for path in paths:
        if ".git" in path.parts:
            continue  # Skip .git directories and children.
        if path.is_symlink():
            if symlink_src is not None:
                _handle_symlink(zipf, base, path, symlink_src)
            else:
                logging.warning("Skipping symlink: %s", path)
        elif path.is_file():
            zipf.write(path, arcname=str(path.relative_to(base)))


def zip_path(
    zipf: zipfile.ZipFile, path: pathlib.Path, glob_match="**/*", symlink_src=None
) -> None:
    """Add the given path and any children to zipf."""
    paths = [path] if path.is_file() else path.glob(glob_match)
    _zip_files(zipf, path.parent, paths, symlink_src)


def main(args: argparse.Namespace) -> None:
    configure_logging(logging.DEBUG if args.verbose else logging.INFO)

    with zipfile.ZipFile(
        args.dest, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as zipf:

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_dir = pathlib.Path(tmp_dir)
            logging.info("Creating python virtualenv")
            level = logging.DEBUG if args.verbose else logging.INFO
            run_tests.create_pyrunner(False, tmp_dir, level)

            logging.info("Archiving virtualenv")
            zip_path(zipf, tmp_dir.joinpath(".venv"), symlink_src=run_tests.PYTHON_DIR)

        # NOTE: There are symlinks here, but they are all to protos within the same tree so can be
        # safefully ignored.
        logging.info("Archiving grpc protos")
        zip_path(zipf, run_tests.GRPC_SERVICES, glob_match="**/*.proto")

        logging.info("Archiving python")
        zip_path(zipf, run_tests.PYTHON_DIR, symlink_src=run_tests.PYTHON_DIR)

        for path in COPY_PATHS:
            logging.info("Archiving %s", path)
            zip_path(zipf, path)


if __name__ == "__main__":
    arguments = parse_arguments()
    main(arguments)
