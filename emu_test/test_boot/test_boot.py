"""Test the emulator boot time"""

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

class BootTestCase(EmuBaseTestCase):
    def __init__(self, *args, **kwargs):
        super(BootTestCase, self).__init__(*args, **kwargs)
        self.avd_config = None
    @classmethod
    def setUpClass(cls):
        super(BootTestCase, cls).setUpClass()

    def create_benchmark(self, name, value, timestamp):
      mean = {"type":"Mean",
              "constTerm":"10.0",
              "meanCoeff":"0.1",
              "stddevCoeff":"1.0"}

      median = {"type":"Median",
                "constTerm":"10.0",
                "medianCoeff":"0.1",
                "madCoeff":"1.0"}

      toleranceParams = [mean,
                         median]

      analyzers = [{"type":"WindowDeviationAnalyzer",
                    "metricAggregate":"MEDIAN",
                    "runInfoQueryLimit":"50",
                    "recentWindowSize":"25",
                    "toleranceParams":toleranceParams}]

      data = {timestamp: value}

      benchmark = {"benchmark": name,
                   "project": "Android Studio Emulator",
                   "data": data,
                   "analyzers": analyzers}

      return benchmark

    def write_perf_data(self,
                        boot_time1, timestamp1,
                        boot_time2, timestamp2):
        api = self.avd_config.api
        jsonDir = os.path.join(emu_args.session_dir,
                               emu_args.test_dir,
                               "test.outputs")
        if not os.path.exists(jsonDir):
            os.makedirs(jsonDir)
        filename = os.path.join(jsonDir,
                                "BootTest" + api + ".json")
        jsonFile = open(filename, "a")
        if "Linux" in emu_args.builder_name:
            platform = "linux"
        elif "Windows" in emu_args.builder_name:
            platform = "windows"
        else:
            platform = "mac"

        benchmarks = [self.create_benchmark("boot_time1", boot_time1, timestamp1),
                      self.create_benchmark("boot_time2", boot_time2, timestamp2)]
        json_data = {"metric": "BOOT_TIME",
                     "benchmarks": benchmarks}

        jsonFile.write(json.dumps(json_data, indent=2))
        jsonFile.close()

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

    def boot_check(self, avd):
        real_expected_boot_time = emu_args.expected_boot_time
        if 'swiftshader' in str(avd):
            real_expected_boot_time = real_expected_boot_time + emu_args.expected_boot_time
        if 'arm' in str(avd):
            real_expected_boot_time = real_expected_boot_time + emu_args.expected_boot_time
        if 'mips' in str(avd):
            real_expected_boot_time = real_expected_boot_time + emu_args.expected_boot_time
        try:
            boot_time1, start_time1 = self.launch_emu_and_wait(avd)
            self.m_logger.info('AVD %s, boot time: %s, expected time: %s'
                               % (avd, boot_time1, real_expected_boot_time))
            self.assertLessEqual(boot_time1, real_expected_boot_time)
        except TimeoutError:
            self.m_logger.error('AVD %s, time out, try one more time' % str(avd))
        except:
            self.m_logger.error('AVD %s, exception, try one more time' % str(avd))
            self.m_logger.error(traceback.format_exc())
        self.kill_emulator()
        boot_time2, start_time2 = self.launch_emu_and_wait(avd)
        self.m_logger.info('2nd try AVD %s, boot time: %s, expected time: %s'
                           % (avd, boot_time2, real_expected_boot_time))
        self.assertLessEqual(boot_time2, real_expected_boot_time)
        self.write_perf_data(boot_time1, start_time1,
                             boot_time2, start_time2)

    def run_boot_test(self, avd_config):
        self.avd_config = avd_config
        if self.create_avd(avd_config) == 0:
            self.boot_check(avd_config)


def create_test_case_for_avds():
    avd_list = emu_args.avd_list
    for avd in avd_list:
        def fn(i):
            return lambda self: self.boot_check(i)
        setattr(BootTestCase, "test_boot_%s" % avd, fn(avd))

if emu_args.config_file is None:
    create_test_case_for_avds()
else:
    emu_test.utils.emu_testcase.create_test_case_from_file("boot", BootTestCase, BootTestCase.run_boot_test)

if __name__ == '__main__':
    os.environ["SHELL"] = "/bin/bash"
    emu_argparser.emu_args = emu_argparser.get_parser().parse_args()
    print emu_argparser.emu_args
    sys.argv[1:] = emu_args.unittest_args
    unittest.main()
