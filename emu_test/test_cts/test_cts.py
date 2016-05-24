"""Run CTS tests for emulator"""

import cts_results_parser

import json
import os, platform
import unittest
import psutil
import shutil
import re
import sys
import threading
from subprocess import PIPE,STDOUT

from utils import emu_argparser
from utils.emu_argparser import emu_args
from utils.emu_testcase import EmuBaseTestCase, AVDConfig
import utils.emu_testcase
api_to_android_version = {"23": "6.0",
                          "22": "5.1",
                          "21": "5.0",
                          "19": "4.4",
                          "18": "4.3",
                          "17": "4.2",
                          "16": "4.1",
                          "15": "4.0",
                          "10": "2.3"}
class CTSTestCase(EmuBaseTestCase):
    def __init__(self, *args, **kwargs):
        super(CTSTestCase, self).__init__(*args, **kwargs)

    @classmethod
    def setUpClass(cls):
        super(CTSTestCase, cls).setUpClass()

    def setUp(self):
        self.m_logger.info('Running - %s', self._testMethodName)

    def tearDown(self):
        def kill_proc_by_name(proc_names):
            for x in psutil.process_iter():
                try:
                    proc = psutil.Process(x.pid)
                    # mips 64 use qemu-system-mipsel64, others emulator-[arch]
                    if any([x in proc.name() for x in proc_names]):
                        if proc.status() != psutil.STATUS_ZOMBIE:
                            self.m_logger.info("kill_proc_by_name - %s, %s" % (proc.name(), proc.status()))
                            proc.kill()
                except psutil.NoSuchProcess:
                    pass

        self.m_logger.debug('First try - quit emulator by adb emu kill')
        kill_proc = psutil.Popen(["adb", "emu", "kill"])
        # check emulator process is terminated
        if not self.term_check(timeout=10):
            self.m_logger.debug('Second try - quit emulator by psutil')
            kill_proc_by_name(["emulator", "qemu-system"])
            result = self.term_check(timeout=10)
            self.m_logger.debug("term_check after psutil.kill - %s", result)
        try:
            kill_proc_by_name(["crash-service"])
            psutil.Popen(["adb", "kill-server"])
        except:
            pass

    def get_cts_exec(self, avd):
        home_dir = os.path.expanduser('~')
        cts_home = os.path.join(home_dir, 'Android', 'CTS')
        cts_dir = "%s-%s" % (api_to_android_version[avd.api], avd.abi)
        return os.path.join(cts_home, cts_dir, 'android-cts', 'tools', 'cts-tradefed')

    def run_cts_plan(self, avd, plan):
        result_re = re.compile("^.*XML test result file generated at (.*). Passed ([0-9]+), Failed ([0-9]+), Not Executed ([0-9]+)")
        #self.assertEqual(self.create_avd(avd), 0)
        self.launch_emu_and_wait(avd)

        exec_path = self.get_cts_exec(avd)
        cst_cmd = [exec_path, "run", "cts", "--plan", plan, "--disable-reboot"]
        # use "script -c" to force message flush, not available on Windows
        if platform.system() in ["Linux", "Darwin"]:
            cst_cmd = ["script", "-c", " ".join(cst_cmd)]

        vars = {'result_line': "",
                'cts_proc': None}

        def launch_in_thread():

            self.m_logger.info('executable path: ' + exec_path)
            vars['cts_proc'] = psutil.Popen(cst_cmd, stdout=PIPE, stdin=PIPE, stderr=STDOUT)
            lines_iterator = iter(vars['cts_proc'].stdout.readline, b"")
            for line in lines_iterator:
                self.simple_logger.info(line)
                if re.match(result_re, line):
                    vars['result_line'] = line
                    self.m_logger.info("Send exit to cts_proc")
                    vars['cts_proc'].stdin.write('exit\n')

        self.m_logger.info('Launching cts-tradefed, cmd: %s', ' '.join(cst_cmd))
        t_launch = threading.Thread(target=launch_in_thread)
        t_launch.start()
        t_launch.join()

        def move_log(name):
            """Copy CTS result to log directory"""
            src_log_path = os.path.join(os.path.dirname(exec_path), "..", "repository", "results", name)
            dst_log_path = os.path.join(emu_args.session_dir, name)
            self.m_logger.info("copy CTS log from %s to %s" % (src_log_path, dst_log_path))
            shutil.copytree(src_log_path, dst_log_path)
        if vars['result_line'] != "":
            log_name, pass_count, fail_count, skip_count = re.match(result_re, vars['result_line']).groups()
            self.m_logger.info("Pass: %s, Fail: %s, Not Executed: %s", pass_count, fail_count, skip_count)
            # copy CTS result to log dir, since cts-tradefed doesn't support custom log location
            move_log(log_name)
            self._checkResults(avd, fail_count,
                               os.path.join(emu_args.session_dir, log_name,
                                            'testResult.xml'))
        else:
            self.assertEqual('NA', '0')

    def _formatSet(self, to_format):
        to_format_list = sorted(to_format)
        # Arbitrary limit on how many names we print.
        num_explicit_names = 15
        result = ', '.join(to_format_list[:num_explicit_names])
        remaining = len(to_format_list) - num_explicit_names
        if remaining > 0:
            result += ' ... and %d others.' % remaining
        return result

    def _checkResults(self, avd, fail_count, cts_results_file):
        if fail_count == 0:
            return

        baseline = os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                'ctsTestCurrentFlakinessData.json')
        with open(baseline, 'r') as f:
            flakiness_data = json.load(f)
        if not flakiness_data:
            self.m_logger.warning('Found empty / corrupted flakiness data')
            return
        self.m_logger.debug('Loaded flakiness data with %d entries' %
                            len(flakiness_data))

        matches = [x for x in flakiness_data
                   if (x['systemImageApi'] == avd.api and
                       x['systemImageTag'] == avd.tag and
                       x['systemImageAbi'] == avd.abi)]
        ignored_fails = set()
        required_passes = set()
        fail_results = set(['flaky', 'bad', 'gotbroken'])
        pass_results = set(['good', 'gotFixed'])
        for target in matches:
            for result in target.get('ctsFlakinessRecords', []):
                full_name = result['fullName']
                flakiness_result = result['flakinessResult']
                if flakiness_result in fail_results:
                    ignored_fails.add(full_name)
                if flakiness_result in pass_results:
                    required_passes.add(full_name)
        # A test that is known to be good for some of the |matches|, but bad for
        # others should remain in |ignored_fails|, but not in |required_passes|.
        required_passes = required_passes - ignored_fails

        results = cts_results_parser.ExtractResults(cts_results_file)
        fails = set()
        passes = set()
        for result in results:
            full_name = '/'.join(
                    [result[x] for x in
                        ['PackageName', 'AppPackageName', 'TestSuiteName',
                        'TestCaseName', 'TestName']])
            if result['Result'] == 'fail':
                fails.add(full_name)
            elif result['Result'] == 'pass':
                passes.add(full_name)

        new_fails = fails - ignored_fails
        missing_passes = required_passes - passes

        self.m_logger.info('List of test fails that were ignored: %s' %
                           self._formatSet(ignored_fails & fails))
        if new_fails:
            self.m_logger.error('List of significant test failures '
                               '(i.e., why did this run go red): %s' %
                               self._formatSet(new_fails))
        if missing_passes:
            self.m_logger.error('List of missing test passes '
                               '(i.e., why did this run go red): %s' %
                                self._formatSet(missing_passes))
        self.assertEqual(0, len(new_fails) + len(missing_passes))


