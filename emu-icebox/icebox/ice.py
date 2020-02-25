#!/usr/bin/env python
#
# Copyright 2020 - The Android Open Source Project
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
from __future__ import absolute_import, division, print_function

import os
import sys
import zlib


# Super hack for protobuf not setting paths properly..
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "proto"))
)

from absl import app, flags, logging

import icebox.process as process
from icebox.adb import Adb
from icebox.icebox_device import IceboxImage
from icebox.snapshot import SnapshotService


FLAGS = flags.FLAGS

flags.DEFINE_string(
    "config",
    os.path.join(os.path.expanduser("~"), ".config", "acloud", "acloud.config"),
    "ACloud base configuration",
)
flags.DEFINE_string("bucket", "emu-dev-icebox", "Bucket to store snapshots.")
flags.DEFINE_string("gradle", None, "Directory with the gradle project")

flags.DEFINE_string("restore", None, "Directory with the gradle project")
flags.DEFINE_integer("port", 5559, "Adb forward port")
flags.DEFINE_string("grpc", "localhost:8556", "gRPC port")
flags.DEFINE_string("base", "icebox-demo-0", "The acloud base image used as a launcher.")

TEST_FAIL = "test_failure_snapshot"


def main(argv=None):
    del argv  # Unused.

    if FLAGS.gradle:
        run_gradle(FLAGS.grpc, FLAGS.bucket, FLAGS.gradle)
    if FLAGS.restore:
        restore(FLAGS.restore, FLAGS.config)


def restore(gradle, config):
    adb = Adb()
    test_name = zlib.crc32(gradle.encode("utf-8"))

    img = IceboxImage(FLAGS.base)
    device = img.launch_with_acloud(config, adb)
    logging.info("Waiting for device to become available..")
    device.available()
    url = device.get_grpc_url()

    logging.info("Connecting to %s", url)
    snapshotService = SnapshotService(url)
    snapshotService.push(os.path.join("/tmp", TEST_FAIL + ".tar"))
    snapshotService.load(TEST_FAIL)
    logging.info("You should now be able to connect to the device..")


def run_gradle(grpc, bucket, gradle):
    test_name = zlib.crc32(gradle.encode("utf-8"))

    # First we delete all snapshots
    snapshotService = SnapshotService(grpc)

    snaps = snapshotService.lists()
    for snap in snaps:
        snapshotService.delete(snap)

    process.run(["adb", "kill-server"])
    process.run(["adb", "wait-for-device"])
    # First run gradle..
    try:
        process.run(
            [
                "./gradlew",
                "-i",
                "connectedAndroidTest",
                "-Pandroid.enableTestIcebox=true",
            ],
            gradle,
        )
    except:
        logging.info("Errors are normal, as our tests fail.. ", exc_info=True)

    # storage_client = storage.Client()
    # bucket = storage_client.bucket(FLAGS.bucket)
    logging.info("Processing snapshots..")
    snaps = snapshotService.lists()
    for snap in snaps:
        # Pull it down.
        logging.info("Pulling down %s, slow!", snap)
        res, fname = snapshotService.pull(snap, "/tmp/")

        remote = "{}-{}".format(snap, test_name)
        logging.info("Pushing %s to cloud as %s.", fname, remote)

        # Push it to gcloud
        # blob = bucket.blob(remote)
        # blob.upload_from_filename(fname)
        process.run(["gsutil", "cp", fname, "gs://{}/{}".format(bucket, remote)])


def cli():
    app.run(main)


if __name__ == "__main__":
    app.run(main)

