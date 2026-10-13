"""Reports the Tradefed results of a run_local.bat or run_external.bat run to Bazel and Sponge.

On gLinux and macOS run_local.sh and run_external.sh are Bazel tests, so Bazel
uploads their JUnit XML, log and outputs to Sponge. On Windows run_local.bat and
run_external.bat drive the emulator and Tradefed outside of Bazel, so they end
with report_to_sponge.bat, which runs this test on their output directory:

  bazel test --config=rcache --config=sponge --nocache_test_results \\
      --zip_undeclared_test_outputs --test_arg=--out_dir=<out\\ets_ui\\timestamp> \\
      @goldfish_test//ets/ui:report_results

It converts every results\\<timestamp>\\test_result.xml below --out_dir into the
JUnit XML Bazel expects in XML_OUTPUT_FILE (what the sequencer's
junit_xml_result agents do in the :ui sequence), copies the emulator log,
Tradefed logs, videos and screenshots into TEST_UNDECLARED_OUTPUTS_DIR
(outputs.zip in Fusion; --config=rcache makes Bazel upload these files), and
fails the way check_tradefed_results.ps1 does: when fewer than --min_results
result files exist, a module did not complete or a test failed.
"""

import argparse
import datetime
import os
import pathlib
import shutil
import sys
import xml.etree.ElementTree as ET


def _parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--out_dir",
        required=True,
        type=pathlib.Path,
        help="Output directory of a run_local.bat run (out\\ets_ui\\<timestamp>).",
    )
    parser.add_argument(
        "--min_results",
        type=int,
        default=1,
        help="Minimum number of test_result.xml files expected below --out_dir.",
    )
    return parser.parse_args(argv)


def _junit_suites(result_file, result, problems):
    """Converts the <Module>s of a Tradefed <Result> into JUnit <testsuite>s."""
    suites = []
    start_ms = int(result.get("start", "0"))
    timestamp = datetime.datetime.fromtimestamp(start_ms / 1000).isoformat(timespec="seconds")
    for module in result.iter("Module"):
        module_name = module.get("name", "unknown")
        suite = ET.Element(
            "testsuite",
            name=module_name,
            package=result.get("suite_name", ""),
            hostname=result.get("host_name", ""),
            timestamp=timestamp,
            time="%.3f" % (int(module.get("runtime", "0")) / 1000),
        )
        tests = failures = skipped = errors = 0
        for test_case in module.iter("TestCase"):
            class_name = test_case.get("name", module_name)
            for test in test_case.iter("Test"):
                tests += 1
                test_name = test.get("name", "unknown")
                case = ET.SubElement(suite, "testcase", classname=class_name, name=test_name)
                outcome = test.get("result", "")
                if test.get("skipped") == "true" or outcome in ("IGNORED", "ASSUMPTION_FAILURE"):
                    skipped += 1
                    ET.SubElement(case, "skipped", message=outcome)
                    print("  SKIPPED %s#%s (%s)" % (class_name, test_name, outcome))
                elif outcome == "pass":
                    if any(m.get("key") == "is_flaky" for m in test.iter("Metric")):
                        ET.SubElement(case, "system-out").text = "passed after a retry (is_flaky)"
                        print("  PASSED  %s#%s (after a retry)" % (class_name, test_name))
                    else:
                        print("  PASSED  %s#%s" % (class_name, test_name))
                else:
                    failures += 1
                    failure = test.find("Failure")
                    message = failure.get("message", "") if failure is not None else ""
                    trace = failure.findtext("StackTrace", "") if failure is not None else ""
                    ET.SubElement(case, "failure", message=message or outcome).text = trace
                    print("  FAILED  %s#%s: %s" % (class_name, test_name, message or outcome))
        if module.get("done") != "true":
            errors += 1
            message = "module %s did not complete" % module_name
            case = ET.SubElement(suite, "testcase", classname=module_name, name="module completed")
            ET.SubElement(case, "error", message=message)
            problems.append("%s: %s" % (result_file, message))
        suite.set("tests", str(tests))
        suite.set("failures", str(failures))
        suite.set("skipped", str(skipped))
        suite.set("errors", str(errors))
        suites.append(suite)
    return suites


def _report(result_file, problems):
    """Prints the summary of one test_result.xml and returns its JUnit suites."""
    result = ET.parse(result_file).getroot()
    summary = result.find("Summary")
    if summary is None:
        problems.append("%s: no <Summary> element" % result_file)
        return []
    passed = int(summary.get("pass", "0"))
    failed = int(summary.get("failed", "0"))
    modules_done = int(summary.get("modules_done", "0"))
    modules_total = int(summary.get("modules_total", "0"))
    print(
        "%s: suite %s, pass=%d failed=%d modules=%d/%d"
        % (result_file, result.get("suite_name", "?"), passed, failed, modules_done, modules_total)
    )
    if failed > 0:
        problems.append("%s: %d test(s) failed" % (result_file, failed))
    if passed < 1:
        problems.append("%s: no test passed" % result_file)
    if modules_done != modules_total:
        problems.append("%s: %d of %d modules completed" % (result_file, modules_done, modules_total))
    return _junit_suites(result_file, result, problems)


def _copy_outputs(out_dir):
    """Copies the run's outputs into TEST_UNDECLARED_OUTPUTS_DIR (outputs.zip in Sponge)."""
    undeclared_dir = os.environ.get("TEST_UNDECLARED_OUTPUTS_DIR")
    if not undeclared_dir:
        print("TEST_UNDECLARED_OUTPUTS_DIR is not set, not copying %s" % out_dir)
        return
    shutil.copytree(out_dir, undeclared_dir, dirs_exist_ok=True)
    print("Copied %s into TEST_UNDECLARED_OUTPUTS_DIR" % out_dir)


def _write_junit_xml(suites):
    xml_output_file = os.environ.get("XML_OUTPUT_FILE")
    if not xml_output_file:
        print("XML_OUTPUT_FILE is not set, not writing JUnit XML")
        return
    root = ET.Element("testsuites")
    root.extend(suites)
    tree = ET.ElementTree(root)
    ET.indent(tree)
    tree.write(xml_output_file, encoding="utf-8", xml_declaration=True)
    print("Wrote %s" % xml_output_file)


def main(argv):
    args = _parse_args(argv)
    out_dir = args.out_dir.resolve()
    if not out_dir.is_dir():
        print("%s is not a directory" % out_dir)
        return 1

    problems = []
    # Tradefed names the result directories after the invocation time; skip its "latest" link.
    result_files = sorted(p for p in out_dir.rglob("test_result.xml") if p.parent.name != "latest")
    print("%d test_result.xml file(s) under %s" % (len(result_files), out_dir))
    if len(result_files) < args.min_results:
        problems.append(
            "expected at least %d test_result.xml file(s) under %s, found %d"
            % (args.min_results, out_dir, len(result_files))
        )
    suites = []
    for result_file in result_files:
        suites.extend(_report(result_file, problems))
    if problems and not suites:
        # Give the invocation a test case that carries the failure.
        suite = ET.Element("testsuite", name="tradefed", tests="1", failures="1", skipped="0", errors="0")
        case = ET.SubElement(suite, "testcase", classname="tradefed", name="results")
        ET.SubElement(case, "failure", message="; ".join(problems))
        suites.append(suite)

    _write_junit_xml(suites)
    _copy_outputs(out_dir)
    if problems:
        print("FAILED:")
        for problem in problems:
            print("  " + problem)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
