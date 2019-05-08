#!/usr/bin/env python
#
# Copyright 2019 - The Android Open Source Project
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

import getpass
import datetime
import json
import os
import re
import shutil
import tempfile
import zipfile
from distutils.spawn import find_executable

import docker
from absl import logging
from acloud.internal.lib import android_build_client, auth
from acloud.public.config import AcloudConfigManager
from jinja2 import Environment, PackageLoader, FileSystemLoader


class DockerDevice:
    """Creates a docker image with the desired emulator build & image.."""

    # The docker
    DOCKER_REPO = "gcr.io/emu-dev-cts"

    def __init__(self, config_file, image, build_id):
        self._configure(config_file)
        self.build_id = build_id
        self.image = image
        self.zip = 'sdk-repo-linux-emulator-{}.zip'.format(build_id)
        self.env = Environment(loader=FileSystemLoader('templates'))
        self.docker_image = None

    def _configure(self, config_file):
        """Configure the metadata for our gce instance."""
        cfg = AcloudConfigManager(config_file).Load()
        credentials = auth.CreateCredentials(cfg)
        self.ab = android_build_client.AndroidBuildClient(credentials)

    def download(self, fname):
        """Downloads the android emulator from go/ab to the given file."""
        self.ab.DownloadArtifact(
            'sdk_tools_linux', self.build_id, self.zip, fname)

    def _unzip(self, zipfilename, directory):
        logging.info('Extracting %s to: %s', zipfilename, directory)
        with zipfile.ZipFile(zipfilename) as zf:
            for info in zf.infolist():
                extracted_filename = zf.extract(info, directory)
                # Permission info in external_attr is shifted 16 bits.
                os.chmod(extracted_filename, info.external_attr >> 16)

    def _create_container(self, tag, src_dir):
        logging.info(
            'Creating docker image: %s.. be patient this takes a while! (>2mins)',
            tag)
        api_client = docker.APIClient(base_url='unix://var/run/docker.sock')
        logging.info(api_client.version())
        result = api_client.build(path=src_dir, tag=tag)

        for entry in result:
            msg = json.loads(entry)
            if 'stream' in msg:
                logging.info('IMG| %s', msg['stream'].strip())
            else:
                logging.info('IMG| %s', msg)

        client = docker.from_env()
        docker_image = client.images.get(tag)

        return docker_image

    def _create_docker_file_from_template(self, tag, src_dir):

        date = datetime.datetime.utcnow().isoformat('T') + 'Z'
        logging.info('Generating docker template: %s', tag)
        template = self.env.get_template('Dockerfile')
        dockerfile = os.path.join(src_dir, 'Dockerfile')
        with open(dockerfile, 'w') as dfile:
            dfile.write(
                template.render(
                    user='{}@google.com'.format(getpass.getuser()),
                    tag=self.image.tag,
                    api=self.image.api,
                    abi=self.image.abi,
                    url=self.image.url,
                    emu_build_id=self.build_id,
                    date=date))

    def create(self):
        if self.image.abi != 'x86_64':
            # TODO(jansene): Templatize config.ini so we can do both ABI's
            logging.error('Only x86_64 abi is currently supported.')
            return self

        logging.info('Creating container for: %s', self.image)
        tag = '{}/emulator/{}-{}-{}:{}'.format(DockerDevice.DOCKER_REPO,
                                               self.image.tag, self.image.api,
                                               self.image.abi, self.build_id)

        template_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), '..', 'templates')
        avd_dir = os.path.join(template_dir, 'avd')

        tmpdir = tempfile.mkdtemp('docker')
        _, tmpfile = tempfile.mkstemp()

        try:
            # Create a temp directory which will contain the docker image
            dist = os.path.join(tmpdir, 'distribution')
            platform = os.path.join(tmpdir, 'platform-tools')

            os.makedirs(dist)
            os.makedirs(platform)

            # Generate the docker file from the template
            self._create_docker_file_from_template(tag, tmpdir)

            # copy over adb from local machine
            shutil.copy2(find_executable('adb'), platform)

            # Copy Pixel2 avd to the right place
            shutil.copytree(avd_dir, os.path.join(tmpdir, 'avd'))

            # Get the emulator and unzip it to our docker dir
            self.download(tmpfile)
            self._unzip(tmpfile, dist)

            # Copy over the launcher script & pulse audio config
            shutil.copy2(
                os.path.join(template_dir, 'launch-emulator.sh'),
                os.path.join(tmpdir, 'distribution'))
            shutil.copy2(
                os.path.join(template_dir, 'default.pa'), tmpdir)

            # run docker
            self.docker_image = self._create_container(tag, tmpdir)

            logging.info('Launch the image by executing the line below:')
            logging.info(
                'docker run -e "ADBKEY=$(cat ~/.android/adbkey)" --privileged  --publish 5556:5556/tcp --publish 5554:5554/tcp %s',
                tag)
            logging.info('Push the image to the %s repo',
                         DockerDevice.DOCKER_REPO)
            logging.info('docker push %s', tag)

        finally:
            # clean up temporary files.
            shutil.rmtree(tmpdir)
            os.remove(tmpfile)

        return self

    def status(self):
        return self.docker_image.tags

    def __str__(self):
        return 'docker tag: {}'.format(self.docker_image.tags)
