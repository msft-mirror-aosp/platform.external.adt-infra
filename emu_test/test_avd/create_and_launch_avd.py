"""AVD Launch test.

Verify an AVD can be created with avdmanager command line interface and then launched.

usage: create_and_launch_avd.py [-h] [-t TIMEOUT_IN_SECONDS] --avd AVD
                                [--exec EMULATOR_EXEC]
"""
import logging
import os
import psutil
from subprocess import PIPE
import sys
import unittest

import emu_test
import emu_test.utils.path_utils as path_utils
from emu_test.utils import emu_argparser
from emu_test.utils.emu_testcase import EmuBaseTestCase, AVDConfig
from launch_avd import launch_emu_and_wait

log = logging.getLogger('launch_avd_no_window')

class CreateAndLaunchAVDTest(EmuBaseTestCase):
    """Tests for creating an AVD via AVD Manager command line interface and launching it."""

    def launch_avd(self, avd_config):
        """Launch AVD with given config."""
        self.avd_config = avd_config
        self.assertEqual(self.create_avd(avd_config), 0)
        test_name  = self.id().rsplit('.', 1)[-1]
        emu_log_path = os.path.join(emu_argparser.emu_args.session_dir,
                                    emu_argparser.emu_args.test_dir,
                                    '%s_verbose.txt' % test_name)

        args = ['-port', '5554', '-wipe-data', '-no-boot-anim', '-no-snapshot',
                '-no-window', '-qemu', '-enable-kvm']
        with open(emu_log_path, 'wb') as emu_log:
            return launch_emu_and_wait(avd_config,
                                       emu_argparser.emu_args,
                                       emu_log,
                                       additional_args = args)

    def create_avd(self, avd_config):
        """
        Create AVD, overwriting old AVD if it exists.

        This method overrides the implementation in `EmuBaseTestCase`
        to use the `avdmanager` command-line interface.

        :param avd_config: Configuration representing the AVD we wish to create.
        :return: Return code of the AVD create process.
        """
        def try_create_with_sdk():
            """
            Create AVD using the avdmanager command line tool.

            :return: Return code of android command line tool.
            """
            avdmanager_binary = path_utils.get_avdmanager_binary()
            avd_abi = '%s/%s' % (avd_config.tag, avd_config.abi)
            api_target = avd_config.api
            avd_target = ';'.join(['system-images',
                                   'android-%s' % api_target,
                                   avd_config.tag,
                                   avd_config.abi])
            create_cmd = [avdmanager_binary, 'create', 'avd', '--force',
                          '--name', avd_name,
                          '-k', avd_target,
                          '-d', avd_config.device,
                          '-c', '20M']
            self.m_logger.info('Create AVD, cmd: %s' % ' '.join(create_cmd))
            avd_proc = psutil.Popen(create_cmd, stdout=PIPE, stdin=PIPE, stderr=PIPE)
            stdout, stderr = avd_proc.communicate(input='\n')
            self.simple_logger.debug(stdout)
            self.simple_logger.debug(stderr)
            if 'Error' in stderr:
                return -1
            return avd_proc.poll()

        # Function execution starts here.
        avd_name = str(avd_config)
        self.m_logger.info('Attempt to create AVD %s.' % avd_name)
        ret = try_create_with_sdk()
        if ret == 1:
            # If we failed to create the AVD with a return of 1, we may be missing the required image.
            # Try to download it.
            api = avd_config.api
            self.install_sdk_package('platforms;android-%s' % api)
            if 'google_apis_playstore' in avd_config.tag:
                self.install_sdk_package('system-images;android-%s;google_apis_playstore;%s'
                                         % (api, avd_config.abi))
            elif 'google' in avd_config.tag:
                self.install_sdk_package('add-ons;addon-google_apis-google-%s' % api)
                self.install_sdk_package('system-images;android-%s;google_apis;%s'
                                         % (api, avd_config.abi))
            elif 'wear' in avd_config.tag:
                self.install_sdk_package('system-images;android-%s;android-wear;%s'
                                         % (api, avd_config.abi))
            elif 'tv' in avd_config.tag:
                self.install_sdk_package('system-images;android-%s;android-tv;%s'
                                         % (api, avd_config.abi))
            elif 'car' in avd_config.tag:
                self.install_sdk_package('system-images;android-%s;android-car;%s'
                                         % (api, avd_config.abi))
            elif 'chromeos' in avd_config.tag:
                self.update_chromeos(avd_config.alt_version)
            else:
                self.install_sdk_package('system-images;android-%s;default;%s'
                                         % (api, avd_config.abi))
            self.m_logger.info('Attempt number 2 at AVD creation now that package has been attempted to be installed.')
            ret = try_create_with_sdk()
        # last step, create config.ini
        if ret != 0:
            self.m_logger.error('Failed to create AVD, even after attempting package install.')
        return ret

if emu_argparser.emu_args.config_file is None:
    sys.exit(-1)
else:
    emu_test.utils.emu_testcase.create_test_case_from_file(
        'launch_avd', CreateAndLaunchAVDTest, CreateAndLaunchAVDTest.launch_avd)


if __name__ == '__main__':
    os.environ['SHELL'] = '/bin/bash'
    emu_argparser.emu_args = emu_argparser.get_parser().parse_args()
    log.info(emu_argparser.emu_args)
    sys.argv[1:] = emu_argparser.emu_args.unittest_args
    unittest.main()