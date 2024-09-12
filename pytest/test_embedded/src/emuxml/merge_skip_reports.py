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
import json
import logging
import platform
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def merge_skip_reports(xml_files, cfg_dir):
    """Merge all testsuites skip reports into a single xml report.

    Args:
        xml_files ([Path]): List of xml skip reports that are to be merged.

    Returns:
        xml.etree.ElementTree: skip report xml merged tree
    """
    testsuites = ET.Element("testsuites")
    alltests = {}
    for xml_file in xml_files:
        try:
            tree = ET.parse(xml_file)
        except ET.ParseError as err:
            logging.info("Xml parser " + err.msg + " (" + xml_file.name + ")")
            continue
        testsuite = tree.getroot()
        testsuites.append(testsuite)
        for platform_ in testsuite.findall("./platforms/platform"):
            os_ = platform_.get("name")
            alltests.setdefault(os_, {})
            for test in platform_.findall(".//test"):
                nodeid = test.find("./nodeid").text
                name = test.find("./name").text
                reason = test.find("./reason").text
                test_data = {"name": name, "reason": reason if reason else ""}
                alltests[os_].setdefault(nodeid, test_data)

    # Create element 'all_testsuites'
    all_testsuites = ET.SubElement(testsuites, "all_testsuites")
    all_platforms = ET.SubElement(all_testsuites, "platforms")
    fullname_map = {
        "win": "Windows",
        "linux": "Linux",
        "mac": "Mac Intel",
        "m1": "Mac M1",
        "all": "All platforms",
    }

    for os_, tests in alltests.items():
        tests = dict(sorted(tests.items()))
        xml_platform = ET.SubElement(all_platforms, "platform")
        xml_platform.set("name", os_)
        xml_platform.set("fullname", fullname_map.get(os_, "Unknonw"))
        for nodeid, test in tests.items():
            xml_test = ET.SubElement(xml_platform, "test")
            ET.SubElement(xml_test, "nodeid").text = nodeid
            for property in ["name", "reason"]:
                ET.SubElement(xml_test, property).text = test[property]

    # Create element 'skipped_testsuites'
    platforms = list(
        dict.fromkeys([platform.system()] + ["Linux", "Darwin", "Windows"]).keys()
    )
    skipped_testsuites = {}
    for plat in platforms:
        emulator_config = Path(cfg_dir / f"emulator_{plat.lower()}_tests.json")
        with open(emulator_config, "r", encoding="utf-8") as file:
            config_json = json.load(file)
            for name, testsuite in config_json.items():
                if testsuite["status"] == "disabled":
                    skipped_testsuites.setdefault(plat, [])
                    skipped_testsuites[plat].append(name)

    if skipped_testsuites:
        skipped_testsuites_xml = ET.SubElement(testsuites, "skipped_testsuites")
        platforms_ = ET.SubElement(skipped_testsuites_xml, "platforms")
        for plat, testsuites_list in skipped_testsuites.items():
            platform_ = ET.SubElement(platforms_, "platform")
            platform_.set("name", plat)
            testsuites_ = ET.SubElement(platform_, "testsuites")
            for name in testsuites_list:
                testsuite_ = ET.SubElement(testsuites_, "testsuite")
                testsuite_.set("name", name)

    return ET.ElementTree(testsuites)


def launch():
    """Parse the command line arguments and launch the transformation."""
    parser = argparse.ArgumentParser(
        description="Merge a series of skipped tests xml reports into one."
    )
    parser.add_argument(
        "--out", help="The (optional) output file where the result will be written to"
    )
    parser.add_argument(
        "--cfg", help="Directory containing the configuration files"
    )
    parser.add_argument(
        "xml", nargs="*", help="The list of xml skip reports that are to be merged"
    )

    args = parser.parse_args()

    out = sys.stdout.buffer
    if args.out:
        out = open(args.out, "wb")

    new_tree = merge_skip_reports(args.xml, Path(args.cfg))
    new_tree.write(
        out,
        encoding="utf-8",
        xml_declaration=True,
    )
    out.flush()


if __name__ == "__main__":
    launch()
