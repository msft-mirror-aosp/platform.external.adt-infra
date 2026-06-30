"""Library to run a test sequencer sequence."""

import logging
import os
import pathlib
import subprocess
import sys

from sequence import gemini_analyzer


def run(test_seq_path: str, sequence: str, extra_path: list[str]):
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
    # Create a fake auth token for the emulator to use b/529880652.
    home.joinpath(".emulator_console_auth_token").write_text("supersecret")
    env = os.environ.copy()
    env["DISABLE_CLEARCUT"] = "1"
    env["HOME"] = str(home)
    env["XDG_RUNTIME_DIR"] = str(xdg_runtime)
    env["PATH"] = os.pathsep.join(extra_path + [env["PATH"]])
    # Macs have TMPDIR on a different filesystem, preventing tradefed from
    # hardlinking files. Redefine TMPDIR to a subdirectory of TEST_TMPDIR
    # to avoid this.
    if sys.platform.lower() == "darwin":
        darwin_tmp = tmp_dir.joinpath("tmp")
        darwin_tmp.mkdir()
        env["TMPDIR"] = str(darwin_tmp)
        env["JAVA_TOOL_OPTIONS"] = "-Djava.io.tmpdir=" + str(darwin_tmp)

    try:
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
    finally:
        try:
            gemini_analyzer.analyze_failures(str(results))
        except Exception as e:
            logging.error(f"Failed to run Gemini failure analysis: {e}")
