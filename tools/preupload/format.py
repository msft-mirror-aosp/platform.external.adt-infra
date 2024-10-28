import sys
import subprocess

import os
import subprocess
import sys
import tempfile
import os
from pathlib import Path

HERE = Path(os.path.dirname(__file__)).absolute()
ADT_INFRA = HERE.parents[1]


def run_black_in_temp_venv(python_files) -> subprocess.CompletedProcess:
    """
    Runs the Black code formatter in a temporary virtual environment.

    This function creates a temporary virtual environment, installs Black in it,
    and then runs Black on the provided Python files.

    Args:
        python_files: A list of Python files to format.

    Returns:
        A CompletedProcess object containing the output from Black.
    """
    with tempfile.TemporaryDirectory() as venv_dir:
        print("Black not found. Installing in a temporary virtual environment...")
        print("You can save time by installing black: `pip install --user black`")

        # Create a virtual environment in the temporary directory
        subprocess.run([sys.executable, "-m", "venv", venv_dir], check=True)

        # Activate the virtual environment
        env = os.environ.copy()
        env["PATH"] = f"{venv_dir}{os.sep}bin{os.pathsep}{env['PATH']}"
        env["VIRTUAL_ENV"] = venv_dir
        # Install black
        subprocess.run(
            [
                "pip",
                "install",
                "black",
                "--find-links",
                str(ADT_INFRA / "devpi" / "repo"),
            ],
            env=env,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Run black
        result = subprocess.run(
            ["black"] + python_files, capture_output=True, text=True, env=env
        )
        return result


def run_black(source_files):
    """
    Runs the black code formatter on the given Python source files.
    Installs black in a virtual environment if it's not already available.
    Exits with code 1 if any file was modified by black.
    Skips non-Python files.

    Args:
      source_files: A list of source files to format.
    """

    python_files = [f for f in source_files if f.endswith(".py")]

    if not python_files:
        print(f"No Python files found in {source_files}, ignoring.")
        sys.exit(0)

    try:
        # Try running black directly
        result = subprocess.run(
            ["black", *python_files], capture_output=True, text=True
        )
    except FileNotFoundError:
        result = run_black_in_temp_venv(python_files)

    # Check if any files were changed
    if result.returncode == 0 and "reformatted" in result.stderr:
        print("Black modified files, please update your commit.")
        sys.exit(1)
    elif result.returncode == 0:
        print("No files were modified.")
        sys.exit(0)
    else:
        print(f"Black failed to run:\n{result.stderr}")
        sys.exit(result.returncode)  # Exit with black's return code


if __name__ == "__main__":
    source_files = sys.argv[1:]  # Get source files from command line arguments
    if not source_files:
        print("Usage: python format.py <source_file1> <source_file2> ...")
        sys.exit(1)

    run_black(source_files)
