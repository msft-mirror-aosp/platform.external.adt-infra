"""Tool to generate and run a test sequence.

The sequence can have %(key)s string template parameters which will be filled
from the --template_args and --template_path_args values. Both of these flags
take space separated key value pairs. The --template_path_args values must be
relative paths, which will be converted to absolute paths before filling in
the sequence.

Usage:
    ./run_sequence.py --test_seq_path <test_seq path> --seq_path <seq path> \
       [--template_args <key> <value>] \
       [--template_path_args <key> <value> ...]
"""

import argparse
from collections.abc import Sequence
import os
import pathlib
import subprocess
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--test_seq_path", required=True, help="Path to the test sequencer binary"
    )
    parser.add_argument(
        "--seq_path", required=True, help="Path to the sequence template file"
    )
    parser.add_argument(
        "--template_args",
        nargs="*",
        default=(),
        help="Space separated key value pairs to be filled in.",
    )
    parser.add_argument(
        "--template_path_args",
        nargs="*",
        default=(),
        help="Space separated key value pairs to be filled in. "
        "The value must be a relative path.",
    )
    return parser.parse_args()


def _create_template_dict(args: Sequence[str], is_path: bool) -> dict[str, str]:
    d = {}
    for i in range(0, len(args), 2):
        if i + 1 < len(args):
            d[args[i]] = (
                os.path.join(os.getcwd(), args[i + 1]) if is_path else args[i + 1]
            )
    return d


def _gen_sequence(template, args, path_args, out_path):
    kwargs = _create_template_dict(args, False)
    kwargs.update(_create_template_dict(path_args, True))
    out_path.write_text(template % kwargs)


def main():
    args = parse_args()

    sequence = pathlib.Path(os.environ["TEST_TMPDIR"], "sequence.txtpb")
    _gen_sequence(
        pathlib.Path(args.seq_path).read_text(),
        args.template_args,
        args.template_path_args,
        sequence,
    )

    results = pathlib.Path(os.environ["TEST_UNDECLARED_OUTPUTS_DIR"], "results")
    runtime = pathlib.Path(os.environ["TEST_TMPDIR"], "runtime")
    common = pathlib.Path(os.environ["TEST_TMPDIR"], "common")
    xdg_runtime = pathlib.Path(os.environ["TEST_TMPDIR"], "xdg_runtime")
    xdg_runtime.mkdir()
    home = pathlib.Path(os.environ["TEST_TMPDIR"], "home")
    home.mkdir()
    env = os.environ.copy()
    env["HOME"] = str(home)
    env["DISABLE_CLEARCUT"] = "1"
    env["XDG_RUNTIME_DIR"] = str(xdg_runtime)

    subprocess.run(
        args=[
            args.test_seq_path,
            "-name",
            results,
            "-runtime_dir",
            runtime,
            "-common_dir",
            common,
            sequence,
        ],
        check=True,
        env=env,
    )


if __name__ == "__main__":
    main()
