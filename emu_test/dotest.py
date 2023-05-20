#!/usr/bin/env python

"""
A simple testing framework for emulator using python's unit testing framework.

Type:

./dotest.py -h

for available options.
"""

import sys
import os
import unittest
import logging
import re
import time
import psutil
import traceback
from subprocess import PIPE, check_call, CalledProcessError
import xml.etree.ElementTree as ET
import lxml.etree as LET
import base64


# Add parent directory to current module. Then, emu_test module is recognized.
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)),
                             os.pardir))
from emu_test.utils import emu_argparser
from emu_test.utils import emu_unittest
from emu_test.utils import path_utils

# Provides a regular expression for matching fail message
TIMEOUT_REGEX = re.compile(r"(^\d+)([smhd])?$")
RESULT_XML_FILE = 'test_{}.xml'

def print_xml(emu_result):
    def getTestName(id):
        return id.rsplit('.', 1)[-1]
    result = ET.Element('testsuite', name='BootTest')
    result.set('tests', str(emu_result.testsRun))
    result.set('failures', str(len(emu_result.failures)+len(emu_result.errors)))

    for x in emu_result.passes:
        ET.SubElement(result, 'testcase', name=getTestName(x.id()),
                      test_result='pass')

    for x in emu_result.failures:
        testcase = ET.SubElement(result, 'testcase',
                                 name=getTestName(x[0].id()),
                                 test_result='fail')
        failure = ET.SubElement(testcase, 'failure')
        failure.text = getattr(x[0].failureException, '__doc__', 'failed')

    for x in emu_result.errors:
        testcase = ET.SubElement(result, 'testcase',
                                 name=getTestName(x[0].id()),
                                 test_result='error')
        error = ET.SubElement(testcase, 'failure')
        error.text = getattr(x[0].failureException, '__doc__', 'failed')

    for x in emu_result.expectedFailures:
        ET.SubElement(result, 'testcase',
                      name=getTestName(x[0].id()),
                      test_result='expected failure')

    for x in emu_result.unexpectedSuccesses:
        ET.SubElement(result, 'testcase',
                      name=getTestName(x.id()),
                      test_result='unexpected failure')

    xml_string_result = ET.tostring(result)
    # Saves each avd testing result to global variable: g_xml_string_result
    g_xml_string_result = xml_string_result

    dst_path = os.path.join(emu_argparser.emu_args.session_dir,
                            emu_argparser.emu_args.test_dir,
                            RESULT_XML_FILE.format(emu_argparser.emu_args.test_dir))

    with open(dst_path, 'w+') as modified:
        modified.write('%s' % g_xml_string_result.decode())

def printResult(result):
    """
    Prints out the results of the emulator test into the logger.
    :param result: class python2.7.unittest.TextTestResult.
    """
    def getTestName(id):
        testname = re.sub('_google_apis.*','', id.rsplit('.', 1)[-1])
        return re.sub('_android-(wear|tv|car).*', '', testname)

    logging.getLogger().info("Test Summary")
    logging.getLogger().info("Run %d tests (%d pass, %d fail, %d error, %d xfail, %d xpass)",
                     result.testsRun, len(result.passes), len(result.failures), len(result.errors),
           len(result.expectedFailures), len(result.unexpectedSuccesses))
    if len(result.errors) > 0 or len(result.failures) > 0:
        for x in result.errors:
            if x[1].splitlines()[-1] == "TimeoutError":
                logging.getLogger().info("TIMEOUT: %s", getTestName(x[0].id()))
            else:
                logging.getLogger().info("ERROR: %s", getTestName(x[0].id()))
        for x in result.failures:
            logging.getLogger().info("FAIL: %s", getTestName(x[0].id()))

    if len(result.passes) > 0:
        logging.getLogger().info('------------------------------------------------------')
    for x in result.passes:
        logging.getLogger().info("PASS: %s, boot time: %s", getTestName(x.id()), x.boot_time)

    if len(result.expectedFailures) > 0:
        logging.getLogger().info('------------------------------------------------------')
    for x in result.expectedFailures:
        logging.getLogger().info("Expected Failure: %s", getTestName(x[0].id()))

    if len(result.unexpectedSuccesses) > 0:
        logging.getLogger().info('------------------------------------------------------')
    for x in result.unexpectedSuccesses:
        logging.getLogger().info("Unexpected Success: %s", getTestName(x.id()))

    logging.getLogger().info('')
    logging.getLogger().info("Test successful - %s", result.wasSuccessful())

    if emu_argparser.emu_args.generate_xml:
        logging.getLogger().info("Write XML report")
        print_xml(result)


