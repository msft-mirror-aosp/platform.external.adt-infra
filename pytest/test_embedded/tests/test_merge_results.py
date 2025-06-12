#!/usr/bin/env python3
import xml.etree.ElementTree as ET
from pathlib import Path
import tempfile
import shutil
from emuxml.merge_results import merge_results

def create_test_xml(name, test_cases, output_path):
    """Creates a test XML file with the given test cases.

    Args:
        name: Name of the test suite
        test_cases: List of tuples (test_name, status, message)
                   where status is 'passed', 'failed', or 'error'
        output_path: Path to write the XML file
    """
    root = ET.Element("testsuites")
    suite = ET.SubElement(root, "testsuite", {
        "name": name,
        "tests": str(len(test_cases)),
        "failures": str(sum(1 for _, status, _ in test_cases if status == 'failed')),
        "errors": str(sum(1 for _, status, _ in test_cases if status == 'error')),
        "time": "1.0",
        "hostname": "test-host",
        "timestamp": "2024-01-01T00:00:00"
    })

    for test_name, status, message in test_cases:
        case = ET.SubElement(suite, "testcase", {
            "name": test_name,
            "classname": "test_class",
            "time": "0.1"
        })
        if status == 'failed':
            failure = ET.SubElement(case, "failure", {"message": message})
            failure.text = message
        elif status == 'error':
            error = ET.SubElement(case, "error", {"message": message})
            error.text = message

    tree = ET.ElementTree(root)
    tree.write(output_path, encoding='utf-8', xml_declaration=True)

def verify_merged_results(tree, expected_results):
    """Verifies that the merged results match the expected outcomes.

    Args:
        tree: ElementTree of the merged results
        expected_results: Dict mapping test names to expected status ('passed', 'failed', 'error')
    """
    suite = tree.getroot().find("testsuite")
    actual_results = {}

    for case in suite.findall("testcase"):
        test_name = case.attrib["name"]
        if case.find("failure") is not None:
            actual_results[test_name] = 'failed'
        elif case.find("error") is not None:
            actual_results[test_name] = 'error'
        else:
            actual_results[test_name] = 'passed'

    # Verify results
    mismatches = []
    for test_name, expected_status in expected_results.items():
        actual_status = actual_results.get(test_name)
        if actual_status != expected_status:
            mismatches.append(f"Test {test_name}: Expected {expected_status}, got {actual_status}")

    return mismatches

def test_merge_results_with_retries():
    """Test that merge_results correctly handles test retries."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Test scenario 1: Test that passes on retry
        create_test_xml("first_run", [
            ("test1", "failed", "First run failure"),
            ("test2", "passed", ""),
        ], temp_path / "first.xml")

        create_test_xml("retry", [
            ("test1", "passed", ""),  # Same test, now passing
            ("test3", "passed", ""),  # New test
        ], temp_path / "second.xml")

        # Test scenario 2: Test that fails on retry
        create_test_xml("first_run2", [
            ("test4", "passed", ""),
            ("test5", "passed", ""),
        ], temp_path / "third.xml")

        create_test_xml("retry2", [
            ("test4", "failed", "Failed on retry"),
            ("test6", "error", "New error"),
        ], temp_path / "fourth.xml")

        # Merge the results
        merged_tree = merge_results([
            str(temp_path / "first.xml"),
            str(temp_path / "second.xml"),
            str(temp_path / "third.xml"),
            str(temp_path / "fourth.xml"),
        ])

        # Define expected results
        expected_results = {
            "test1": "passed",    # Should be passed (overridden by retry)
            "test2": "passed",    # Should remain passed
            "test3": "passed",    # Should be passed (new test)
            "test4": "failed",    # Should be failed (overridden by retry)
            "test5": "passed",    # Should remain passed
            "test6": "error",     # Should be error (new test)
        }

        # Verify results
        mismatches = verify_merged_results(merged_tree, expected_results)
        assert not mismatches, "\n".join(mismatches)

def test_merge_results_empty_files():
    """Test that merge_results handles empty test files correctly."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create an empty test file
        create_test_xml("empty", [], temp_path / "empty.xml")

        # Merge the results
        merged_tree = merge_results([str(temp_path / "empty.xml")])

        # Verify results
        suite = merged_tree.getroot().find("testsuite")
        assert suite is not None
        assert int(suite.attrib["tests"]) == 0
        assert int(suite.attrib["failures"]) == 0
        assert int(suite.attrib["errors"]) == 0

def test_merge_results_single_file():
    """Test that merge_results handles a single file correctly."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create a single test file
        create_test_xml("single", [
            ("test1", "passed", ""),
            ("test2", "failed", "Failure message"),
        ], temp_path / "single.xml")

        # Merge the results
        merged_tree = merge_results([str(temp_path / "single.xml")])

        # Verify results
        expected_results = {
            "test1": "passed",
            "test2": "failed",
        }
        mismatches = verify_merged_results(merged_tree, expected_results)
        assert not mismatches, "\n".join(mismatches)