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

    def _save_gradle_test_report(self, test_method, gradle_report_path):
        dst_path = os.path.join(emu_args.session_dir, test_method + '_report')
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
        self.m_logger.info('System image UI tests (%s) start.' % self._testMethodName)
        uitest_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', 'system_image_uitests')

        # install APKs required in UI tests
        uitest_assets_dir = os.path.join(uitest_dir, 'app', 'src', 'main', 'assets')
        for filename in os.listdir(uitest_assets_dir):
            if filename.endswith('.apk'):
                p = psutil.Popen(['adb', 'install', '-r', filename], cwd=uitest_assets_dir, stdout=PIPE, stderr=PIPE)
                (out, err) = p.communicate()
                self.m_logger.info('Install APK, stdout: %s, stderr: %s', out, err)
                self.assertTrue(p.poll() == 0, "Failed to install %s." % filename)

        # run tests using gradle script
        proc = self._launch_ui_test_with_avd_configs(uitest_dir, avd)
        (output, err) = proc.communicate()
        self.m_logger.info('gradle_stdout:\n' + output)
        self.m_logger.info('gradle_stderr:\n' + err)
        if err is not None and len(err.strip()) > 0:
            m = re.search('file://(.+)index\.html', err)
            if m.group(1) is None:
                self.m_logger.error("Failed to find the gradle test report.")
            self._save_gradle_test_report(self._testMethodName, m.group(1))
        self.m_logger.info('System image UI tests (%s) end.' % self._testMethodName)
        self.assertTrue(err is None or len(err.strip()) == 0, "The UI tests failed.")

    def run_ui_test(self, avd_config):
        self.avd_config = avd_config
        self.assertEqual(self.create_avd(avd_config), 0)
        self.ui_test_check(avd_config)


if emu_args.config_file is None:
    sys.exit(0)
else:
    create_test_case_from_file("ui", UiAutomatorBaseTestCase, UiAutomatorBaseTestCase.run_ui_test)

if __name__ == '__main__':
    os.environ["SHELL"] = "/bin/bash"
    emu_argparser.emu_args = emu_argparser.get_parser().parse_args()
    print emu_argparser.emu_args
    sys.argv[1:] = emu_args.unittest_args
    unittest.main()