def printTestBreakdown(emu_args):
    """
    Print out detailed testcase information for each class.
    """
    logger = logging.getLogger()
    gradle_report_path = os.path.join(emu_args.session_dir, emu_args.test_dir)

    if not os.path.exists(gradle_report_path):
        logger.info('Failed to find gradle report path.')
        return

    xml_files = []
    for filename in os.listdir(gradle_report_path):
        if filename.endswith('.xml'):
            xml_files += [os.path.join(gradle_report_path, filename)]
    if not xml_files:
        logger.info('No gradle XML reports found.')
        return

    logger.info('\nTestsuite breakdown:\n')

    # Parse XML reports
    tests, passes, failures, errors, skips, times = [], [], [], [], [], []

    for xml_file in sorted(xml_files):
        try:
            tree = ET.parse(xml_file)
        except ET.ParseError as err:
            logger.warning("{} in file '{}'".format(err.msg, xml_file))
            continue
        testsuite = tree.getroot()
        classname = testsuite.get('name', '')
        test = int(testsuite.get('tests', 0))
        failure = int(testsuite.get('failures', 0))
        error = int(testsuite.get('errors', 0))
        skip = int(testsuite.get('skipped', 0))
        pass_ = test - sum([error, failure, skip])
        time_class = ''
        if testsuite.get('time'):
            time_class = ', duration {:.2f}s'.format(float(testsuite.get('time')))

        logger.info('---------------------------')
        logger.info('Class "{}"'.format(classname.replace('com.android.devtools.','')))
        logger.info('Run {} tests ({} pass, {} failures, {} errors, {} skipped{})\n'\
                        .format(test, pass_, failure, error, skip, time_class))

        testcases = sorted(testsuite.findall('./testcase'),
                           key=lambda child: child.get('name'))

        for testcase in testcases:
            if testcase.findall('./failure'):
                status = 'FAILED'
            elif testcase.findall('./error'):
                status = 'ERROR'
            elif testcase.findall('./skipped'):
                status = 'SKIPPED'
            else:
                status = 'PASSED'
            time_case = ''
            if testcase.get('time'):
                time_case = ', duration {:.2f}s'.format(float(testcase.get('time')))

            logger.info('{}: {}{}'.format(status, testcase.get('name'), time_case))

        tests.append(test)
        passes.append(pass_)
        failures.append(failure)
        errors.append(error)
        skips.append(skip)
        times.append(float(testcase.get('time')) if testcase.get('time') else 0)

    logger.info('-------------')
    logger.info('Testsuite summary\n')
    total_time = ', duration {:.2f}s'.format(sum(times)) if sum(times) > 0. else ''
    logger.info('Run {} tests ({} pass, {} failures, {} errors, {} skipped{})\n'\
                    .format(sum(tests), sum(passes), sum(failures),
                            sum(errors), sum(skips), total_time))

