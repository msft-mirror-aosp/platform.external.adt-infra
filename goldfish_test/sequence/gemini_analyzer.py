# Copyright 2026 - The Android Open Source Project
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
import fnmatch
import logging
import os
import xml.etree.ElementTree as ET

from sequence.gemini_client import GeminiClient


def analyze_failures(results_dir: str):
    """
    Scans the results directory for XML files, identifies test failures (supports
    both JUnit and Tradefed formats), retrieves corresponding logcat logs,
    queries Gemini for explanations, and appends the explanations.
    """
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
        )

    logging.info(f"Starting Gemini failure analysis in: {results_dir}")
    xml_files = []

    # Add the primary Bazel test result XML if available
    bazel_xml = os.getenv("XML_OUTPUT_FILE")
    if bazel_xml and os.path.exists(bazel_xml):
        logging.info(f"Adding Bazel XML_OUTPUT_FILE to analysis: {bazel_xml}")
        xml_files.append(bazel_xml)

    for root, _, files in os.walk(results_dir):
        for file in files:
            if file.endswith(".xml"):
                xml_files.append(os.path.join(root, file))

    if not xml_files:
        logging.info("No XML files found to analyze.")
        return

    client = None
    try:
        client = GeminiClient()
    except Exception as e:
        logging.error(f"Failed to initialize GeminiClient: {e}. Skipping analysis.")
        return

    for xml_path in xml_files:
        logging.info(f"Parsing XML: {xml_path}")

        # Read the first line to check if it contains the XML declaration
        # and preserve it exactly (including stylesheet PIs)
        xml_header = ""
        try:
            with open(xml_path, "r", encoding="utf-8", errors="ignore") as f:
                first_line = f.readline()
                if first_line.strip().startswith("<?xml"):
                    xml_header = first_line
                    if not xml_header.endswith("\n"):
                        xml_header += "\n"
        except Exception as e:
            logging.warning(f"Failed to read XML header from {xml_path}: {e}")

        try:
            tree = ET.parse(xml_path)
            root_el = tree.getroot()
        except ET.ParseError as e:
            logging.error(f"Failed to parse XML file {xml_path}: {e}")
            continue

        parent_map = {c: p for p in tree.iter() for c in p}
        failures_found = False

        # Detect Format
        # JUnit has <testcase> tags, Tradefed has <Test> tags.
        has_junit = len(list(root_el.iter("testcase"))) > 0
        has_tradefed = len(list(root_el.iter("Test"))) > 0

        if not has_junit and not has_tradefed:
            logging.info(
                f"XML file format not recognized as JUnit or Tradefed: {xml_path}"
            )
            continue

        if has_junit:
            logging.info(f"Processing JUnit format XML: {xml_path}")
            for testcase in root_el.iter("testcase"):
                failure_el = testcase.find("failure")
                if failure_el is None:
                    continue

                failures_found = True
                classname = testcase.attrib.get("classname", "")
                test_name = testcase.attrib.get("name", "")
                failure_msg = failure_el.attrib.get("message", "")
                stacktrace = failure_el.text or ""

                _process_single_failure(
                    classname,
                    test_name,
                    failure_msg,
                    stacktrace,
                    failure_el,
                    xml_path,
                    client,
                )

        elif has_tradefed:
            logging.info(f"Processing Tradefed format XML: {xml_path}")
            for test_el in root_el.iter("Test"):
                if test_el.attrib.get("result") != "fail":
                    continue
                failure_el = test_el.find("Failure")
                if failure_el is None:
                    continue

                failures_found = True
                test_name = test_el.attrib.get("name", "")
                failure_msg = failure_el.attrib.get("message", "")

                stacktrace_el = failure_el.find("StackTrace")
                stacktrace = ""
                if stacktrace_el is not None:
                    stacktrace = stacktrace_el.text or ""
                else:
                    stacktrace = failure_el.text or ""

                classname = ""
                parent_testcase = parent_map.get(test_el)
                if parent_testcase is not None and parent_testcase.tag == "TestCase":
                    classname = parent_testcase.attrib.get("name", "")

                target_el = stacktrace_el if stacktrace_el is not None else failure_el
                _process_single_failure(
                    classname,
                    test_name,
                    failure_msg,
                    stacktrace,
                    target_el,
                    xml_path,
                    client,
                )

        if failures_found:
            try:
                if xml_header:
                    with open(xml_path, "wb") as f:
                        f.write(xml_header.encode("utf-8"))
                        tree.write(f, encoding="utf-8", xml_declaration=False)
                else:
                    tree.write(xml_path, encoding="utf-8", xml_declaration=False)
                logging.info(
                    f"Successfully updated XML with Gemini explanations: {xml_path}"
                )
            except Exception as e:
                logging.error(f"Failed to write updated XML to {xml_path}: {e}")


