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
import os
import zipfile


import urlfetch
from absl import logging
from emudev.gce_device import GCEDevice


class AndroidSystemImage(object):
    """An android system image, that can be launched in the emulator."""

    def __init__(self, pkg):
        """Initializes and android system image from an XML snippet."""
        details = pkg.find('type-details')
        self.api = details.find('api-level').text
        self.tag = details.find('tag').find('id').text
        if self.tag == 'default':
            self.tag = 'android'
        self.abi = details.find('abi').text
        self.zip = pkg.find('.//url').text
        self.url = 'https://dl.google.com/android/repository/sys-img/%s/%s' % (
            self.tag, self.zip)

    def download(self, fname):
        """Downloads the current image to the given file name/file object."""
        if hasattr(fname, 'write'):
            self.__download(fname)
        else:
            with open(fname, 'wb') as fileobj:
                self.__download(fileobj)

    def __download(self, fileobj):
        logging.info('Fetching %s', self.url)
        response = urlfetch.get(self.url)
        if response.status == 200:
            for chunk in response:
                fileobj.write(chunk)
        else:
            raise IOError('Unable to fetch %s, status: %s' %
                          (self.url, response.status))

    def has_ranchu_multi(self, dest_dir):
        """Checks to see if the zip contains kernel ranchu.

        Note: This is very expensive as it requires downloading the image."""
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
        fname = os.path.join(dest_dir, '%s-%s' % (self.tag, self.zip))
        logging.info('Checking %s for ranchu kernel', fname)
        if not os.path.exists(fname):
            self.download(fname)
        with zipfile.ZipFile(fname, 'r') as zipf:
            return any(['ranchu' in z for z in zipf.namelist()])

    def launch_with_acloud(self, config_file, build_id, adb):
        """Launches a GCE instance using the image with the given build_id"""
        device = GCEDevice(config_file, self, build_id, adb)
        device.start()
        return device

    @staticmethod
    def header():
        """Returns a CSV header."""
        return "api, tag, abi, zip, url"

    def __str__(self):
        return "%s, %s, %s, %s, %s" % (self.api, self.tag, self.abi, self.zip, self.url)
