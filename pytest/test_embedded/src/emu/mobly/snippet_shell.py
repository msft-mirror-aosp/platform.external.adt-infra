#!/usr/bin/env python3.4
#
# Copyright 2016 Google Inc.
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

from mobly.controllers import android_device
from mobly.controllers.android_device_lib import jsonrpc_shell_base


class Error(Exception):
    pass


class SnippetShell(jsonrpc_shell_base.JsonRpcShellBase):
    def __init__(self, package=android_device.MBS_PACKAGE):
        self._package = package

    def load_device(self, serial=None):
        """Creates an AndroidDevice for the given serial number.

        If no serial is given, it will read from the ANDROID_SERIAL
        environmental variable. If the environmental variable is not set, then
        it will read from 'adb devices' if there is only one.
        """
        serials = android_device.list_adb_devices()
        if not serials:
            raise Error("No adb device found!")
        # No serial provided, try to pick up the device automatically.
        if not serial:
            env_serial = os.environ.get("ANDROID_SERIAL", None)
            if env_serial is not None:
                serial = env_serial
            elif len(serials) == 1:
                serial = serials[0]
            else:
                raise Error(
                    "Expected one phone, but %d found. Use the -s flag or "
                    "specify ANDROID_SERIAL." % len(serials)
                )
        if serial not in serials:
            raise Error('Device "%s" is not found by adb.' % serial)
        ads = android_device.get_instances([serial])
        assert len(ads) == 1
        self._ad = ads[0]
