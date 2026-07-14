#!/usr/bin/env python3
import sys
import os
import xml.etree.ElementTree as ET

def main():
    if len(sys.argv) < 2:
        print("Usage: parse_results.py <sponge_id_dir>")
        sys.exit(1)

    sponge_dir = sys.argv[1]
    if not os.path.isdir(sponge_dir):
        print(f"Error: {sponge_dir} is not a directory.")
        sys.exit(1)

    passed_tests = []
    failed_tests = []

    # Find all test_result.xml recursively
    for root, dirs, files in os.walk(sponge_dir):
        for file in files:
            if file == 'test_result.xml':
                file_path = os.path.join(root, file)
                print(f"Parsing {file_path}...")
                try:
                    tree = ET.parse(file_path)
                    root_elem = tree.getroot()
                    for module in root_elem.findall('.//Module'):
                        module_name = module.get('name', '')
                        for testcase in module.findall('.//TestCase'):
                            class_name = testcase.get('name', '')
                            for test in testcase.findall('.//Test'):
                                test_name = test.get('name', '')
                                result = test.get('result', '')
                                test_id = f"{module_name} {class_name}#{test_name}"
                                if result == 'pass':
                                    passed_tests.append(test_id)
                                elif result == 'fail':
                                    failed_tests.append(test_id)
                except Exception as e:
                    print(f"Error parsing {file_path}: {e}")

    # Deduplicate and sort
    passed_tests = sorted(list(set(passed_tests)))
    failed_tests = sorted(list(set(failed_tests)))

    passed_file_path = os.path.join(sponge_dir, "passed.txt")
    failed_file_path_txt = os.path.join(sponge_dir, "failed.txt")

    print(f"Writing {len(passed_tests)} passed tests to {passed_file_path}")
    with open(passed_file_path, "w") as f:
        for t in passed_tests:
            f.write(t + "\n")

    print(f"Writing {len(failed_tests)} failed tests to {failed_file_path_txt}")

    with open(failed_file_path_txt, "w") as f_txt:
        for t in failed_tests:
            f_txt.write(t + "\n")

    print("Parsing completed.")

if __name__ == "__main__":
    main()
