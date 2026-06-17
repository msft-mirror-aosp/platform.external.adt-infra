"""Tests for the android-ets.zip file.

Tests that all the modules in the android-ets.zip file are explicitly included
or excluded in the presubmit xml files.
"""

import io
import os
import sys
import unittest
from xml.etree import ElementTree
import zipfile

from python.runfiles import Runfiles

_ETS_ZIP_PATH = ""
# Modules that are allowed to not be present.
_ALLOW_LIST = frozenset([
    "CloseEmulatorTest",  # This is run in a separate tradefed invocation.
    "CtsVerifierTest",  # This is run as a separate bazel target.
])


class EtsModulesTest(unittest.TestCase):
    def test_ets_modules(self):
        with zipfile.ZipFile(_ETS_ZIP_PATH, "r") as ets_zip:
            ets_modules = _get_ets_modules(ets_zip)
            self.assertNotEqual(0, len(ets_modules))
            ets_jar = ets_zip.read("android-ets/tools/e2e_tests_post_deploy.jar")
            next_modules, now_modules = _get_next_and_now_modules(ets_jar)
        ets_modules = ets_modules - _ALLOW_LIST
        self.assertCountEqual(ets_modules, next_modules,
                              "Modules are missing from the presubmit.xml file")
        self.assertCountEqual(
            ets_modules, now_modules,
            "Modules are missing from the emu_now_presubmit.xml file")


def _get_next_and_now_modules(ets_jar: bytes) -> tuple[list[str], list[str]]:
    raw = io.BytesIO(ets_jar)
    with zipfile.ZipFile(raw, "r") as jar_zip:
        next_modules = _modules_from_xml(jar_zip.read("config/presubmit.xml"))
        now_modules = _modules_from_xml(jar_zip.read("config/emu_now_presubmit.xml"))
    return next_modules, now_modules


def _modules_from_xml(xml: bytes) -> list[str]:
    ret = set()
    root = ElementTree.fromstring(xml.decode("utf-8"))
    for e in root:
        if e.tag == "option":
          ret.add(e.get("value").split()[0])
    return ret


def _get_ets_modules(ets_zip: zipfile.ZipFile) -> list[str]:
    ret = set()
    for name in ets_zip.namelist():
        if name.endswith(".config"):
            ret.add(os.path.basename(name)[:-7])
    return ret

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise ValueError("Usage: ets_modules_test <ets_zip_path>")
    _ETS_ZIP_PATH = Runfiles.Create().Rlocation(sys.argv[1])
    sys.argv = sys.argv[:1]
    unittest.main()
