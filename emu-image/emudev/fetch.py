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
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import multiprocessing
import os
import xml.etree.ElementTree as ET
import sys
import tempfile
from functools import partial
from operator import attrgetter

from absl import app
from absl import flags

import urlfetch

from emudev.adb import Adb
from emudev.android_image import AndroidSystemImage

REPOS = [
    'https://dl.google.com/android/repository/sys-img/android-tv/sys-img2-1.xml',
    'https://dl.google.com/android/repository/sys-img/android-wear/sys-img2-1.xml',
    'https://dl.google.com/android/repository/sys-img/android/sys-img2-1.xml',
    'https://dl.google.com/android/repository/sys-img/google_apis_playstore/sys-img2-1.xml'
]
FLAGS = flags.FLAGS
flags.DEFINE_boolean(
    'list_ranchu', False,
    'List the images and check if the image has kernel ranchu')
flags.DEFINE_string('img_dir', os.path.join(tempfile.gettempdir(), 'sys-images'),
                    'Directory to store downloaded images for kernel-ranchu check.'
                    'Remove this to download the images again')
flags.DEFINE_boolean('list', False, 'List all the images.')
flags.DEFINE_boolean('delete', True, 'Delete instance after booting.')
flags.DEFINE_string(
    'config',
    os.path.join(os.path.expanduser('~'), '.config',
                 'acloud', 'acloud.config'),
    'ACloud base configuration')
flags.DEFINE_string('build_id', '5048570',
                    'Emulator build used to launch the image')
flags.DEFINE_string('gpu', None,
                    'GPU to attach to the device or None. e.g. nvidia-tesla-k80')
flags.DEFINE_string(
    'boot', None, 'Matching string from list to boot image.'
    'For example: "21" will boot all 21 images. '
    '"28, android, x86_64" will boot a single image.')
flags.DEFINE_string('result_file', None,
                    'Print the resulting csv to this file')
flags.DEFINE_integer('concurrency', multiprocessing.cpu_count(),
                     'Max number of concurrent requests. '
                     'Lower this if you lack gce quota during boot testing')


def get_system_images():
    """Gets all the publicly available system images from the Android Image Repos.

         Returns a list of AndroidSystemImages that were found.
      """
    xml = []
    for url in REPOS:
        response = urlfetch.get(url)
        if response.status == 200:
            xml.append(response.content)
    xml = [ET.fromstring(x).findall('remotePackage') for x in xml]
    # Flatten the list of lists into a system image objects.
    return [AndroidSystemImage(item) for sublist in xml for item in sublist]


def _boot_image(adb, system_image):
    """Attempts to boot a single system image.

      The device will be torn down after boot completion.

      Returns: True if the device booted
      """
    if not FLAGS.delete:
        return system_image.launch_with_acloud(FLAGS.config,
                                               FLAGS.build_id,
                                               adb,
                                               FLAGS.gpu).wait_until_booted()

    with system_image.launch_with_acloud(FLAGS.config,
                                         FLAGS.build_id, adb) as device:
        return device.wait_until_booted()


def boot(system_images):
    """Boots the given list of images."""
    with Adb() as adb:
        boot_img = partial(_boot_image, adb)

        # Use number of available cores to spin up machines
        # Be careful, we have limited quota!
        pool = multiprocessing.Pool(processes=FLAGS.concurrency)
        return zip(system_images, pool.map(boot_img, system_images))


def _has_ranchu(system_image):
    return system_image.has_ranchu_multi(FLAGS.img_dir)

def has_ranchu_multi(system_images):
    """Checks to see if the given images have a ranchu kernel."""
    # Note, thread pool executor has some issues with urlfetch module.
    return zip(system_images, map(_has_ranchu, system_images))


def main(argv=None):
    del argv  # Unused.

    # setup output..
    output = sys.stdout
    if FLAGS.result_file:
        output = open(FLAGS.result_file, 'w')

    # Get all the images sorted by api level
    system_images = sorted(get_system_images(), key=attrgetter('api'))

    if FLAGS.list:
        output.write('%s\n' % AndroidSystemImage.header())
        output.write('\n'.join(map(str, system_images)))

    if FLAGS.list_ranchu:
        ranchu = has_ranchu_multi(system_images)
        output.write('%s, ranchu\n' % AndroidSystemImage.header())
        output.write('\n'.join(map(lambda x: '%s, %s' % x, ranchu)))

    if FLAGS.boot:
        launched = boot(
            [pkg for pkg in system_images if FLAGS.boot in str(pkg)])
        output.write('%s, can_boot\n' % AndroidSystemImage.header())
        output.write('\n'.join(map(lambda x: '%s, %s' % x, launched)))

    output.write('\n\nEmulator build: %s\n\n' % FLAGS.build_id)
    output.close()

    # Acloud spins up a lot of threads, so just exit with no error.
    sys.exit(0)


def launch():
    app.run(main)


if __name__ == '__main__':
    app.run(main)