def create_test_case_for_avds():
    avd_name_re = re.compile("([^-]*)-(.*)-(.*)-(\d+)-gpu_(.*)-api(\d+)-CTS")
    def create_avd_from_name(avd_str):
        res = avd_name_re.match(avd_str)
        assert res is not None
        tag, abi, device, ram, gpu, api = avd_name_re.match(avd_str).groups()
        avd_config = AVDConfig(api, tag, abi, device, ram, gpu, classic="no", port="", cts=True, ori="mnc")
        return avd_config

    def fn(avd_name, plan):
        #return lambda self: self.run_cts_plan(create_avd_from_name(avd_name), plan)
        return lambda self: self.run_cts_plan(create_avd_from_name(avd_name), plan)

    for avd in emu_args.avd_list:
        if avd_name_re.match(avd):
            setattr(CTSTestCase, "test_cts_%s" % avd, fn(avd, "CTS"))

# TODO: create test case based on config file. Since we need to do some pre-work to run CTS, use static AVD at this time for simplicity.
create_test_case_for_avds()
#utils.emu_testcase.create_test_case_from_file("cts", CTSTestCase, CTSTestCase.run_cts_plan)

create_test_case_for_avds()
if __name__ == '__main__':
    emu_argparser.emu_args = emu_argparser.get_parser().parse_args()
    print emu_argparser.emu_args
    sys.argv[1:] = emu_args.unittest_args
    unittest.main()
