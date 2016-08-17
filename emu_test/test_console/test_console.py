"""
This class is the entry point for console tests from dotest.py.
When the class is instantiated, it sets up logger and runs emulator for tests.
Then, using unittest loader, it loads all the console test cases
that are written in the python files with filename starting with "testcase_" in the same directory.
"""

import unittest
import os
import time
import psutil
import shutil
import sys
import re
from subprocess import PIPE
from utils.emu_error import *
from utils.emu_argparser import emu_args
import utils.emu_testcase
from utils.emu_testcase import EmuBaseTestCase, AVDConfig, create_test_case_from_file
from utils import emu_unittest
from subprocess import PIPE

class ConsoleTestCase(EmuBaseTestCase):

    def __init__(self, *args, **kwargs):
        super(ConsoleTestCase, self).__init__(*args, **kwargs)
        self.avd_config = None

    @classmethod
    def setUpClass(cls):
        super(ConsoleTestCase, cls).setUpClass()

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

    def printConsoleResult(self, emuResult):
        def getTestName(id):
            return id.rsplit('.', 1)[-1]
        self.m_logger.info("Run %d tests (%d fail, %d pass, %d xfail, %d xpass)",
               emuResult.testsRun, len(emuResult.failures)+len(emuResult.errors), len(emuResult.passes),
               len(emuResult.expectedFailures), len(emuResult.unexpectedSuccesses))
        if len(emuResult.passes) > 0:
            self.m_logger.info('------------------------------------------------------')
        for x in emuResult.passes:
            self.m_logger.info("PASS: %s", getTestName(x.id()))

        if len(emuResult.failures) + len(emuResult.errors) > 0:
            self.m_logger.info('------------------------------------------------------')
        for x in emuResult.failures:
            self.m_logger.info("Failure: %s", getTestName(x[0].id()))
        for x in emuResult.errors:
            self.m_logger.info("Error: %s", getTestName(x[0].id()))

        if len(emuResult.expectedFailures) > 0:
            self.m_logger.info('------------------------------------------------------')
        for x in emuResult.expectedFailures:
            self.m_logger.info("Expected Failure: %s", getTestName(x[0].id()))

        if len(emuResult.unexpectedSuccesses) > 0:
            self.m_logger.info('------------------------------------------------------')
        for x in emuResult.unexpectedSuccesses:
            self.m_logger.info("Unexpected Success: %s", getTestName(x.id()))

        self.m_logger.info('')

    def console_test_check(self, avd):
        """
        1) Run emulator with self.launch_emu_and_wait(avd)
        2) Print to logger that the test begins
        3) Load all the console tests using unittest.TestLoader()
        4) Verify whether every individual testcase was successful
        """
        self.launch_emu_and_wait(avd)
        self.m_logger.info('Console tests (%s) start.' % self._testMethodName)
        test_root_dir=os.path.dirname(os.path.realpath(__file__))
        emuSuite = unittest.TestLoader().discover(start_dir=test_root_dir, pattern="testcase_*")
        emuRunner = emu_unittest.EmuTextTestRunner(stream=sys.stdout)
        emuResult = emuRunner.run(emuSuite)
        self.printConsoleResult(emuResult)
        self.assertTrue(emuResult.wasSuccessful(), self._testMethodName + " was failed.")

    def run_console_test(self, avd_config):
        """
        Run console test with the given avd_config.
        This function first make sure whether avd is properly up or not.
        """
        self.avd_config = avd_config
        self.assertEqual(self.create_avd(avd_config), 0)
        self.console_test_check(avd_config)


if emu_args.config_file is None:
    sys.exit(-1)
else:
    utils.emu_testcase.create_test_case_from_file("console", ConsoleTestCase, ConsoleTestCase.run_console_test)

if __name__ == '__main__':
    os.environ["SHELL"] = "/bin/bash"
    emu_argparser.emu_args = emu_argparser.get_parser().parse_args()
    print emu_argparser.emu_args
    sys.argv[1:] = emu_args.unittest_args
    unittest.main()