def printHtml(emu_args):
    """Generate a HTML report for all testcases
    """
    logger = logging.getLogger()
    logger.info("Write HTML report")
    gradle_report_path = os.path.join(emu_args.session_dir, emu_args.test_dir)

    if not os.path.exists(gradle_report_path):
        logger.info('Failed to find gradle report path.')
        return
    xml_files = []
    for filename in os.listdir(gradle_report_path):
        if filename.endswith('.xml'):
            xml_files += [os.path.join(gradle_report_path, filename)]
    if not xml_files:
        logger.info('No gradle XML reports found.')
        return

    xml_report_filepath = os.path.join(gradle_report_path, 'test_report.xml')
    html_report_filepath = os.path.join(gradle_report_path, 'test_report.html')
    xslt_filepath = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                                'utils', 'asHtml.xslt' )
    xml_report_name = ''.join(emu_args.session_dir.split('/')[3:4]).\
                                                replace('git_devtools-','')

    # Create the xml tree and append individual testcases
    xml_report = ET.Element('testsuites')
    xml_report_testsuite = ET.SubElement(xml_report, 'testsuite')
    xml_report_testsuite.set('name', xml_report_name)
    errors = tests = failures = skipped = times = 0
    for xml_file in sorted(xml_files):
        try:
            tree = ET.parse(xml_file)
        except ET.ParseError as err:
            logger.info('Xml parser ' + err.msg + ' (' + os.path.basename(xml_file) + ')')
            continue
        testsuite = tree.getroot()
        tests += int(testsuite.get('tests', 0))
        errors += int(testsuite.get('errors', 0))
        failures += int(testsuite.get('failures', 0))
        skipped += int(testsuite.get('skipped', 0))
        times += float(testsuite.get('time', 0.))

        classname = testsuite.get('name').split('.')[-1]
        available_report_folders = next(os.walk(gradle_report_path))[1]
        detailed_report_folder = [folder for folder in available_report_folders \
                                        if classname in folder and '_details' in folder]
        testcases = sorted(testsuite.findall('./testcase'),
                            key=lambda child: child.get('name'))
        for testcase in testcases:
            testcase.set('classname', testcase.get('classname').\
                                                replace('com.android.devtools.', ''))
            # Add 'xml' and 'png' files that may exist in the '_detais' folder.
            if detailed_report_folder:
                testcase_reports_relpath = os.path.join(detailed_report_folder[0],
                                                        classname, testcase.get('name'))
                testcase_reports_path = os.path.join(gradle_report_path,
                                                     testcase_reports_relpath)
                if os.path.exists(testcase_reports_path):
                    testcase_hierarchies = ET.SubElement(testcase, 'hierarchies')
                    testcase_screenshots = ET.SubElement(testcase, 'screenshots')

                    for filename in os.listdir(testcase_reports_path):
                        report_relpath = os.path.join(testcase_reports_relpath, filename)
                        if filename.endswith('.xml'):
                            hierachy = ET.SubElement(testcase_hierarchies, 'hierarchy')
                            hierachy.set('name', filename)
                            hierachy.set('path', report_relpath)
                        elif filename.endswith('.png'):
                            screenshot = ET.SubElement(testcase_screenshots, 'screenshot')
                            screenshot.set('name', filename)
                            screenshot.set('path', report_relpath)
                            # Add base64 encode
                            imgpath = os.path.join(testcase_reports_path, filename)
                            with open(imgpath, "rb") as img:
                                base64enc = base64.b64encode(img.read())
                                screenshot.set('base64', base64enc.decode('utf-8'))

            xml_report_testsuite.append(testcase)

    xml_report_testsuite.set('tests', str(tests))
    xml_report_testsuite.set('passed', str(tests - errors - failures - skipped))
    xml_report_testsuite.set('failures', str(failures))
    xml_report_testsuite.set('errors', str(errors))
    xml_report_testsuite.set('skipped', str(skipped))
    xml_report_testsuite.set('time', '{:.2f}'.format(times))

    # Write test_report.xml
    xml_tree = ET.ElementTree(xml_report)
    xml_tree.write(xml_report_filepath, xml_declaration=True, encoding='UTF-8')

    # Generate the HTML file
    lxml_tree = LET.parse(xml_report_filepath)
    xslt = LET.parse(xslt_filepath)
    try:
        transform = LET.XSLT(xslt)
        html_result = transform(lxml_tree)
    except Exception as err:
        logging.warning("Failed to generate file '%s' from '%s' due to error '%s'.",
                            os.path.basename(xml_report_filepath),
                            os.path.basename(xslt_filepath), err)
    else:
        html_result.write(html_report_filepath)
        logger.info("Created file '%s'", html_report_filepath)


