# This file will parse all xml files in the UI_TEST_* subdirectories under the main directory, summarizing the results
# Usage: python parse_xml_results.py <test_logs_directory>

import sys
from xml.dom import minidom
from os import listdir
from os.path import isfile, isdir, join

testLogsDirectory = sys.argv[1]

uiTestDirectories = [join(testLogsDirectory, dirName) for dirName in listdir(testLogsDirectory)
                     if isdir(join(testLogsDirectory, dirName)) and dirName.startswith("UI_TEST_")]

loopedDictionary = {}
testCount = 0
runCount = 0
passCount = 0
failCount = 0
for uiTestDirectory in uiTestDirectories:
    testResultsFiles = [join(uiTestDirectory, fileName) for fileName in listdir(uiTestDirectory)
                        if isfile(join(uiTestDirectory, fileName))
                        and fileName.startswith("test_") and fileName.endswith(".xml")]
    if len(testResultsFiles) > 0:
        runCount = runCount + 1
        for testResultsFile in testResultsFiles:
            testResultsDoc = minidom.parse(testResultsFile)
            testSuiteElements = testResultsDoc.getElementsByTagName('testsuite')[0]
            testSuite = str(testSuiteElements.attributes['name'].value)
            numTests = int(testSuiteElements.attributes['tests'].value)
            numSkipped = int(testSuiteElements.attributes['skipped'].value)
            testCount = testCount + int(numTests) - numSkipped

            passedTests = []
            failedTests = []
            skippedTests = []
            testCaseElements = testResultsDoc.getElementsByTagName('testcase')
            for testCaseElement in testCaseElements:
                failureTag = testCaseElement.childNodes
                if len(failureTag) > 0:
                    failedTests.append(str(testCaseElement.attributes['name'].value) + ":" + str(runCount))
                    failCount = failCount + 1
                else:
                    passedTests.append(str(testCaseElement.attributes['name'].value) + ":" + str(runCount))
                    passCount = passCount + 1

            if testSuite in loopedDictionary:
                loopedDictionary[testSuite]['passedTests'].extend(passedTests)
                loopedDictionary[testSuite]['failedTests'].extend(failedTests)
            else:
                testDictionary = {testSuite:
                                  {'passedTests': passedTests, 'failedTests': failedTests}}
                loopedDictionary.update(testDictionary)
print("\nTesting Results in " + testLogsDirectory)
print("Execution Looped " + str(runCount) + " Times")
for uiTestSuite, uiTestResults in loopedDictionary.iteritems():
    passedTests = uiTestResults['passedTests']
    failedTests = uiTestResults['failedTests']
    passedTests.sort()
    failedTests.sort()
    numPassed = len(passedTests)
    numFailed = len(failedTests)
    numTests = numPassed + numFailed
    print("\nTest Suite: " + uiTestSuite)
    print("=======================================")
    print("Number of Tests Passed: " + str(numPassed) + "/" + str(numTests))
    print("Number of Tests Failed: " + str(numFailed) + "/" + str(numTests))
    print("=======================================")
    print("\nPassed Tests:")
    if numPassed > 0:
        print('\n'.join(passedTests))
    else:
        print('None')
    print("\nFailed Tests:")
    if numFailed > 0:
        print('\n'.join(failedTests))
    else:
        print('None')
    print("---------------------------------------")

print ("\nAnalyzed " + str(testCount/runCount) + " Tests from " + testLogsDirectory)
print ("Looped " + str(runCount) + " Times for " + str(testCount) + " Total Tests")
print (str(passCount) + " Tests Passed and " + str(failCount) + " Tests Failed") 
