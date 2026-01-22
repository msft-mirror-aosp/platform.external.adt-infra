"""Library to run a test sequencer sequence."""

import os
import pathlib
import subprocess


def run(test_seq_path: str, sequence: str):
    tmp_dir = pathlib.Path(os.environ["TEST_TMPDIR"])
    sequence_path = tmp_dir.joinpath("sequence.txtpb")
    sequence_path.write_text(sequence)
    results = pathlib.Path(os.environ["TEST_UNDECLARED_OUTPUTS_DIR"], "results")
    results.mkdir(parents=True)
    runtime = tmp_dir.joinpath("runtime")
    common = tmp_dir.joinpath("common")
    xdg_runtime = tmp_dir.joinpath("xdg_runtime")
    xdg_runtime.mkdir()
    home = tmp_dir.joinpath("home")
    home.mkdir()
    env = os.environ.copy()
    env["DISABLE_CLEARCUT"] = "1"
    env["HOME"] = str(home)
    env["XDG_RUNTIME_DIR"] = str(xdg_runtime)

    subprocess.run(
        args=[
            test_seq_path,
            "-name",
            results,
            "-runtime_dir",
            runtime,
            "-common_dir",
            common,
            sequence_path,
        ],
        check=True,
        env=env,
    )
