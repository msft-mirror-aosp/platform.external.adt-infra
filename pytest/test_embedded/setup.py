import subprocess
import sys
import platform
from os import path
from shutil import copyfile

from setuptools import setup
from setuptools.command.build_py import build_py
from setuptools.command.sdist import sdist



def compile_apk():
    # raise Exception("Failure")
    here = path.abspath(path.dirname(__file__))
    source = path.join(here, "AnimateBox")
    apk_dest = path.join(here, "src/emu/apk/app-debug.apk")
    bin = "./gradlew" if platform.platform() != "Windows" else "gradlew.bat"
    

    if not path.exists(bin) and path.exists(apk_dest):
        sys.stderr.write(f"Apk exists, and source app missing, good to go\n")
        return

    sys.stderr.write(f"Invoking gradle for: {source}\n")

    subprocess.check_call([bin, "assembleDebug"], cwd=source)
    apk_produced = path.join(
        here, "AnimateBox/app/build/outputs/apk/debug/app-debug.apk"
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