"""System image UI tests"""

import unittest
import os
import time
import psutil
import shutil
import sys
import re
from subprocess import PIPE

from utils.emu_argparser import emu_args
from utils.emu_testcase import EmuBaseTestCase, create_test_case_from_file

class UiAutomatorBaseTestCase(EmuBaseTestCase):
    def __init__(self, *args, **kwargs):
        super(UiAutomatorBaseTestCase, self).__init__(*args, **kwargs)
        self.avd_config = None

    @classmethod
    def setUpClass(cls):
        super(UiAutomatorBaseTestCase, cls).setUpClass()

    def tearDown(self):
        self.m_logger.debug('First try - quit emulator by adb emu kill')
        kill_proc = psutil.Popen(["adb", "emu", "kill"])
        # check emulator process is terminated
        result = self.term_check(timeout=5)
        if not result:
            self.m_logger.debug('Second try - quit emulator by psutil')
            self.kill_proc_by_name(["emulator", "qemu-system"])
            result = self.term_check(timeout=10)
            self.m_logger.debug("term_check after psutil.kill - %s", result)
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
            self.m_logger.error("Error in cleanup - %r", e)
            pass

    def _save_gradle_test_report(self, avd, gradle_report_path):
        dst_path = os.path.join(emu_args.session_dir, str(avd) + '_report')
        if os.path.exists(dst_path):
            shutil.rmtree(dst_path)
        shutil.copytree(gradle_report_path, dst_path)

    def _launch_ui_test_with_avd_configs(self, uitest_dir, avd):
        if os.name is 'nt':
            gradle = 'gradlew.bat'
        else:
            gradle = './gradlew'
        test_args_prefix = '-Pandroid.testInstrumentationRunnerArguments'
        test_package = test_args_prefix + '.package=com.android.devtools.systemimage.uitest.smoke'
        test_api = test_args_prefix + '.api=' + avd.api
        test_abi = test_args_prefix + '.abi=' + avd.abi
        test_tag = test_args_prefix + '.tag=' + avd.tag
        test_ori = test_args_prefix + '.origin=' + avd.ori
        return psutil.Popen([gradle, 'cAT', test_package, test_api, test_abi, test_tag, test_ori],
                            cwd=uitest_dir, stdout=PIPE, stderr=PIPE)

    def ui_test_check(self, avd):
        self.launch_emu_and_wait(avd)
        self.m_logger.info('AVD %s, system image UI tests start.', avd)
        uitest_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', 'system_image_uitests')
        proc = self._launch_ui_test_with_avd_configs(uitest_dir, avd)
        (output, err) = proc.communicate()
        self.m_logger.info(output)
        self.m_logger.info(err)
        m = re.search('file://(.+)index\.html', err)
        self.assertIsNotNone(m.group(1), "Failed to find the gradle test report.")
        self._save_gradle_test_report(avd, m.group(1))
        self.m_logger.info('AVD %s, system image UI tests end.', avd)

    def run_ui_test(self, avd_config):
        self.avd_config = avd_config
        self.assertEqual(self.create_avd(avd_config), 0)
        self.ui_test_check(avd_config)


def create_test_case_for_avds():
    avd_list = emu_args.avd_list
    for avd in avd_list:
        def fn(i):
            return lambda self: self.ui_test_check(i)
        setattr(UiAutomatorBaseTestCase, "test_ui_%s" % avd, fn(avd))


if emu_args.config_file is None:
    create_test_case_for_avds()
else:
    create_test_case_from_file("ui", UiAutomatorBaseTestCase, UiAutomatorBaseTestCase.run_ui_test)

if __name__ == '__main__':
    os.environ["SHELL"] = "/bin/bash"
    emu_argparser.emu_args = emu_argparser.get_parser().parse_args()
    print emu_argparser.emu_args
    sys.argv[1:] = emu_args.unittest_args
    unittest.main()