"""Tool to generate and run a test sequence.

The sequence can have %(key)s string template parameters which will be filled
from the --template_args values. That flag is a space separated list, with three
values for each entry:
  - key: Template key to replace.
  - kind:
    - str: filled directly into the template.
    - path: relative path that will be made absolute before filling.
    - dir: same as path, but the parent directory will be used instead.
    - symdir: same as dir, but a temp symlink will be created and used instead
      to result in a shorter path.
  - value: Value to use.

Usage:
    ./run_sequence.py --test_seq_path <test_seq path> --seq_path <seq path> \
       [--template_args <key> <kind> <value> ...]
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
        help="Space separated key kind value groups to be filled in.",
    )
    return parser.parse_args()


def _create_template_dict(args: Sequence[str], tmp_dir: pathlib.Path) -> dict[str, str]:
    d = {}
    for i in range(0, len(args), 3):
        if i + 2 < len(args):
            val = args[i + 2]
            if args[i + 1] == "path":
                val = os.path.join(os.getcwd(), val)
            elif args[i + 1] == "dir":
                val = os.path.dirname(os.path.join(os.getcwd(), val))
            elif args[i + 1] == "symdir":
                p = tmp_dir.joinpath(os.path.basename(val))
                p.symlink_to(os.path.dirname(os.path.join(os.getcwd(), val)))
                val = str(p)
            d[args[i]] = val
    return d


def main():
    args = parse_args()

    tmp_dir = pathlib.Path(os.environ["TEST_TMPDIR"])
    sequence = tmp_dir.joinpath("sequence.txtpb")
    sym_dir = tmp_dir.joinpath("s")
    sym_dir.mkdir()
    kwargs = _create_template_dict(args.template_args, sym_dir)
    sequence.write_text(pathlib.Path(args.seq_path).read_text() % kwargs)

    results = pathlib.Path(os.environ["TEST_UNDECLARED_OUTPUTS_DIR"], "results")
    results.mkdir(parents=True)
    runtime = tmp_dir.joinpath("runtime")
    common = tmp_dir.joinpath("common")
    xdg_runtime = tmp_dir.joinpath("xdg_runtime")
    xdg_runtime.mkdir()
    home = tmp_dir.joinpath("home")
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
