import os
import platform
import subprocess
import sys
from pathlib import Path
from shutil import copyfile

from setuptools import setup
from setuptools.command.build_py import build_py
from setuptools.command.sdist import sdist

EMU_TEST_DIR = Path(os.path.dirname(__file__)).absolute()
AOSP_ROOT = EMU_TEST_DIR.parents[3]
GRADLE_DIR = EMU_TEST_DIR / "AnimateBox"


def compile_apk(source_dir, dest_apk, gradle_target):
    if dest_apk.exists():
        sys.stderr.write(
            f">>>>>--- {dest_apk} exists, no need to build. "
            f"Remove {dest_apk} if you wish to rebuild it.\n"
        )
        return

    bin_path = (
        GRADLE_DIR / "gradlew"
        if platform.system() != "Windows"
        else GRADLE_DIR / "gradlew.bat"
    )

    if not bin_path.exists():
        raise Exception(f"The gradle script {bin_path} is not present")

    sys.stderr.write(f"Invoking {bin_path} for: {source_dir}\n")
    subprocess.check_call(
        [str(bin_path), "-b", str(source_dir / "build.gradle"), gradle_target],
        cwd=source_dir,
    )

    for apk_produced in source_dir.glob(f"**/{dest_apk.name}"):
        sys.stderr.write(f"   copyfile({apk_produced}, {dest_apk})\n")
        copyfile(apk_produced, dest_apk)


def gradle():
    compile_apk(
        AOSP_ROOT / "external" / "mobly-bundled-snippets",
        EMU_TEST_DIR / "src" / "emu" / "apk" / "mobly-bundled-snippets-debug.apk",
        "assembleDebug",
    )
    compile_apk(
        EMU_TEST_DIR / "AnimateBox",
        EMU_TEST_DIR / "src" / "emu" / "apk" / "app-release.apk",
        "build",
    )


class ApkSource(sdist):
    """This command automatically compiles the apk and copies it over."""

    def run(self):
        gradle()
        super().run()


class ApkBuild(build_py):
    """This command automatically compiles the apk and copies it over."""

    def run(self):
        gradle()
        super().run()


if __name__ == "__main__":
    local_path: str = (Path(__file__).parent).absolute()
    try:
        setup(
            dependency_links=[str(local_path)],
            cmdclass={"build_py": ApkBuild, "sdist": ApkSource},
        )
    except Exception as e:
        print(
            "\n\nAn error occurred while building the project, "
            "please ensure you have the most updated version of setuptools, "
            "setuptools_scm and wheel with:\n"
            "   pip install -U setuptools setuptools_scm wheel\n\n"
        )
        raise e
