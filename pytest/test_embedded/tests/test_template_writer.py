# Copyright 2020 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Lint as: python3
"""Unit tests for the template writer

"""

import os
import shutil
import tempfile
import unittest
import pytest

from emu.template_writer import TemplateWriter

pytestmark = pytest.mark.std


class TemplateTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp("unittest")
        self.writer = TemplateWriter(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_writer_writes_file(self):
        self.writer.write_template("Pixel2.ini", {})
        self.assertTrue(os.path.exists(os.path.join(self.tmpdir, "Pixel2.ini")))

    def test_renames_file(self):
        self.writer.write_template("Pixel2.ini", {}, "foo")
        self.assertTrue(os.path.exists(os.path.join(self.tmpdir, "foo")))

    def test_makes_dict(self):
        dict = self.writer.template_to_dict(
            "Pixel2.ini", {"avd_home": "foo", "name": "bar"}
        )
        assert dict["path"] == "foo/bar.avd"


if __name__ == "__main__":
    unittest.main()
