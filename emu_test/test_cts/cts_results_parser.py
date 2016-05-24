#!/usr/bin/python

import xml.etree.ElementTree as ET


databaseColumns = [
        'BuildId', 'BuildDate',  # file name
        'PackageName', 'AppPackageName', 'ABI',  # TestPackage
        'TestSuiteName',  # TestSuite
        'TestCaseName',  # TestCase
        'TestName', 'Result',  # Test
]


def _InsertRow(result, row):
    result.append(row)


def _ExtractTest(test, row, result):
    row['TestName'] = test.attrib.get('name', '')
    row['Result'] = test.attrib.get('result', '')
    _InsertRow(result, row)


def _ExtractTestCase(testCase, row, result):
    row['TestCaseName'] = testCase.attrib.get('name', '')
    for test in [x for x in testCase if x.tag == 'Test']:
        _ExtractTest(test, dict(row), result)


def _ExtractSuite(suite, row, result):
    if row['TestSuiteName'] != '':
        row['TestSuiteName'] += '.'
    row['TestSuiteName'] += suite.attrib.get('name', '__')
    # Order of these for-loops is significant
    for testCase in [x for x in suite if x.tag == 'TestCase']:
        _ExtractTestCase(testCase, dict(row), result)
    for child in [x for x in suite if x.tag == 'TestSuite']:
        _ExtractSuite(child, dict(row), result)


def _ExtractPackage(package, row, result):
    row['PackageName'] = package.attrib.get('name', '')
    row['AppPackageName'] = package.attrib.get('appPackageName', '')
    row['ABI'] = package.attrib.get('abi', '')
    row['TestSuiteName'] = ''
    for suite in [x for x in package if x.tag == 'TestSuite']:
        _ExtractSuite(suite, dict(row), result)


def ExtractResults(ctsFilePath):
    result = []
    tree = ET.parse(ctsFilePath)
    root = tree.getroot()
    for package in root.findall('TestPackage'):
        _ExtractPackage(package, {}, result)
    return result
