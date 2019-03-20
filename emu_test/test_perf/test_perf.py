"""Generate perf data for emulator"""

import unittest
import os
import time
import psutil
import shutil
import traceback
import json

from emu_test.utils.emu_error import *
from emu_test.utils.emu_argparser import emu_args
import emu_test.utils.emu_testcase
from emu_test.utils.emu_testcase import EmuBaseTestCase, AVDConfig
import emu_test.utils.path_utils as path_utils

class PerfTestCase(EmuBaseTestCase):
    def __init__(self, *args, **kwargs):
        super(PerfTestCase, self).__init__(*args, **kwargs)
        self.avd_config = None
        self.perf_file = ""

    @classmethod
    def setUpClass(cls):
        super(PerfTestCase, cls).setUpClass()

    def kill_emulator(self):
        self.m_logger.debug('First try - quit emulator by adb emu kill')
        adb_binary = path_utils.get_adb_binary()
        kill_proc = psutil.Popen([adb_binary, "emu", "kill"]).communicate()
        # check emulator process is terminated
        result = self.term_check(timeout=5)
        if not result:
            self.m_logger.info('Second try - quit emulator by psutil')
            self.kill_proc_by_name(["emulator", "qemu-system"])
            result = self.term_check(timeout=10)
            self.m_logger.info("term_check after psutil.kill - %s" % result)
        return result

    def tearDown(self):
        result = self.kill_emulator()
        self.m_logger.info("Remove AVD inside of tear down")
        # avd should be found $HOME/.android/avd/
        avd_dir = os.path.join(os.path.expanduser('~'), '.android', 'avd')
        try:
            if result and self.start_proc:
                self.start_proc.wait()
            time.sleep(1)
            self.kill_proc_by_name(["crash-service", "adb"])
            os.remove(os.path.join(avd_dir, '%s.ini' % self.avd_config.name()))
            shutil.rmtree(os.path.join(avd_dir, '%s.avd' % self.avd_config.name()), ignore_errors=True)
        except Exception, e:
            self.m_logger.error("Error in cleanup - %r" % e)
            pass

    def launch_emulator(self, metric, avd):
        try:
            self.m_logger.info("PerfGate Metric: %s" % metric)
            self.perf_file = os.path.join(emu_args.session_dir,
                                          emu_args.test_dir,
                                          metric + ".log")
            boot_time, start_time = self.launch_emu_and_wait(avd)
            self.m_logger.info('AVD %s, boot time: %s' % (avd, boot_time))
        except TimeoutError:
            self.m_logger.error('AVD %s, time out, try one more time' % str(avd))
        except:
            self.m_logger.error('AVD %s, exception, try one more time' % str(avd))
            self.m_logger.error(traceback.format_exc())

    def generate_perf_data_idle(self, avd):
        metric = "New_AVD_" + avd.tag + "_" + avd.gpu + "_idle"
        self.launch_emulator(metric, avd)
        time.sleep(300)
        self.kill_emulator()
        metric = "Existing_AVD_" + avd.tag + "_" + avd.gpu + "_idle"
        self.launch_emulator(metric, avd)
        time.sleep(300)

    def run_perf_test(self, avd_config):
        self.avd_config = avd_config
        if self.create_avd(avd_config) == 0:
            self.generate_perf_data_idle(avd_config)


def create_test_case_for_avds():
    avd_list = emu_args.avd_list
    for avd in avd_list:
        def fn(i):
            return lambda self: self.generate_perf_data(i)
        setattr(PerfTestCase, "test_perf_%s" % avd, fn(avd))

if emu_args.config_file is None:
    create_test_case_for_avds()
else:
    emu_test.utils.emu_testcase.create_test_case_from_file("perf", PerfTestCase, PerfTestCase.run_perf_test)

if __name__ == '__main__':
    os.environ["SHELL"] = "/bin/bash"
    emu_argparser.emu_args = emu_argparser.get_parser().parse_args()
    print emu_argparser.emu_args
    sys.argv[1:] = emu_args.unittest_args
    unittest.main()
