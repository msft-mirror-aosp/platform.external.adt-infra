"""System image UI tests"""

import unittest
import os
import time
import psutil
import shutil
import sys
import re
import subprocess
from subprocess import PIPE

from emu_test.utils.emu_argparser import emu_args
from emu_test.utils.emu_testcase import EmuBaseTestCase, create_test_case_from_file
from emu_test.utils import path_utils

class UiAutomatorBaseTestCase(EmuBaseTestCase):
    def __init__(self, *args, **kwargs):
        super(UiAutomatorBaseTestCase, self).__init__(*args, **kwargs)
        self.avd_config = None

    @classmethod
    def setUpClass(cls):
        super(UiAutomatorBaseTestCase, cls).setUpClass()

    def tearDown(self):
        self.m_logger.debug('First try - quit emulator by adb emu kill')
        adb_binary = path_utils.get_adb_binary()
        kill_proc = psutil.Popen([adb_binary, "emu", "kill"])
        # check emulator process is terminated
        result = self.term_check(timeout=10)
        if not result:
            self.m_logger.debug('Second try - quit emulator by psutil')
            self.kill_proc_by_name(["emulator", "qemu-system"])
            result = self.term_check(timeout=10)
            self.m_logger.debug("term_check after psutil.kill - %s", result)
        self.m_logger.info("Remove AVD inside of tear down")
        avd_dir = os.environ['ANDROID_AVD_HOME']

        if emu_args.save_snapshot:
          try:
              dist_dir = os.environ["SNAPSHOT_DIR"]
              avd = self.avd_config.name()
              self.m_logger.info("copy %s to %s", os.path.join(avd_dir, avd+'.avd'), os.path.join(dist_dir, avd+'.avd'))
              shutil.copytree(os.path.join(avd_dir, avd+'.avd'), os.path.join(dist_dir, avd+'.avd'))
              self.m_logger.info("copy %s to %s", os.path.join(avd_dir, avd+'.ini'), os.path.join(dist_dir, avd+'.ini'))
              shutil.copyfile(os.path.join(avd_dir, avd+'.ini'), os.path.join(dist_dir, avd+'.ini'))
          except KeyError:
              self.m_logger.error("Please set SNAPSHOT_DIR to provide destination directory for snapshots.")

        try:
            if result and self.start_proc:
                self.start_proc.wait()
            time.sleep(1)
            self.kill_proc_by_name(["crash-service", "adb"])
            os.remove(os.path.join(avd_dir, '%s.ini' % self.avd_config.name()))
            if sys.platform == "win32":
                rm_avd = "rmdir /s /q " + os.path.join(avd_dir, '%s.avd' % self.avd_config.name()) 
                os.system(rm_avd)
            else:
                shutil.rmtree(os.path.join(avd_dir, '%s.avd' % self.avd_config.name()), ignore_errors=True)
        except Exception as e:
            self.m_logger.error("Error in cleanup - %r", e)
            pass

    def _save_gradle_test_report(self, test_method):
        self.m_logger.info('Generate reports from Gradle')
        # Copy HTML reports
        gradle_report_path = os.path.join(self.uitest_dir, 'app', 'build', 'reports', 'androidTests', 'connected', '')
        if not os.path.exists(gradle_report_path):
            self.m_logger.info('Failed to find gradle HTML reports.')
        else:
            dst_path = os.path.join(emu_args.session_dir, emu_args.test_dir, test_method + '_HTML_report')
            if os.path.exists(dst_path):
                shutil.rmtree(dst_path)
            shutil.copytree(gradle_report_path, dst_path)

        # Copy XML reports
        gradle_report_path = os.path.join(self.uitest_dir, 'app', 'build', 'outputs', 'androidTest-results', 'connected', '')
        if not os.path.exists(gradle_report_path):
            self.m_logger.info('Failed to find gradle XML reports.')
        else:
            xml_file = ''
            for filename in os.listdir(gradle_report_path):
                if filename.endswith('.xml'):
                    xml_file = filename
            if not xml_file:
                self.m_logger.info('Failed to find gradle XML report.')
                return
            src_file = os.path.join(gradle_report_path, xml_file)
            dst_file = os.path.join(emu_args.session_dir, emu_args.test_dir, test_method + '.xml')
            if os.path.isfile(dst_file):
                os.remove(dst_file)
            shutil.copyfile(src_file, dst_file)

    def _save_adb_bug_report(self, test_method):
        adb_binary = path_utils.get_adb_binary()
        self.m_logger.info('Generate ADB bugreport')
        dst_path = os.path.join(emu_args.session_dir, emu_args.test_dir, test_method + '_bugreport.txt')
        with open(dst_path, 'w') as f:
            p = psutil.Popen([adb_binary, 'bugreport'], stdout=f, stderr=f)
            p.communicate()

    def _pull_log_details(self, test_method):
        adb_binary = path_utils.get_adb_binary()
        self.m_logger.info('Pull details from sdcard')
        dst_path = os.path.join(emu_args.session_dir, emu_args.test_dir, test_method + '_details')
        p = psutil.Popen([adb_binary, 'pull',
                          '/sdcard/Documents/Logs', dst_path],
                         stdout=PIPE, stderr=PIPE)
        (out, err) = p.communicate()
        self.m_logger.info('adb_pull_stdout:\n' + out.decode())
        self.m_logger.info('adb_pull_stderr:\n' + err.decode())

    def _launch_single_class_ui_test_with_avd_configs(self, avd, class_name):
        """Launch a new AVD per class of tests.

        Each class of tests will run in it's own instance of the emulator.
        Without this method, the entire suite of tests (all classes) run in
        one instance of the emulator.

        Args:
            avd: The AVD configuration.
            class_name: Class name of UI tests.

        Returns the process.

        """
        if 'android-tv' in avd.tag:
           pkg = 'tv'
        elif 'android-wear' in avd.tag:
           pkg = 'wear'
        else:
           pkg = 'smoke'
           adb_binary = path_utils.get_adb_binary()
           execute_query = psutil.Popen([adb_binary, 'shell', 'pm', 'dump', 'com.google.android.gms',
                                         '|', 'grep', 'versionName'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
           out, err = execute_query.communicate()
           self.m_logger.info('GMSCore version is::' + str(out).lstrip())
        test_args_prefix = '-Pandroid.testInstrumentationRunnerArguments'
        test_class = test_args_prefix + '.class=com.android.devtools.systemimage.uitest.' +\
                     pkg + '.api' + avd.api + '.' + class_name
        test_api = '%s.api=%s' % (test_args_prefix, avd.api)
        test_abi = test_args_prefix + '.abi=' + avd.abi
        test_tag = test_args_prefix + '.tag=' + avd.tag
        test_ori = test_args_prefix + '.origin=' + avd.ori
        self.m_logger.info('Calling gradle with cwd %r params: %r', self.uitest_dir,
                           [self.gradle, 'cAT', test_class, test_api, test_abi, test_tag,
                            test_ori, '--stacktrace'])
        return psutil.Popen([self.gradle, 'cAT', test_class, test_api, test_abi, test_tag,
                             test_ori, '--stacktrace'], cwd=self.uitest_dir, stdout=PIPE, stderr=PIPE,
                            shell=self.use_shell)

    def _launch_ui_test_with_avd_configs(self, avd):
        if 'android-tv' in avd.tag:
           pkg = 'tv'
        elif 'android-wear' in avd.tag:
           pkg = 'wear'
        else:
           pkg = 'smoke'
        test_args_prefix = '-Pandroid.testInstrumentationRunnerArguments'
        test_package = test_args_prefix + '.package=com.android.devtools.systemimage.uitest.' +\
                       pkg + '.api' + avd.api
        test_api = test_args_prefix + '.api=' + avd.api
        test_abi = test_args_prefix + '.abi=' + avd.abi
        test_tag = test_args_prefix + '.tag=' + avd.tag
        test_ori = test_args_prefix + '.origin=' + avd.ori
        return psutil.Popen([self.gradle, 'cAT', test_package, test_api, test_abi, test_tag, test_ori],
                            cwd=self.uitest_dir, stdout=PIPE, stderr=PIPE, shell=self.use_shell)

    def _launch_local_presubmit_check(self, avd, test_method):
        adb_binary = path_utils.get_adb_binary()
        p1 = psutil.Popen([self.gradle, 'installDebug'],
                          cwd=self.uitest_dir, stdout=PIPE, stderr=PIPE, shell=self.use_shell)
        p1.communicate()
        p2 = psutil.Popen([self.gradle, 'installDebugAndroidTest'],
                          cwd=self.uitest_dir, stdout=PIPE, stderr=PIPE, shell=self.use_shell)
        p2.communicate()
        self.assertTrue(p1.poll() == 0 and p2.poll() == 0, "Failed to install the instrumentation APK.")

        p = psutil.Popen([adb_binary, 'shell', 'am', 'instrument', '-w',
                          '-e', 'class', test_method,
                          '-e', 'api', avd.api, '-e', 'abi', avd.abi, '-e', 'tag', avd.tag, '-e', 'origin', avd.ori,
                          'com.android.devtools.systemimage.uitest.test/android.support.test.runner.AndroidJUnitRunner'],
                         cwd=self.uitest_dir, stdout=PIPE, stderr=PIPE, shell=self.use_shell)
        (out, err) = p.communicate()
        self.m_logger.info('instrumentation_test_stdout:\n' + out)
        self.m_logger.info('instrumentation_test_stderr:\n' + err)
        self.assertTrue(p.poll() == 0 and 'FAILURES!!!' not in out, "%s failed." % test_method)

    def ui_test_check(self, avd, class_name=None):
        """Runs all UI tests for the AVD described by 'avd' and the class 'class_name'.

        Runs all tests if class_name is None.
        """
        self.launch_emu_and_wait(avd)
        self.m_logger.info('System image UI tests (%s) start.' % self._testMethodName)
        if os.name is 'nt':
            self.gradle = 'gradlew.bat'
            self.use_shell = True
        else:
            self.gradle = './gradlew'
            self.use_shell = False
        self.uitest_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', 'system_image_uitests')

        # check if it is a local presubmit test
        if emu_args.uitest_psc_pkg is not None:
            test = emu_args.uitest_psc_pkg + '.api' + avd.api + '.' + emu_args.uitest_psc_test
            self._launch_local_presubmit_check(avd, test)
            return

        # run tests using gradle script
        self.m_logger.info('Test class: %s', class_name)
        proc = self._launch_single_class_ui_test_with_avd_configs(avd, class_name)
        (out, err) = proc.communicate()
        self.m_logger.info('gradle_stdout:\n' + out.decode())
        self.m_logger.info('gradle_stderr:\n' + err.decode())

        # save gradle reports
        self._save_gradle_test_report(self._testMethodName)

        if "AddGoogleAccountTest" in self._testMethodName:
            # save adb bug reports for the bug report automation purpose
            self._save_adb_bug_report(self._testMethodName)

        # pull detailed test case log info from android
        self._pull_log_details(self._testMethodName)

        self.m_logger.info('System image UI tests (%s) end.' % self._testMethodName)
        self.assertTrue(proc.returncode == 0, "The UI tests failed.")

    def run_ui_test(self, avd_config, class_name=None):
        """Creates an AVD described by 'avd_config' or load a previously
        saved snapshot and runs UI tests.

        If the 'class_name' is provided, runs only the tests in that class.
        Otherwise all UI tests run.
        """
        self.avd_config = avd_config
        if emu_args.load_snapshot:
            self.assertEqual(self.copy_snapshot(avd_config), 0)
        else:
            self.assertEqual(self.create_avd(avd_config), 0)
        self.ui_test_check(avd_config, class_name)

    def save_snapshot(self, avd_config):
        """Save snapshot for an AVD described by 'avd_config'
        """
        self.uitest_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', 'system_image_uitests')
        self.avd_config = avd_config
        self.assertEqual(self.create_avd(avd_config), 0)
        self.launch_emu_and_wait(avd_config)
        if "google_apis_playstore" in avd_config.tag:
            adb_binary = path_utils.get_adb_binary()
            # Turn off ac charger. Keep display on.
            subprocess.call([adb_binary, 'emu', 'power', 'ac', 'off'])
            subprocess.call([adb_binary, 'shell', 'settings', 'put', 'system', 'screen_off_timeout', '2147483647'])
            subprocess.call([adb_binary, 'shell', 'dumpsys', 'battery', 'set', 'level', '10'])

            # Pre-Install required APKs
            path_to_apk = os.path.join(self.uitest_dir, "app", "src", "main", "assets")
            apks = ["ApiDemos_x86.apk", "CrashExample.apk", "FredVPN.apk", "HelloAr_C.apk", "HelloCompute.apk"]
            for apk in apks:
                subprocess.call([adb_binary,
                                 'install',
                                 '-g',
                                 os.path.join(path_to_apk, apk)])

        # wait for 5 minutes before taking the snapshot
        time.sleep(300)

if emu_args.config_file is None:
    sys.exit(0)
else:
    # When running with save_snapshot option, it will save a snaphot for every
    # AVD config defined by the config file.
    # OR
    # When not running a local presubmit test, find the names of all test
    # classes and create an individual test case function for each class. This
    # allows us to launch a new emulator for each test class, which is more
    # robust in the case of emulator hangs or other such failures.
    if emu_args.save_snapshot:
        create_test_case_from_file("ui", UiAutomatorBaseTestCase, UiAutomatorBaseTestCase.save_snapshot)
    else:
        create_test_case_from_file("ui", UiAutomatorBaseTestCase, UiAutomatorBaseTestCase.run_ui_test,
                                   emu_args.uitest_psc_pkg is None)


if __name__ == '__main__':
    os.environ["SHELL"] = "/bin/bash"
    emu_argparser.emu_args = emu_argparser.get_parser().parse_args()
    print(emu_argparser.emu_args)
    sys.argv[1:] = emu_args.unittest_args
    unittest.main()
