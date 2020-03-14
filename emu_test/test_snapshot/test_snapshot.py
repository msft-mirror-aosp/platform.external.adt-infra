"""Test the emulator snapshot grpc endpoints."""

import os
import shutil
import socket
import tempfile
import time
import traceback
import unittest
from contextlib import closing

import psutil

import emu_test.utils.emu_testcase
import emu_test.utils.path_utils as path_utils
from emu_test.test_snapshot.snapshot import SnapshotService
from emu_test.test_snapshot.waterfall_adb import WaterfallService
from emu_test.utils.emu_argparser import emu_args
from emu_test.utils.emu_error import *
from emu_test.utils.emu_testcase import AVDConfig, EmuBaseTestCase


class TemporaryDirectory(object):
    """Self deleting tempory directory."""

    def __enter__(self):
        self.location = tempfile.mkdtemp()
        return self.location

    def __exit__(self, exc_type, exc_value, traceback):
        shutil.rmtree(self.location)


def find_free_port():
    """Finds an avalaible free port."""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


class SnapshotTestCase(EmuBaseTestCase):
    def __init__(self, *args, **kwargs):
        super(SnapshotTestCase, self).__init__(*args, **kwargs)
        self.avd_config = None

    @classmethod
    def setUpClass(cls):
        super(SnapshotTestCase, cls).setUpClass()

    def kill_emulator(self):
        self.m_logger.debug("First try - quit emulator by adb emu kill")
        adb_binary = path_utils.get_adb_binary()
        kill_proc = psutil.Popen([adb_binary, "emu", "kill"]).communicate()
        # check emulator process is terminated
        result = self.term_check(timeout=5)
        if not result:
            self.m_logger.info("Second try - quit emulator by psutil")
            self.kill_proc_by_name(["emulator", "qemu-system"])
            result = self.term_check(timeout=10)
            self.m_logger.info("term_check after psutil.kill - %s" % result)
        try:
            self.m_logger.debug("kill adb and crash-service")
            if result and self.start_proc:
                self.start_proc.wait()
            time.sleep(1)
            self.kill_proc_by_name(["crash-service", "adb"])
        except Exception, e:
            self.m_logger.error("Error in cleanup - %r" % e)
            pass
        self.m_logger.debug("Killed emulator done")

    def tearDown(self):
        self.kill_emulator()
        self.m_logger.info("Remove AVD inside of tear down")
        avd_dir = os.environ['ANDROID_AVD_HOME']
        try:
            os.remove(os.path.join(avd_dir, "%s.ini" % self.avd_config.name()))
            shutil.rmtree(
                os.path.join(avd_dir, "%s.avd" % self.avd_config.name()),
                ignore_errors=True,
            )
        except Exception, e:
            self.m_logger.error("Error in cleanup - %r" % e)
            pass

    def waterfall_check(self, wfall):
        """Checks that waterfall is working as expected."""
        sout, _, exitcode = wfall.get_props()
        return exitcode == 0 and "sys.boot_completed" in sout


    def snapshot_check(self, avd):
        grpc_port = find_free_port()
        try:
            self.launch_emu_and_wait(avd, ["-grpc", str(grpc_port), "-waterfall", "adb"])
            self.m_logger.debug("Emulator is up and ready")
        except TimeoutError:
            self.m_logger.error("AVD %s, time out.." % str(avd))
            return

        try:
            self.m_logger.debug("Getting a snapshot")
            snapshot = SnapshotService(grpc_port, self.m_logger)
            wfall = WaterfallService(grpc_port, self.m_logger)
            self.assertTrue(self.waterfall_check(wfall))

            initial = snapshot.lists()

            # Local snapshot test create/list/load/delete/list
            self.assertTrue(snapshot.save("foo"))
            self.assertTrue("foo" in snapshot.lists())
            self.assertTrue(snapshot.load("foo"))

            # Waterfall will reconnect properly after snapshot restore
            self.assertTrue(self.waterfall_check(wfall))
            self.assertTrue(snapshot.delete("foo"))
            self.assertFalse("foo" in snapshot.lists())

            # Now do a pull and push test, validating we
            # can export and import snapshots.
            # create/pull/delete/push/load
            with TemporaryDirectory() as d:
                self.assertTrue(snapshot.save("foo"))
                self.assertTrue(snapshot.pull("foo", d))
                self.assertTrue(snapshot.delete("foo"))
                self.assertFalse("foo" in snapshot.lists())
                self.assertFalse(snapshot.load("foo"))

                # Waterfall over adb still functions after failed restore
                self.assertTrue(self.waterfall_check(wfall))
                self.assertTrue(snapshot.push(os.path.join(d, "foo.tar.gz")))
                self.assertTrue("foo" in snapshot.lists())
                self.assertTrue(snapshot.load("foo"))
                # Waterfall over adb still functions after successfull restore
                self.assertTrue(self.waterfall_check(wfall))
        except:
            self.m_logger.error("Fatal error in main test", exc_info=True)

    def run_snapshot_test(self, avd_config):
        self.avd_config = avd_config
        if self.create_avd(avd_config) == 0:
            self.snapshot_check(avd_config)


def create_test_case_for_avds():
    avd_list = emu_args.avd_list
    for avd in avd_list:

        def fn(i):
            return lambda self: self.snapshot_check(i)

        setattr(SnapshotTestCase, "test_snapshot_%s" % avd, fn(avd))


if emu_args.config_file is None:
    create_test_case_for_avds()
else:
    emu_test.utils.emu_testcase.create_test_case_from_file(
        "snapshot", SnapshotTestCase, SnapshotTestCase.run_snapshot_test
    )

if __name__ == "__main__":
    os.environ["SHELL"] = "/bin/bash"
    emu_argparser.emu_args = emu_argparser.get_parser().parse_args()
    print emu_argparser.emu_args
    sys.argv[1:] = emu_args.unittest_args
    unittest.main()
