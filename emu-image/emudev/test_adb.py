#!/usr/bin/env python
#
# Copyright 2018 - The Android Open Source Project
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
import os
import unittest
from emudev.adb import Adb

class AdbTest(unittest.TestCase):

    def test_keygen(self):
        a = Adb()
        self.assertIsNotNone(a.pub)
        self.assertIsNotNone(a.priv)

    def test_Singleton(self):
        a = Adb()
        b = Adb()
        self.assertEqual(a.priv, b.priv)
        self.assertEqual(a.pub, b.pub)

    def test_adbdir(self):
        a = Adb()
        self.assertTrue(os.path.exists(a.keydir))
        self.assertTrue(os.path.exists(os.path.join(a.keydir, 'adbkey')))
        self.assertTrue(os.path.exists(os.path.join(a.keydir, 'adbkey.pub')))

    def test_getVersion(self):
        a = Adb()
        res = a.cmd(['version'], 1234)
        self.assertIsNotNone(res)
