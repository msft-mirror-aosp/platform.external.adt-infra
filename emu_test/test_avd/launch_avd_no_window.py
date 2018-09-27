"""AVD Launch test.

Verify the emulator launched in AVD without window can be detected.

usage: launch_avd_no_window.py [-h] [-t TIMEOUT_IN_SECONDS] --avd AVD
                               [--exec EMULATOR_EXEC]
"""

import logging
import os
import sys
import unittest

import emu_test
from emu_test.utils import emu_argparser
from emu_test.utils.emu_testcase import EmuBaseTestCase, AVDConfig

from launch_avd import launch_emu_and_wait

log = logging.getLogger('launch_avd_no_window')

class LaunchAVDNoWindowTest(EmuBaseTestCase):
    def launch_avd(self, avd_config):
        self.avd_config = avd_config
        self.assertEqual(self.create_avd(avd_config), 0)
        test_name  = self.id().rsplit('.', 1)[-1]
        emu_log_path = os.path.join(emu_argparser.emu_args.session_dir,
                                    emu_argparser.emu_args.test_dir,
                                    "%s_verbose.txt" % test_name)
        args = ['-port', '5554', '-wipe-data', '-no-boot-anim', '-no-snapshot',
                '-no-window', '-qemu', '-enable-kvm']
        with open(emu_log_path, 'wb') as emu_log:
            return launch_emu_and_wait(avd_config,
                                       emu_argparser.emu_args,
                                       emu_log,
                                       additional_args = args)


if emu_argparser.emu_args.config_file is None:
    sys.exit(-1)
else:
    emu_test.utils.emu_testcase.create_test_case_from_file(
        'launch_avd', LaunchAVDNoWindowTest, LaunchAVDNoWindowTest.launch_avd)


if __name__ == '__main__':
    os.environ['SHELL'] = '/bin/bash'
    emu_argparser.emu_args = emu_argparser.get_parser().parse_args()
    log.info(emu_argparser.emu_args)
    sys.argv[1:] = emu_argparser.emu_args.unittest_args
    unittest.main()