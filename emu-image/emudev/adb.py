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
import subprocess
import os
import shutil
import tempfile
from distutils.spawn import find_executable

class Singleton(type):
    """Ye olde singleton."""
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(
                Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Adb:
    """Singleton that takes care of adb and key generation.

    Note: This will kill your currently running adb server and reinstantiate it
    with its own set of keys that will be generated when this class is instantiated
    for the first time.
    """
    __metaclass__ = Singleton

    def __init__(self):
        self.bin_path = find_executable('adb')
        self.keydir = tempfile.mkdtemp('adbkeys')
        self.gen_keys()

    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        self.release()

    def release(self):
        if os.path.exists(self.keydir):
            shutil.rmtree(self.keydir)

    def gen_keys(self):
        """Generate the pub/private keys to be used."""
        subprocess.check_call([self.bin_path, 'kill-server'])
        subprocess.check_call(
            [self.bin_path, 'keygen', os.path.join(self.keydir, 'adbkey')])
        self.priv = open(os.path.join(self.keydir, 'adbkey'), 'r').read()

    def cmd(self, cmd, adb_port):
        """Executes the given adb cmd on this devices. (Note, cmd should be an array)"""
        env = {'ADB_VENDOR_KEYS': '%s/adbkey' % self.keydir}
        proc = subprocess.Popen([self.bin_path, '-s', '127.0.0.1:%s' % adb_port] + cmd,
                                stdout=subprocess.PIPE,
                                shell=True,
                                env=env)
        outs, _ = proc.communicate()
        proc.wait()
        return outs
