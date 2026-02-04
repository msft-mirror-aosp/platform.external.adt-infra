"""Library to help creating and running test sequencer configs.

The *_type functions below are intended to be used as the type argument to add_argument().
"""

import argparse
from collections.abc import Callable
import os

from google.protobuf import text_format
from python.runfiles import Runfiles
from sequence import run

from test_seq.proto import test_sequencer_pb2


def path_type(value: str) -> str:
    """Turns a rlocationpath into an absolute path."""
    runfiles = Runfiles.Create()
    return runfiles.Rlocation(value)


def dir_type(value: str) -> str:
    return os.path.dirname(path_type(value))


def symlink_dir_type(value: str) -> str:
    sym_dir = os.path.join(os.environ["TEST_TMPDIR"], os.path.basename(value))
    os.symlink(dir_type(value), sym_dir, target_is_directory=True)
    return sym_dir


def main(
    parser: argparse.ArgumentParser,
    get_config: Callable[[argparse.Namespace], list[test_sequencer_pb2.AgentConfig]],
):
    _add_args(parser)
    # Process the config once using the FlagRegister to register any flags used from agent_common.py.
    # This ensures only used flags are registered as they are all considered required if used.
    get_config(_FlagRegister(parser))

    # Now parse the flags and create the config.
    args = parser.parse_args()
    cfg = text_format.MessageToString(
        test_sequencer_pb2.TestSequence(agent=get_config(args))
    )

    if args.mode == "print":
        print(cfg)
    elif args.mode == "run":
        # NOTE: All of the java tools are passed in, just use the first.
        run.run(args.test_seq_path, cfg, [args.java_path[0]])


def _add_args(parser: argparse.ArgumentParser):
    parser.add_argument(
        "--mode",
        choices=["print", "run"],
        default="run",
        help="Mode to run, print: print .txtpb, run: run the sequence",
    )
    parser.add_argument(
        "--test_seq_path",
        type=path_type,
        help="Path to the test sequencer binary",
        required=True,
    )
    parser.add_argument(
        "--java_path",
        nargs="+",
        type=dir_type,
        help="Paths to the java tools to put in PATH",
        required=True,
    )


_KNOWN_FLAGS = {
    "abi": lambda p: p.add_argument(
        "--abi", help="ABI to run the tests as", required=True
    ),
    "build_tools_extract_dir": lambda p: p.add_argument(
        "--build_tools_extract_dir",
        type=dir_type,
        help="Path to the extracted build tools",
        required=True,
    ),
    "emulator_access_json": lambda p: p.add_argument(
        "--emulator_access_json",
        type=path_type,
        help="Path to the emulator_access.json",
        required=True,
    ),
    "goldfish_zip": lambda p: p.add_argument(
        "--goldfish_zip", type=path_type, help="Path to the goldfish zip", required=True
    ),
    "hellovk_extract_dir": lambda p: p.add_argument(
        "--hellovk_extract_dir",
        type=dir_type,
        help="Path to the extracted hellovk app",
        required=True,
    ),
    "image_extract_dir": lambda p: p.add_argument(
        "--image_extract_dir",
        type=dir_type,
        help="Path to the extracted image",
        required=True,
    ),
    "platform_tools_extract_dir": lambda p: p.add_argument(
        "--platform_tools_extract_dir",
        type=dir_type,
        help="Path to the extracted platform tools",
        required=True,
    ),
    "tradefed_args": lambda p: p.add_argument(
        "--tradefed_args",
        help="Arguments to pass to tradefed (comma-separated)",
        required=True,
    ),
    "tradefed_extract_dir": lambda p: p.add_argument(
        "--tradefed_extract_dir",
        type=symlink_dir_type,
        help="Path to the extracted tradefed zip",
        required=True,
    ),
    "tradefed_zip": lambda p: p.add_argument(
        "--tradefed_zip",
        type=path_type,
        help="Path to the android-ets zip",
        required=True,
    ),
}


class _FlagRegister(argparse.Namespace):
    """Calls add_argument() for any known flag associated with a reference attribute."""

    def __init__(self, parser: argparse.ArgumentParser):
        self._parser = parser
        self._seen = set()

    def __getattr__(self, name):
        if name not in self._seen and name in _KNOWN_FLAGS:
            self._seen.add(name)
            _KNOWN_FLAGS[name](self._parser)
        return ""
