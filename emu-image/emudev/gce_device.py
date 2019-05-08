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

import getpass
import subprocess
import time
from distutils.spawn import find_executable

# Absl-py
from absl import logging
from acloud.internal.lib import android_build_client, auth
from acloud.internal.lib.utils import AutoConnect
from acloud.public import device_driver
from acloud.public.actions import create_goldfish_action
# You will need to install the acloud module.
from acloud.public.config import AcloudConfigManager
from acloud.public.report import Status


class GCEDevice:
    """Represents a running GCE instance with the emulator deployed."""
    ADB_KEY = 'cvd_01_adb_key'
    ADB_KEY_PUB = 'cvd_01_adb_key_pub'
    ADB_PORT = 5555
    VNC_PORT = 6444
    GCE_INSTANCE_NAME = 'instance_name'
    GCE_INSTANCE_IP = 'ip'
    DEVICES = 'devices'
    FAILED = 'devices_failing_boot'
    SCP_ARGS = ("-i %(rsa_key_file)s -o UserKnownHostsFile=/dev/null "
                "-o StrictHostKeyChecking=no "
                "%(ssh_user)s@%(ip_addr)s:%(remote_file)s "
                "%(local_file)s")

    SSH_ARGS = ("-i %(rsa_key_file)s -o UserKnownHostsFile=/dev/null "
                "-o StrictHostKeyChecking=no "
                "%(ssh_user)s@%(ip_addr)s "
                "%(cmd)s")

    def __init__(self, config_file, image, build_id, adb, gpu=None):
        self.launch = None
        self.adb_port = None
        self.image = image
        self.build_id = build_id
        self.adb = adb
        self.gpu = gpu
        self._configure(config_file)
        self.status = False

    def _configure(self, config_file):
        """Configure the metadata for our gce instance."""
        self.cfg = AcloudConfigManager(config_file).Load()
        metadata = self.image.metadata()
        for k, v in metadata.iteritems():
            self.cfg.metadata_variable[k] = v

        # User knows best, but we likely want to run sdk_tools_linux...
        if not self.cfg.emulator_build_target:
            self.cfg.emulator_build_target = 'sdk_tools_linux'

    def __enter__(self):
        if not self.launch:
            self.start()
        return self

    def __exit__(self, type, value, tb):
        self.delete()

    def start(self):
        """Starts this image, returning the report upon completion."""
        # Note that we pass in a branch and target that needs to resolve, but
        # ultimately will not be used by gce.
        # ACloud uses these parameters to do some internal checks, this checks
        # are not relevant to us, but we must pass them.
        self.launch = create_goldfish_action.CreateDevices(
            cfg=self.cfg,
            emulator_build_id=self.build_id,
            num=1,
            branch=self.image.branch,
            build_id=self.image.build_id,
            build_target=self.image.build_target,
            gpu=self.gpu,
            report_internal_ip=False)
        self.launch.Dump(None)

        # Make sure our adb deamon has the new private key.
        if self.is_running():
            try:
                self._get_adb_keys()
            except:
                logging.exception('Failed to obtain adb private key %s')

        return self.launch

    def _exec(self, cmd):
        logging.info("Executing %s", cmd)
        return subprocess.check_call(cmd)

    def _get_adb_keys(self):
        """Copy the private adb key to the adb key directory.

           If all goes well, adb will pick up this key and will try
           to offer it during authentication.
        """
        scp_args = GCEDevice.SCP_ARGS % {
            'rsa_key_file':  self.cfg.ssh_private_key_path,
            'ssh_user': getpass.getuser(),
            'ip_addr': self.instance_ip(),
            'remote_file': '/tmp/adbkey',
            'local_file': '%s/%s.adbkey' % (self.adb.keydir, self.instance_name())
        }

        ssh_args = GCEDevice.SSH_ARGS % {
            'rsa_key_file':  self.cfg.ssh_private_key_path,
            'ssh_user': getpass.getuser(),
            'ip_addr': self.instance_ip(),
            'cmd': 'sudo cp /home/vsoc-01/.android/adbkey /tmp && sudo chmod 777 /tmp/adbkey',
        }

        ssh_del = GCEDevice.SSH_ARGS % {
            'rsa_key_file':  self.cfg.ssh_private_key_path,
            'ssh_user': getpass.getuser(),
            'ip_addr': self.instance_ip(),
            'cmd': 'sudo rm /tmp/adbkey',
        }

        # Get the adb key..
        self._exec([find_executable('ssh')] + ssh_args.split())
        self._exec([find_executable('scp')] + scp_args.split())
        self._exec([find_executable('ssh')] + ssh_del.split())

    def get_adb_port(self):
        """Establishes an ssh forwarding connection to the remote instance.

           It will set the local adb_port where we can reach the device.
        """
        if self.adb_port:
            return self.adb_port

        logging.info("Establishing ssh connection to %s", self.instance_ip())
        self.adb_port = AutoConnect(self.instance_ip(),
                                    self.cfg.ssh_private_key_path,
                                    GCEDevice.VNC_PORT,
                                    GCEDevice.ADB_PORT,
                                    getpass.getuser()).adb_port
        return self.adb_port

    def is_running(self):
        """True if the launch was successful."""
        return self.launch and self.launch.status == Status.SUCCESS

    def wait_until_booted(self, timeout=300):
        """Polls a running device until it has booted, or timed out."""
        if not self.is_running():
            logging.info("No need to wait, launch was not successful")
            return False

        start = time.time()
        self.status = self.boot_complete()
        while not status and time.time() - start < timeout:
            logging.info("Waiting for boot completion message.")
            time.sleep(1)
            self.status = self.boot_complete()

        logging.info("Finished waiting, booted: %s", status)
        return self

    def boot_complete(self):
        """Returns true if the sys.boot_completed property is set in the device."""
        return (self.is_running() and
                '1' in self.adb.cmd(['shell', 'getprop', 'sys.boot_completed'], self.get_adb_port()))

    def _get_property(self, prop):
        """Returns the given property from the launch report or None if not there."""
        if not self.launch:
            return None

        # 2 cases, success, and failure
        lookfor = GCEDevice.DEVICES
        if GCEDevice.FAILED in self.launch.data:
            lookfor = GCEDevice.FAILED
        return next(iter([device[prop] for device in self.launch.data[lookfor]]), None)

    def status(self):
        return self.status

    def instance_ip(self):
        """Gets the public ip address of the running gce instance."""
        return self._get_property(GCEDevice.GCE_INSTANCE_IP)

    def instance_name(self):
        """Gets the instance name of this device."""
        return self._get_property(GCEDevice.GCE_INSTANCE_NAME)

    def delete(self):
        """Deletes this instance."""
        return device_driver.DeleteAndroidVirtualDevices(self.cfg, [self.instance_name()])

    def __str__(self):
        return "%s - Running: %s, Booted: %s" % (self.image, self.is_running(), self.status)
