"""Library to help creating and running test sequencer configs.

The *_type functions below are intended to be used as the type argument to add_argument().
"""

import argparse
from collections.abc import Callable
import os

from python.runfiles import Runfiles
from sequence import run


def path_type(value: str) -> str:
    """Turns a relative path into an absolute one."""
    runfiles = Runfiles.Create()
    return runfiles.Rlocation(value)


def dir_type(value: str) -> str:
    return os.path.dirname(path_type(value))


def symlink_dir_type(value: str) -> str:
    sym_dir = os.path.join(os.environ["TEST_TMPDIR"], os.path.basename(value))
    os.symlink(dir_type(value), sym_dir, target_is_directory=True)
    return sym_dir


def add_args(parser: argparse.ArgumentParser):
    parser.add_argument(
        "--mode",
        choices=["print", "run"],
        default="run",
        help="Mode to run, print: print .txtpb, run: run the sequence",
    )
    parser.add_argument(
        "--test_seq_path", type=path_type, help="Path to the test sequencer binary"
    )


def main(args: argparse.Namespace, config: str):
    if args.mode == "print":
        print(config)
    elif args.mode == "run":
        run.run(args.test_seq_path, config)
