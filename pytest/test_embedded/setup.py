import subprocess
import sys
import platform
from pathlib import Path
from shutil import copyfile

from setuptools import setup
from setuptools.command.build_py import build_py
from setuptools.command.sdist import sdist


def compile_apk():
    # raise Exception("Failure")
    here = Path(__file__).parent.absolute()
    source = here / "AnimateBox"
    apk_dest = here / "src" / "emu" / "apk" / "app-release.apk"

    if apk_dest.exists():
            sys.stderr.write(f">>>>>--- {apk_dest} exists, no need to build. "
                             f"Remove {apk_dest} if you wish to rebuild it.\n")
            return

    bin = (
        source / "gradlew" if platform.system() != "Windows" else source / "gradlew.bat"
    )

    if not bin.exists():
        raise Exception(f"The gradle script {bin} is not present")

    if apk_dest.exists():
        sys.stderr.write(f"Apk exists, not rebuilding.\n")
        return

    sys.stderr.write(f"Invoking {bin} for: {source}\n")

    subprocess.check_call([str(bin), "build"], cwd=source)
    apk_produced = (
        here
        / "AnimateBox"
        / "app"
        / "build"
        / "outputs"
        / "apk"
        / "release"
        / "app-release.apk"
    )

    sys.stderr.write(f"   copyfile({apk_produced}, {apk_dest})\n")
    copyfile(
        apk_produced,
        apk_dest,
    )


class ApkSource(sdist):
    """This command automatically compiles the apk and copies it over."""

    def run(self):
        compile_apk()
        super().run()


class ApkBuild(build_py):
    """This command automatically compiles the apk and copies it over."""

    def run(self):
        compile_apk()
        super().run()


if __name__ == "__main__":
    try:
        setup(
            # use_scm_version={"version_scheme": "no-guess-dev", "root": "../../../"},
            cmdclass={"build_py": ApkBuild, "sdist": ApkSource},
        )
    except:  # noqa
        print(
            "\n\nAn error occurred while building the project, "
            "please ensure you have the most updated version of setuptools, "
            "setuptools_scm and wheel with:\n"
            "   pip install -U setuptools setuptools_scm wheel\n\n"
        )
        raise
