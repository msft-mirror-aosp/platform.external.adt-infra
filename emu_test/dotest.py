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
import glob
from pathlib import Path


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
    gradle_report_path = Path(emu_args.session_dir) / emu_args.test_dir

    xml_report_filepath = gradle_report_path / 'test_report.xml'
    html_report_filepath = gradle_report_path / 'test_report.html'
    xslt_filepath = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                                'utils', 'asHtml.xslt' )
    write_xml_report(emu_args)

    # Generate the HTML file
    if not xml_report_filepath.exists():
        logger.info("Couldn't find the XML test suites report.")
        return

    parser = LET.XMLParser(huge_tree=True)
    lxml_tree = LET.parse(xml_report_filepath, parser=parser)
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


def write_xml_report(emu_args):
    """Write a XML test suites report

    Args:
        emu_args (argparse.Namespace): parsed command-line arguments
    """
    logger = logging.getLogger()
    logger.info("Write XML test suites report")

    gradle_report_path = Path(emu_args.session_dir) / emu_args.test_dir
    if not gradle_report_path.exists():
         logger.info('Failed to find gradle report path.')
         return

    xml_files = sorted(Path(gradle_report_path).glob('*.xml'))
    if not xml_files:
        logger.info('No gradle XML reports found.')
        return

    xml_report_filepath = gradle_report_path / 'test_report.xml'
    session_name = ''.join(emu_args.session_dir.split('/')[3:4]) \
                                   .replace('git_devtools-','')

    xml_report = ET.Element('testsuites')
    xml_report_testsuite = ET.SubElement(xml_report, 'testsuite')
    xml_report_testsuite.set('name', session_name)
    errors = tests = failures = skipped = times = 0

    for xml_file in xml_files:
        try:
            tree = ET.parse(xml_file)
        except ET.ParseError as err:
            logger.info('Xml parser ' + err.msg + ' (' + xml_file.name + ')')
            continue
        testsuite = tree.getroot()
        tests += int(testsuite.get('tests', 0))
        errors += int(testsuite.get('errors', 0))
        failures += int(testsuite.get('failures', 0))
        skipped += int(testsuite.get('skipped', 0))
        times += float(testsuite.get('time', 0.))

        classname = testsuite.get('name').split('.')[-1]
        logcat_path = xml_file.with_name(xml_file.stem + '_logcat.txt')
        test_details_path = xml_file.with_name(xml_file.stem + '_details')
        test_log_path = test_details_path / classname
        testcases = sorted(testsuite.findall('./testcase'),
                            key=lambda child: child.get('name'))

        # Parse the XML file containing the ignored tests of the current test class
        ignored_testcases_report = test_log_path / 'ignored_tests.xml'
        if ignored_testcases_report.exists():
            try:
                ignored_testcases_tree = ET.parse(ignored_testcases_report)
                ignored_testcases = ignored_testcases_tree.getroot()
            except ET.ParseError as err:
                logger.info(f"Error parsing XML file '{ignored_testcases_report}': {err}")
                ignored_testcases= None

        for testcase in testcases:
            testcase.set('classname', testcase.get('classname') \
                                              .replace('com.android.devtools.', ''))
            testcase.set('logcat', logcat_path.name)
            testcase_log_path = test_log_path / testcase.get('name')

            if xml_report.find('properties') is None:
                # Append the properties of the first test class to the main xml report
                properties = ET.SubElement(xml_report, 'properties')
                testsuite_properties = testsuite.findall('./properties/property')
                [properties.append(property) for property in testsuite_properties]

            # For ignored testcases, add the ignore reason as the 'message' property
            skipped_element = testcase.find('./skipped')
            if skipped_element is not None and ignored_testcases:
                ignore_reason_xpath = '/'.join(['ignoredTest',
                                                f"[methodName='{testcase.get('name')}']",
                                                'ignoreReason'])
                ignore_reason = ignored_testcases.find(ignore_reason_xpath)
                skipped_element.set('message', ignore_reason.text)

            if testcase_log_path.exists():
                # Add 'xml' and 'png' reports that may have been pulled.
                testcase_hierarchies = ET.SubElement(testcase, 'hierarchies')
                testcase_screenshots = ET.SubElement(testcase, 'screenshots')
                for report in testcase_log_path.glob('*'):
                    if report.suffix == '.xml':
                        hierarchy = ET.SubElement(testcase_hierarchies, 'hierarchy')
                        hierarchy.set('name', report.name)
                        # Include hierarchy file contents
                        with open(report, "r", encoding="utf-8") as hierarchy_file:
                            contents = hierarchy_file.read()
                            # hierachy.set('xml-content', contents)
                            hierarchy.text = contents
                    elif report.suffix == '.png':
                        screenshot = ET.SubElement(testcase_screenshots, 'screenshot')
                        screenshot.set('name', report.name)
                        # Add base64 encoding of the image
                        with open(report, "rb") as img:
                            base64enc = base64.b64encode(img.read())
                            screenshot.set('base64', base64enc.decode('utf-8'))

            add_logcat(testcase, logcat_path)  # Add logcat info to the testcase tree.
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


def add_logcat(testcase: ET, logcat_file: Path):
    """Add logcat information to the testcase tree.

    Args:
        testcase (xml.etree.ElementTree.Element): testcase element tree.
        logcat_file (Path): path to the logcat (class) file.

    Notes:
        The default behavior of the AndroidJUnit4 XML renderer is to omit
        writing stdout output for passed tests in the XML JUnit reports.
        This method adds a new XML element, system-out, to test_report.xml
        for passed test cases and test cases not included in ignored_testcases.
        Only log entries of types log_levels are written.
    """
    subelements = set([child.tag for child in testcase])
    ignored_testcases = {'failure', 'error', 'skipped'}
    if subelements & ignored_testcases:
        # Don't add logcat info to testcases types in `ignored_testcases`
        return

    logcat_content = ''
    if not logcat_file.exists():
        logging.warning(f"Couldn't find logcat file '{logcat_file.stem}'")
        return

    with open(logcat_file, 'r') as file:
        logcat_content = file.read()

    log_levels = 'IWE'  # Debug (D), Error (E), Info (I), Warning (W), Verbose (V).
    name = testcase.get('name')
    start_tag = f'TestRunner: started: {name}'
    end_tag = f'TestRunner: finished: {name}'
    testcase_regex = re.compile(fr'(?sm)^[^\n]+{re.escape(start_tag)}.*?{re.escape(end_tag)}')
    match = testcase_regex.search(logcat_content)

    if match:
        entries = match.group().strip().split('\n')
        logcat_pattern = re.compile(r'^\S+\s+\S+\s+\d+\s+\d+\s+[' + log_levels + ']\s+.*')
        # Filter entries that match `log_level`
        filtered_entries = [entry for entry in entries if logcat_pattern.search(entry)]
        ET.SubElement(testcase, 'system-out').text = '\n'.join(filtered_entries)
    else:
        logging.warning(f"Couldn't find entries for test '{name}' in file '{logcat_file}'")


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
    logging.info("Test complete with exit code {int(not emuResult.wasSuccessful())}")
    sys.exit(not emuResult.wasSuccessful())
