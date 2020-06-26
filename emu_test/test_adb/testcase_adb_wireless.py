"""Run adb wireless tests"""

import inspect
import os
import psutil
import unittest
from subprocess import PIPE

import testcase_base
from emu_test.utils import emu_argparser

class AdbWirelessTest(testcase_base.BaseAdbTest):
    """This class aims to run adb wireless tests."""

    def __init__(self, method_name=None):
        if method_name:
            super(AdbWirelessTest, self).__init__(method_name)
        else:
            super(AdbWirelessTest, self).__init__()
    adbUtils_dir = None
    gradle = None
    use_shell = None

    def setUp(self):
        self.adbUtils_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', 'adb_wireless_test')
        self.gradle = './gradlew'
        self.use_shell = False

        # install instrumented adb utility
        p1 = psutil.Popen([self.gradle, 'installDebug'],
                          cwd=self.adbUtils_dir, stdout=PIPE, stderr=PIPE, shell=self.use_shell)
        p1.communicate()
        p2 = psutil.Popen([self.gradle, 'installDebugAndroidTest'],
                          cwd=self.adbUtils_dir, stdout=PIPE, stderr=PIPE, shell=self.use_shell)
        p2.communicate()
        self.assertTrue(p1.poll() == 0 and p2.poll() == 0, "Failed to install the instrumentation APK.")

        # Clear device logcat
        p3 = psutil.Popen([self.adb_binary, 'logcat', '-b', 'all', '-c'],
                          cwd='.', stdout=PIPE, stderr=PIPE, shell=self.use_shell)
        p3.communicate()

    def tearDown(self):
        """There is nothing to do in tearDown()."""
        pass

    def _run_adb_wireless_util_func(self, util_func):
        p = psutil.Popen([self.adb_binary, 'shell', 'am', 'instrument', '-w',
                          '-e', 'class', 'com.android.devtools.adbtestutils.AdbTestUtils#'+util_func,
                          'com.android.devtools.adbtestutils.test/android.support.test.runner.AndroidJUnitRunner'],
                         cwd='.', stdout=PIPE, stderr=PIPE, shell=self.use_shell)
        (out, err) = p.communicate()

    def test_adb_wireless_connect(self):
        print 'Running test: %s' % (inspect.stack()[0][3])
        # Run util function
        self._run_adb_wireless_util_func('openPairCode')

        # Gather logcat
        p = psutil.Popen([self.adb_binary, 'logcat', '-d', 'ADBWireless:I', '*:S'],
                         cwd='.', stdout=PIPE, stderr=PIPE, shell=self.use_shell)
        (out, err) = p.communicate()

        logcat_file = os.path.join(emu_argparser.emu_args.session_dir,
                                   emu_argparser.emu_args.test_dir,
                                   'adb_util_logcat.log')
        logcat_err_file = os.path.join(emu_argparser.emu_args.session_dir,
                                       emu_argparser.emu_args.test_dir,
                                       'adb_util_logcat.err')
        f = open(logcat_file, 'w')
        f.write(out)
        f.close()
        f = open(logcat_err_file, 'w')
        f.write(err)
        f.close()

        dst_path = os.path.join(emu_argparser.emu_args.session_dir,
                                emu_argparser.emu_args.test_dir,
                                'adb_util_details')
        p = psutil.Popen([self.adb_binary, 'pull', '/sdcard/Logs', dst_path],
                         cwd='.', stdout=PIPE, stderr=PIPE, shell=self.use_shell)
        (out1, err1) = p.communicate()

        connect_ip = ''
        pair_ip = ''
        pair_code = ''
        # Extract ip, pair code and ports
        for line in out.split('\n'):
            print line
            if 'connect ip' in line:
                connect_ip = line.split()[-1]
            elif 'pair ip' in line:
                pair_ip = line.split()[-1]
            elif 'pair code' in line:
                pair_code = line.split()[-1]

        self.assertTrue(connect_ip != '', "Connect ip not found")
        self.assertTrue(pair_ip != '', "Pair ip not found")
        self.assertTrue(pair_code != '', "Pair code not found")

        print "connect ip " + connect_ip
        print "pair ip " + pair_ip
        print "pair code " + pair_code

        p = psutil.Popen([self.adb_binary, 'pair', pair_ip],
                         cwd='.', stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=self.use_shell)
        (out, err) = p.communicate(pair_code)

        p = psutil.Popen([self.adb_binary, 'connect', connect_ip],
                         cwd='.', stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=self.use_shell)
        (out, err) = p.communicate()


if __name__ == '__main__':
    print '======= ADB Wireless Tests ======='
    unittest.main()

