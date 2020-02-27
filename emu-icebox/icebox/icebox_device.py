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
# limitations under the License.import tempfile
from icebox.gce_device import GCEDevice


class IceboxImage(object):
    """An icebox image."""

    IMAGE_URL = "cvd_01_emulator_image"
    ICEBOX_IMG = "icebox-demo-0"
    DEFAULT_IMG = "q-google-x64:29.3.6"

    def __init__(self, icebox=ICEBOX_IMG, image=DEFAULT_IMG):
        """Initializes ."""
        self.api = 29
        self.tag = "google_api"

        # The properties below are "fake" and needed to make sure acloud
        # has the necessary data to proceed.
        self.branch = "git_pi-dev"  # Unused, points to an existing branch
        self.build_id = 5136849  # Unused, points to an existing build
        self.fake_emu_build = 6141708
        self.build_target = "sdk_gphone_x86_64-userdebug"  # Unused.
        self.image = image
        self.icebox = icebox

    def launch_with_acloud(self, config_file, adb, gpu=None):
        """Creates a docker image using the image with the given build_id"""
        device = GCEDevice(config_file, self, self.fake_emu_build, adb,
                           self.icebox, gpu)
        device.start()
        return device

    def metadata(self):
        """Gets the metadata items that need to be set on gce image.

           We are using pre-fab docker image so we don't care.
        """
        return {IceboxImage.IMAGE_URL: self.image}