def setupLogger():
    """
    Create logging.getLogger() that will be used by test driver
    """
    log_formatter = logging.Formatter('%(message)s')
    file_name = 'main_%s.log' % time.strftime("%Y%m%d-%H%M%S")
    if emu_argparser.emu_args.session_dir is None:
        emu_argparser.emu_args.session_dir = time.strftime("%Y%m%d-%H%M%S")
    if not os.path.exists(emu_argparser.emu_args.session_dir):
        os.makedirs(emu_argparser.emu_args.session_dir)
    if emu_argparser.emu_args.test_dir is None:
        emu_argparser.emu_args.test_dir = 'testcase_%s' % time.strftime("%Y%m%d-%H%M%S")
    test_path = os.path.join(emu_argparser.emu_args.session_dir,
                             emu_argparser.emu_args.test_dir)
    if not os.path.exists(test_path):
        os.makedirs(test_path)

    file_handler = logging.FileHandler(os.path.join(test_path, file_name))

    file_handler.setFormatter(log_formatter)
    # Test summary goes to standard error, since we rely on stderr to parse test results in buildbot
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(log_formatter)

    logging.getLogger().addHandler(file_handler)
    logging.getLogger().addHandler(console_handler)
    logging.getLogger().setLevel(getattr(logging, emu_argparser.emu_args.loglevel.upper()))
    logging.getLogger().info("Logger created and active.")


def findSystemAVDs():
    """
    Find available AVDs in system.  Found my calling -list-avds on target emulator.
    """
    # avd is searched in the order of $ANDROID_AVD_HOME,$ANDROID_SDK_HOME/.android/avd and $HOME/.android/avd
    avd_list_proc = psutil.Popen([emu_argparser.emu_args.emulator_exec, "-list-avds"], stdout=PIPE, stderr=PIPE)
    (output, err) = avd_list_proc.communicate()
    logging.getLogger().debug(output)
    logging.getLogger().debug(err)
    avd_list = [x.strip() for x in output.splitlines()]
    logging.getLogger().info("Found %d AVDs - %s", len(avd_list), avd_list)
    return avd_list


if __name__ == '__main__':
    """
    Main Execution.  For the passed arguments (held in emu_argparser) perform the requested tests.
    We find our test cases by searching for the passed in --file_pattern from the script execution directory.
    For instance, for a boot test we search for files named test_boot.*py, which we will find under
    test_boot/boot_test.py.  So this testcase would be found and run.

    When testcases are finished, we manually kill the ADB server.  This ensures a couple things:
      1.  It ensures our next test is run with a fresh daemon.  We are not testing ADB in these tests.
      2.  It ensures we do not hold up Buildbot code by holding on to a child process, blocking slave return.
    """
    os.environ["SHELL"] = "/bin/bash"
    # Make sure that ANDROID_SDK_ROOT and ANDROID_AVD_HOME env are defined
    if "ANDROID_SDK_ROOT" not in os.environ:
        logging.error("Please define ANDROID_SDK_ROOT")
        sys.exit(1)
    if "ANDROID_AVD_HOME" not in os.environ:
        logging.error("Please define ANDROID_AVD_HOME")
        sys.exit(1)

    try:
        emu_argparser.emu_args = emu_argparser.get_parser().parse_args()
        setupLogger()
        logging.getLogger().info(emu_argparser.emu_args)

        if not emu_argparser.emu_args.use_device and emu_argparser.emu_args.avd_list is None:
            emu_argparser.emu_args.avd_list = findSystemAVDs()

        test_root_dir = os.path.dirname(os.path.realpath(__file__))
        emuSuite = unittest.TestLoader().discover(start_dir=test_root_dir, pattern=emu_argparser.emu_args.pattern)
        emuRunner = emu_unittest.EmuTextTestRunner(stream=sys.stdout)
        emuResult = emuRunner.run(emuSuite)
        printResult(emuResult)
        printTestBreakdown(emu_argparser.emu_args)
        if emu_argparser.emu_args.generate_html:
            printHtml(emu_argparser.emu_args)
    except Exception:
        logging.exception("Error in dotest.py")

    # Always attempt to kill the adb server.  We are now done testing with it.
    try:
        logging.info("Try to kill adb server")
        adb_binary = path_utils.get_adb_binary()
        check_call([adb_binary, 'kill-server'], stdout=PIPE, stdin=PIPE)
        logging.info("adb server killed")
    except CalledProcessError:
        logging.exception("Error shutting down adb")
    logging.info("Test complete")
    sys.exit(not emuResult.wasSuccessful())
