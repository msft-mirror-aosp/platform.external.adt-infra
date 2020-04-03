"""Test ADB"""

import glob
import importlib
import inspect
import os
import shutil
import subprocess
import sys
import time
import unittest
import xml.etree.ElementTree as ET
import psutil

import emu_test
from emu_test.utils import emu_argparser
from emu_test.utils import emu_testcase
from emu_test.utils import emu_unittest
from emu_test.utils import path_utils

CUR_DIR = os.path.dirname(os.path.realpath(__file__))
ADB_RESULT_XML_FILE = 'test_adbTestResult.xml'

g_xml_string_result = ''
g_avd_counter = 0

adb_binary = path_utils.get_adb_binary()

class AdbTestCase(emu_testcase.EmuBaseTestCase):
    """This class helps for run all adb tests."""

    def __init__(self, *args, **kwargs):
        super(AdbTestCase, self).__init__(*args, **kwargs)
        self.avd_config = None

    @classmethod
    def setUpClass(cls):
        super(AdbTestCase, cls).setUpClass()

    def kill_emulator(self):
        self.m_logger.debug('First try - quit emulator by adb emu kill')
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
        if emu_argparser.emu_args.use_device:
            return
        self.m_logger.info("Remove AVD inside of tear down")
        avd_dir = os.environ['ANDROID_AVD_HOME']
        try:
            if self.result and self.start_proc:
                self.start_proc.wait()
            time.sleep(1)
            self.kill_proc_by_name(["crash-service", "adb"])
            os.remove(os.path.join(avd_dir, '%s.ini' % self.avd_config.name()))
            shutil.rmtree(os.path.join(avd_dir, '%s.avd' % self.avd_config.name()), ignore_errors=True)
        except Exception, e:
            self.m_logger.error("Error in cleanup - %r" % e)
            pass

    def get_test_name(self, failed_test_id):
        return failed_test_id.rsplit('.', 1)[-1]

    def create_result_xml(self, emu_result):
        global g_xml_string_result
        global g_avd_counter
        g_avd_counter += 1

        dst_path = os.path.join(emu_argparser.emu_args.session_dir,
                                emu_argparser.emu_args.test_dir,
                                ADB_RESULT_XML_FILE)

        result = ET.Element('testsuite', name=self._testMethodName)
        result.set('tests', str(emu_result.testsRun))
        result.set('failures', str(len(emu_result.failures)))
        result.set('errors', str(len(emu_result.errors)))

        for x in emu_result.passes:
            ET.SubElement(result, 'testcase', name=self.get_test_name(x.id()),
                          test_result='pass')

        for x in emu_result.failures:
            testcase = ET.SubElement(result, 'testcase',
                                     name=self.get_test_name(x[0].id()),
                                     test_result='fail')
            failure = ET.SubElement(testcase, 'failure')
            failure.text = getattr(x[0].failureException, '__doc__', 'failed')

        for x in emu_result.errors:
            testcase = ET.SubElement(result, 'testcase',
                                     name=self.get_test_name(x[0].id()),
                                     test_result='error')
            error = ET.SubElement(testcase, 'failure')
            error.text = getattr(x[0].failureException, '__doc__', 'failed')

        for x in emu_result.expectedFailures:
            ET.SubElement(result, 'testcase',
                          name=self.get_test_name(x[0].id()),
                          test_result='expected failure')

        for x in emu_result.unexpectedSuccesses:
            ET.SubElement(result, 'testcase',
                          name=self.get_test_name(x.id()),
                          test_result='unexpected failure')

        xml_string_result = ET.tostring(result)
        # Saves each avd testing result to global variable: g_xml_string_result
        g_xml_string_result += xml_string_result

        # Refresh the current whole test result page.
        with open(dst_path, 'w+') as modified:
            modified.write(('%s' % g_xml_string_result))
            self.m_logger.info("Wrote %s" % dst_path)

    def print_adb_result(self, emu_result):
        self.m_logger.info(
            'Run %d tests (%d fail, %d pass, %d xfail, %d xpass)' %
            (emu_result.testsRun,
             len(emu_result.failures) + len(emu_result.errors),
             len(emu_result.passes),
             len(emu_result.expectedFailures),
             len(emu_result.unexpectedSuccesses)))

        border_line = '------------------------------------------------------'
        if emu_result.passes:
            self.m_logger.info(border_line)
        for x in emu_result.passes:
            self.m_logger.info('PASS: %s' % self.get_test_name(x.id()))

        if len(emu_result.failures) + len(emu_result.errors) > 0:
            self.m_logger.info(border_line)
        for x in emu_result.failures:
            self.m_logger.info('Failure: %s' % self.get_test_name(x[0].id()))
        for x in emu_result.errors:
            self.m_logger.info('Error: %s' % self.get_test_name(x[0].id()))

        if emu_result.expectedFailures:
            self.m_logger.info(border_line)
        for x in emu_result.expectedFailures:
            self.m_logger.info('Expected Failure: %s' %
                               self.get_test_name(x[0].id()))

        if emu_result.unexpectedSuccesses:
            self.m_logger.info(border_line)
        for x in emu_result.unexpectedSuccesses:
            self.m_logger.info('Unexpected Success: %s' %
                               self.get_test_name(x.id()))

        self.m_logger.info('')
        self.create_result_xml(emu_result)

    def get_all_adb_test_classes(self):
        current_dir = os.path.dirname(os.path.realpath(__file__))

        test_classes = []
        for test_file in glob.glob(os.path.join(current_dir, 'testcase_*.py')):
            name = os.path.splitext(os.path.basename(test_file))[0]
            test_module = importlib.import_module('.' + name, 'test_adb')
            for member in dir(test_module):
                handler_class = getattr(test_module, member)
                if handler_class and inspect.isclass(handler_class):
                    test_classes.append(handler_class)

        return test_classes

    def adb_test_check(self, avd):
        """Checks ADB test.

        1) Print to logger that the test begins
        2) Load all the adb tests using unittest.TestLoader()
        3) Verify whether every individual testcase was successful

        Args:
          avd: The running avd.
        """
        self.m_logger.info('ADB tests (%s) start.' % self._testMethodName)
        if not emu_argparser.emu_args.use_device:
            self.launch_emu_and_wait(avd)
        test_classes = self.get_all_adb_test_classes()
        emu_suite = unittest.TestSuite()
        for test_class in test_classes:
            for method in dir(test_class):
                if method.startswith('test_'):
                    emu_suite.addTest(test_class(method, avd))

        emu_runner = emu_unittest.EmuTextTestRunner(stream=sys.stdout)
        emu_result = emu_runner.run(emu_suite)
        if not emu_argparser.emu_args.use_device:
            self.result = self.kill_emulator()
        self.print_adb_result(emu_result)
        self.run_with_timeout([adb_binary, 'kill-server'], 20)
        self.assertTrue(emu_result.wasSuccessful(),
                        '%s was failed.' % self._testMethodName)

    def run_adb_test(self, avd_config):
        """Run ADB test.

        Run ADB test with the given avd_config.
        This function first make sure whether avd is properly up or not.

        Args:
          avd_config: The avd configuration.
        """
        self.avd_config = avd_config
        if not emu_argparser.emu_args.use_device:
            self.assertEqual(self.create_avd(avd_config), 0)
        self.adb_test_check(avd_config)


if emu_argparser.emu_args.config_file is None:
    sys.exit(-1)
else:
    emu_test.utils.emu_testcase.create_test_case_from_file(
        'adb', AdbTestCase, AdbTestCase.run_adb_test)

if __name__ == '__main__':
    os.environ['SHELL'] = '/bin/bash'
    emu_argparser.emu_args = emu_argparser.get_parser().parse_args()
    print emu_argparser.emu_args
    sys.argv[1:] = emu_argparser.emu_args.unittest_args
    unittest.main()
