import argparse
import json

emu_args = None

def get_parser():
    parser = argparse.ArgumentParser(description='Argument parser for emu test')

    parser.add_argument('-t', '--timeout', type=int, dest='timeout_in_seconds', action='store',
                        default=600,
                        help='an integer for timeout in seconds, default is 600')
    parser.add_argument('-l', '--loglevel', type=str, dest='loglevel', action='store',
                        choices=['DEBUG' , 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], default='INFO',
                        help='set the log level, default is INFO')
    parser.add_argument('-avd', type=str, nargs='+', dest='avd_list', action='store',
                        default=None,
                        help='run test for given AVD, support multiple avd separated by space')
    parser.add_argument('-b', type=int, dest='expected_boot_time', action='store',
                        default=600,
                        help='expected boot time in seconds, default is 600')
    parser.add_argument('-exec', type=str, dest='emulator_exec', action='store',
                        default='emulator',
                        help='path of emulator executable, default is system emulator')
    parser.add_argument('-s', type=str, dest='session_dir', action='store',
                        default=None,
                        help='specify the name of the dir created to store the session files of tests If not specified, the test driver uses the timestamp as the session dir name')
    parser.add_argument('-p', type=str, dest='pattern', action='store',
                        default='test*.py',
                        help='regex file name pattern for inclusion in the test suite')
    parser.add_argument('-c', type=str, dest='config_file', action='store',
                        default=None,
                        help='path to test configuration file')
    parser.add_argument('-n', type=str, dest='builder_name', action='store',
                        default=None,
                        help='builder name as appeared in config_file')
    parser.add_argument('-f', type=json.loads, dest='filter_dict', action='store',
                        default=None,
                        help='json style pattern to filter config_file')
    parser.add_argument('--skip-adb-perf', action='store_true',
                        help='when defined, skip adb performance test')
    parser.add_argument('--is-gts', action='store_true',
                        help='when defined, run gts instead of cts')
    parser.add_argument('--uitest-psc', type=str, dest='uitest_psc', action='store',
                        default=None,
                        help='test class and method for uitest presubmit check')
    parser.add_argument('--cts-plan', type=str, dest='cts_plan', action='store',
                        default=None,
                        help='The plan.xml file to use for executing CTS tests')
    parser.add_argument('--cts-dir', type=str, dest='cts_dir', action='store',
                        default=None,
                        help='specify the root directory of android cts tests, usually this ends in android-cts')
    parser.add_argument('--cts-module', type=str, dest='cts_module', action='store',
                        help='the individual cts module to execute when running the module test')
    parser.add_argument('unittest_args', nargs='*')
    return parser
