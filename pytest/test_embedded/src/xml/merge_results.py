# Copyright 2020 - The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def merge_results_multiple_suites(xml_files):
    """Merge all the tests files into multiple suites."""
    suites = []
    for file_name in xml_files:
        config_name = Path(file_name).stem
        tree = ET.parse(file_name)
        test_suite = tree.getroot().find("testsuite")
        test_suite.attrib["name"] = config_name
        suites.append(test_suite)
        for case in test_suite.findall("testcase"):
            case.attrib["classname"] = f"{config_name}.{case.get('classname', '')}"

    new_root = ET.Element("testsuites")
    for suite in suites:
        new_root.append(suite)

    return ET.ElementTree(new_root)


def merge_results(xml_files):
    """Merges al the test results into a single xml as a single suite that we can present."""
    failures = 0
    tests = 0
    errors = 0
    time = 0.0
    cases = []
    hostname = ""
    timestamp = None
    names = []

    for file_name in xml_files:
        config_name = Path(file_name).stem
        names.append(config_name)
        tree = ET.parse(file_name)
        test_suite = tree.getroot().find("testsuite")
        if not timestamp:
            timestamp = test_suite.attrib.get("timestamp", "unknown")

        hostname = test_suite.attrib.get("hostname", "unknown")
        failures += int(test_suite.attrib["failures"])
        tests += int(test_suite.attrib["tests"])
        errors += int(test_suite.attrib["errors"])
        time += float(test_suite.attrib["time"])
        for case in test_suite.findall("testcase"):
            case.attrib["classname"] = f"{config_name}.{case.get('classname', '')}"
            cases.append(case)

    new_root = ET.Element("testsuites")
    test_suite = ET.SubElement(
        new_root,
        "testsuite",
        attrib={
            "name": "_".join(names),
            "failures": f"{failures}",
            "tests": f"{tests}",
            "errors": f"{errors}",
            "time": f"{time}",
            "hostname": hostname,
            "timestamp": timestamp,
        },
    )
    for case in cases:
        test_suite.append(case)

    return ET.ElementTree(new_root)


def launch():
    """Parse the command line arguments and launch the transformation."""
    parser = argparse.ArgumentParser(
        description="Merge a series of junit xml files into one."
    )
    parser.add_argument(
        "--out", help="The (optional) output file where the result will be written to"
    )
    parser.add_argument(
        "xml", nargs="*", help="The list of junit xml files that are to be merged"
    )
    parser.add_argument(
        "--single",
        default=False,
        action="store_true",
        help="Merge into a singlue suite",
    )

    args = parser.parse_args()

    out = sys.stdout.buffer
    if args.out:
        out = open(args.out, "wb")

    if args.single:
        new_tree = merge_results_multiple_suites(args.xml)
    else:
        new_tree = merge_results(args.xml)

    new_tree.write(out, encoding="utf-8")
    out.flush()


if __name__ == "__main__":
    launch()
