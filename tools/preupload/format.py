import sys
import subprocess

import os


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
        print("Black not found. Installing in a virtual environment...")
        print("You can save time by installing black: `pip install black`")
        # Create a virtual environment
        subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True)

        # Activate the virtual environment
        if sys.platform == "win32":
            activate_script = ".venv\\Scripts\\activate"
        else:
            activate_script = ".venv/bin/activate"
        subprocess.run([activate_script], shell=True, check=True)

        # Install black
        subprocess.run(["pip", "install", "black"], check=True)

        # Run black
        result = subprocess.run(
            ["black", *python_files], capture_output=True, text=True
        )

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