def _process_single_failure(
    classname: str,
    test_name: str,
    failure_msg: str,
    stacktrace: str,
    target_el: ET.Element,
    xml_path: str,
    client: GeminiClient,
):
    logging.info(f"Processing failure: {classname}#{test_name}")
    suite_name = classname.split(".")[-1]

    # Locate logs directory
    xml_dir = os.path.dirname(xml_path)
    parent_dir_name = os.path.basename(xml_dir)

    logcat_content = ""
    if parent_dir_name.endswith(".results"):
        logs_dir_name = parent_dir_name.replace(".results", ".logs")
        logs_dir = os.path.join(os.path.dirname(xml_dir), logs_dir_name)

        if os.path.exists(logs_dir):
            logcat_content = _find_and_read_logcat(logs_dir, suite_name)
        else:
            logging.warning(f"Expected logs directory does not exist: {logs_dir}")
    else:
        logging.info(
            f"XML parent dir '{parent_dir_name}' does not end with '.results'. Searching sibling folders."
        )
        # Fallback: search the sibling folders of results directory
        logs_dir = xml_dir.replace("results", "logs")
        if os.path.exists(logs_dir):
            logcat_content = _find_and_read_logcat(logs_dir, suite_name)

    if not logcat_content:
        logging.warning(
            f"Could not retrieve logcat content for {classname}#{test_name}"
        )

    # Call Gemini
    logging.info(f"Querying Gemini for {test_name} failure analysis...")
    prompt = _build_prompt(
        classname, test_name, failure_msg, stacktrace, logcat_content
    )
    try:
        explanation = client.get_generated_text(prompt)
        _append_explanation(target_el, explanation)
    except Exception as e:
        logging.error(f"Gemini API call failed: {e}")


def _find_and_read_logcat(logs_dir: str, suite_name: str) -> str:
    """
    Searches the logs directory for logcat files matching the suite name.
    Falls back to any logcat file if none match the suite name.
    """
    logcat_files = []
    for root, _, files in os.walk(logs_dir):
        for file in files:
            if "logcat" in file and file.endswith(".txt"):
                logcat_files.append(os.path.join(root, file))

    if not logcat_files:
        logging.warning(f"No logcat files found in {logs_dir}")
        return ""

    # Try to find file containing suite_name (e.g. CallTest)
    matched_file = None
    for file_path in logcat_files:
        if suite_name in os.path.basename(file_path):
            matched_file = file_path
            break

    if not matched_file:
        # Fallback to the first logcat file found
        matched_file = logcat_files[0]
        logging.info(
            f"No logcat matched suite '{suite_name}'. Using fallback: {matched_file}"
        )
    else:
        logging.info(
            f"Found matching logcat file for suite '{suite_name}': {matched_file}"
        )

    try:
        with open(matched_file, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception as e:
        logging.error(f"Failed to read logcat file {matched_file}: {e}")
        return ""


def _build_prompt(
    classname: str,
    test_name: str,
    failure_msg: str,
    stacktrace: str,
    logcat_content: str,
) -> str:
    logcat_section = logcat_content if logcat_content else "No logcat output available."
    return f"""You are an expert Android test engineer. Explain why the following emulator test failed.

Test Class: {classname}
Test Name: {test_name}
Failure Message: {failure_msg}
Stacktrace:
{stacktrace}

Here is the complete logcat output:
--- LOGCAT START ---
{logcat_section}
--- LOGCAT END ---

Provide a concise explanation of the root cause and how to fix it under 150 words.
"""


def _append_explanation(failure_el: ET.Element, explanation: str):
    """Appends Gemini's explanation to the text content of the failure element."""
    original_text = failure_el.text or ""
    separator = (
        "\n\n======================================================================\n"
    )
    header = "GEMINI FAILURE ANALYSIS:\n"
    footer = (
        "\n======================================================================\n"
    )

    new_text = f"{original_text}{separator}{header}{explanation}{footer}"
    failure_el.text = new_text
