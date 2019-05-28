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
import tempfile
import zipfile

import urlfetch
from absl import logging
from emudev.gce_device import GCEDevice
from emudev.docker_device import DockerDevice
from acloud.internal.lib import android_build_client, auth
from acloud.public.config import AcloudConfigManager
from emudev.gce_device import GCEDevice


class AndroidSystemImage(object):
    """An android system image, that can be launched in the emulator."""

    IMAGE_URL = 'cvd_01_fetch_image_url'

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

        # The properties below are "fake" and needed to make sure acloud
        # has the necessary data to proceed.
        self.branch='git_pi-dev'  # Unused, points to an existing branch
        self.build_id=5136849     # Unused, points to an existing build
        self.build_target='sdk_gphone_x86_64-userdebug'  # Unused.

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

    def create_docker_container(self, config_file, build_id):
        """Launches a GCE instance using the image with the given build_id"""
        device = DockerDevice(config_file, self, build_id)
        device.create()
        return device

    def launch_with_acloud(self, config_file, build_id, adb, gpu=None):
        """Creates a docker image using the image with the given build_id"""
        device = GCEDevice(config_file, self, build_id, adb, gpu)
        device.start()
        return device

    def metadata(self):
        """Gets the metadata items that need to be set on gce image."""
        # This meta data item will be used by our GCE instance to infer
        # which emulator we should launch, the url should point to:
        # - An existing, publicly accessible url
        # - Must be a zip file
        # - Must be a valid system image,
        return {AndroidSystemImage.IMAGE_URL: self.url}

    @staticmethod
    def header():
        """Returns a CSV header."""
        return "api, tag, abi, zip, url"

    def __str__(self):
        return "%s, %s, %s, %s, %s" % (self.api, self.tag, self.abi, self.zip, self.url)


class InternalAndroidImage(AndroidSystemImage):

    BUILD_TARGET = 'cvd_01_fetch_android_build_target'
    BUILD_ID = 'cvd_01_fetch_android_bid'

    def __init__(self, config_file,  build_id, target='sdk_gphone_x86_64-user'):
        """Initializes and android system image from a build id."""
        cfg = AcloudConfigManager(config_file).Load()
        credentials = auth.CreateCredentials(cfg)
        self.ab = android_build_client.AndroidBuildClient(credentials)
        self.branch = self.ab.GetBranch(target, build_id)
        self.build_target = target
        self.build_id = build_id
        self.zip = "{}-img-{}.zip".format(self.build_target.split('-')
                                          [0], self.build_id)
        self.url = 'http://go/ab/{}'.format(build_id)
        self.tag = 'android'
        self.api = 'unknown'
        self.abi = 'unknown'
        try:
            self._extract_properties()
        except:
            logging.error("Unable to extract build properties (api/abi). You might be using an older build.")


    def _extract_properties(self):
        """Extract the properties of the build from build.prop.

           Note: this can fail on older deserts. (Lollipop for example.)
        """
        _, prop_file = tempfile.mkstemp()
        self.ab.DownloadArtifact(self.build_target,
                                 self.build_id,
                                 'build.prop',
                                 prop_file)
        with open(prop_file, 'r') as props:
            properties = dict([x.strip().split('=')
                               for x in props.readlines() if '=' in x])

        self.api = properties['ro.build.version.sdk']
        self.abi = properties['ro.product.cpu.abilist'].split(',')[0]
        os.remove(prop_file)

    def download(self, fname):
        """Downloads the  image from go/ab to the given file."""
        self.ab.DownloadArtifact(self.build_target,
                                 self.build_id,
                                 self.zip,
                                 fname)

    def metadata(self):
        return {}
