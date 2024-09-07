import logging
import sys
from pathlib import Path
from time import sleep
from traceback import format_exception
from typing import Generator, List, Optional


from io import StringIO
import pytest
from _pytest.logging import caplog_records_key
from _pytest.terminal import TerminalReporter

from pytest_crashretry.crashreporter import CrashReporter
from pytest_crashretry.configs import Defaults


outcome_key = pytest.StashKey[str]()
attempts_key = pytest.StashKey[int]()
duration_key = pytest.StashKey[float]()
server_port_key = pytest.StashKey[int]()
stages = ("setup", "call", "teardown")
RETRY = 0
FAIL = 1
EXIT = 2
PASS = 3


class Reporter:
    def __init__(self) -> None:
        self.stream = StringIO()

    def record_attempt(self, lines: list[str]) -> None:
        self.stream.writelines(lines)


class ConfigurationError(Exception):
    pass


class RetryManager:
    """
    Stores statistics and reports for crash_flake tests and fixtures which have
    failed at least once during the test session and need to be retried
    """

    def __init__(self, config: pytest.Config) -> None:
        self.reporter: Reporter = Reporter()
        self.trace_limit: Optional[int] = 1
        self.node_stats: dict[str, dict] = {}
        self.messages = (
            " failed on attempt {attempt}! Retrying!\n\t",
            " failed after {attempt} attempts!\n\t",
            " teardown failed on attempt {attempt}! Exiting immediately!\n\t",
            " passed on attempt {attempt}!\n\t",
        )
        self.crash_reporter: CrashReporter = self.get_crash_reporter(config)
        self.log_file = config.getoption("--log-file")

    def get_crash_reporter(self, config: pytest.Config) -> CrashReporter:
        exe = config.getoption("emulator")
        emulator_directory = Path(exe).parent if exe else None
        return CrashReporter(emulator_directory, config.getoption("symbols"), None)

    def crash_reports(self) -> List[str]:
        return self.crash_reporter.list_crashes()

    def write_crash_reports(self):
        if not self.log_file or not Path(self.log_file).exists():
            return

        log_dir = Path(self.log_file).parent
        self.crash_reporter.write_reports_to_disk(log_dir)

    def log_attempt(
        self, attempt: int, name: str, exc: Optional[pytest.ExceptionInfo], result: int
    ) -> None:
        message = self.messages[result].format(attempt=attempt)
        formatted_trace = ""
        if exc:
            err = (exc.type, exc.value, exc.tb)
            formatted_trace = (
                formatted_trace.join(format_exception(*err, limit=self.trace_limit))
                .replace("\n", "\n\t")
                .rstrip()
            )
        self.reporter.record_attempt([f"\t{name}", message, formatted_trace, "\n\n"])

    def build_retry_report(self, terminal_reporter: TerminalReporter) -> None:
        contents = self.reporter.stream.getvalue()
        if not contents:
            return

        terminal_reporter.write("\n")
        terminal_reporter.section(
            "the following tests were retried", sep="=", bold=True, yellow=True
        )
        terminal_reporter.write(contents)
        terminal_reporter.section("end of test retry report", sep="=", bold=True, yellow=True)
        terminal_reporter.write("\n")

    def record_node_stats(self, report: pytest.TestReport) -> None:
        self.node_stats[report.nodeid]["outcomes"][report.when].append(report.outcome)
        self.node_stats[report.nodeid]["durations"][report.when].append(report.duration)

    def simple_outcome(self, item: pytest.Item) -> str:
        """
        Return failed if setup, teardown, or final call outcome is 'failed'
        Return skipped if test was skipped
        """
        test_outcomes = self.node_stats[item.nodeid]["outcomes"]
        for outcome in ("skipped", "failed"):
            if outcome in test_outcomes["setup"]:
                return outcome
        if not test_outcomes["call"] or test_outcomes["call"][-1] == "failed":
            return "failed"
        # can probably just simplify this to return test_outcomes["teardown"] as a fallthrough
        if "failed" in test_outcomes["teardown"]:
            return "failed"
        return "passed"

    def simple_duration(self, item: pytest.Item) -> float:
        """
        Return total duration for test summing setup, teardown, and final call
        """
        return sum(self.node_stats[item.nodeid]["durations"][stage][-1] for stage in stages)

    def sum_attempts(self, item: pytest.Item) -> int:
        return len(self.node_stats[item.nodeid]["outcomes"]["call"])


retry_manager: RetryManager = None


def should_handle_retry(call: pytest.CallInfo) -> bool:
    """Determines whether a test should be retried if it failed and an emulator
    crashreport is present.

    Args:
        call: A pytest.CallInfo object containing information about the test execution.

    Returns:
        True if the test should be retried, False otherwise.

    This function checks for crashes, success, test stage, and skipped status to
    decide whether to retry the test. It also handles crash report management.
    """

    crashes = retry_manager.crash_reports()
    if crashes:
        retry_manager.write_crash_reports()
        retry_manager.clear()

    # Success?
    if call.excinfo is None:
        return False
    # if teardown stage, don't retry
    # may handle fixture setup retries in v2 if requested. For now, this is fine.
    if call.when in {"setup", "teardown"}:
        return False

    # if test was skipped, don't retry
    if call.excinfo.typename == "Skipped":
        return False

    # Retry if there crashes
    return crashes


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item: pytest.Item) -> Optional[object]:
    retry_manager.node_stats[item.nodeid] = {
        "outcomes": {k: [] for k in stages},
        "durations": {k: [0.0] for k in stages},
    }
    yield
    item.stash[outcome_key] = retry_manager.simple_outcome(item)
    item.stash[duration_key] = retry_manager.simple_duration(item)  # always overwrite, for now
    item.stash[attempts_key] = retry_manager.sum_attempts(item)


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(
    item: pytest.Item, call: pytest.CallInfo
) -> Generator[None, pytest.TestReport, None]:
    outcome = yield
    original_report: pytest.TestReport = outcome.get_result()
    retry_manager.record_node_stats(original_report)

    if not should_handle_retry(call):
        return

    # Set dynamic outcome for each stage until runtest protocol has completed
    item.stash[outcome_key] = original_report.outcome

    flake_mark = item.get_closest_marker("crash_flake")
    retries = flake_mark.kwargs.get("crash_retries", Defaults.CRASH_RETRIES)
    delay = flake_mark.kwargs.get("crash_delay", Defaults.CRASH_RETRY_DELAY)
    cumulative_timing = flake_mark.kwargs.get(
        "crash_cumulative_timing", Defaults.CRASH_CUMULATIVE_TIMING
    )
    attempts = 1
    hook = item.ihook

    while True:
        # Default teardowns are already excluded, so this must be the `call` stage
        # Try preliminary teardown using a fake class to ensure every local fixture (i.e.
        # excluding session) is torn down. Yes, including module and class fixtures
        t_call = pytest.CallInfo.from_call(
            lambda: hook.pytest_runtest_teardown(
                item=item,
                nextitem=pytest.Class.from_parent(item.session, name="FakeCrash"),
            ),
            when="teardown",
        )
        # If teardown fails, break. Flaky teardowns are unacceptable and should raise immediately
        if t_call.excinfo:
            item.stash[outcome_key] = "failed"
            retry_manager.log_attempt(
                attempt=attempts, name=item.name, exc=t_call.excinfo, result=EXIT
            )
            # Prevents a KeyError when an error during retry teardown causes a redundant teardown
            empty: dict[str, list[logging.LogRecord]] = {}
            item.stash[caplog_records_key] = empty
            break

        # If teardown passes, send report that the test is being retried
        if attempts == 1:
            original_report.outcome = "retried"  # type: ignore
            hook.pytest_runtest_logreport(report=original_report)
            original_report.outcome = "failed"
        retry_manager.log_attempt(attempt=attempts, name=item.name, exc=call.excinfo, result=RETRY)
        sleep(delay)
        # Calling _initrequest() is required to reset fixtures for a retry. Make public pls?
        item._initrequest()  # type: ignore[attr-defined]

        pytest.CallInfo.from_call(lambda: hook.pytest_runtest_setup(item=item), when="setup")
        call = pytest.CallInfo.from_call(lambda: hook.pytest_runtest_call(item=item), when="call")
        retry_report = pytest.TestReport.from_item_and_call(item, call)
        retry_manager.record_node_stats(retry_report)

        attempts += 1
        should_keep_retrying = (
            not retry_report.passed and attempts <= retries and retry_manager.crash_reports()
        )

        if not should_keep_retrying:
            original_report.outcome = retry_report.outcome
            original_report.longrepr = retry_report.longrepr
            if cumulative_timing is False:
                original_report.duration = retry_report.duration
            else:
                original_report.duration = sum(
                    retry_manager.node_stats[original_report.nodeid]["durations"]["call"]
                )

            retry_manager.log_attempt(
                attempt=attempts,
                name=item.name,
                exc=call.excinfo,
                result=FAIL if retry_report.failed else PASS,
            )
            break


def pytest_terminal_summary(terminalreporter: TerminalReporter) -> None:
    retry_manager.build_retry_report(terminalreporter)


def pytest_report_teststatus(
    report: pytest.TestReport,
) -> Optional[tuple[str, str, tuple[str, dict]]]:
    if report.outcome == "retried":
        return "retried", "R", ("RETRY", {"yellow": True})
    return None


def pytest_configure(config: pytest.Config) -> None:
    global retry_manager
    retry_manager = RetryManager(config)
    config.addinivalue_line(
        "markers",
        "crash_flake(retries=1, delay=0, only_on=..., exclude=..., condition=...): indicate a crash_flake "
        "test which will be retried the number of times specified with an (optional) specified "
        "delay between each attempt. "
        "Any statement which returns a bool can be used as a condition",
    )
    verbosity = config.getoption("verbose")
    if verbosity:
        # set trace limit according to verbosity count, or unlimited if 5
        retry_manager.trace_limit = verbosity if verbosity < 5 else None
    Defaults.configure(config)


CRASH_RETRIES_HELP_TEXT = "number of times to retry failed tests. Defaults to 0."
DELAY_HELP_TEXT = "configure a delay (in seconds) between retries."
TIMING_HELP_TEXT = "if True, retry duration will be included in overall reported test duration"


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup(
        "crash-retry",
        "retry tests that crash the emulator to compensate for intermittent failures",
    )
    group.addoption(
        "--crash-retries",
        action="store",
        dest="crash_retries",
        type=int,
        help=CRASH_RETRIES_HELP_TEXT,
    )
    group.addoption(
        "--crash-retry-delay",
        action="store",
        dest="crash_retry_delay",
        type=float,
        help=DELAY_HELP_TEXT,
    )
    group.addoption(
        "--crash-cumulative-timing",
        action="store",
        dest="crash_cumulative_timing",
        type=bool,
        help=TIMING_HELP_TEXT,
    )
    parser.addini("crash_retries", CRASH_RETRIES_HELP_TEXT, default=0, type="string")
    parser.addini("crash_retry_delay", DELAY_HELP_TEXT, default=0, type="string")
    parser.addini("crash_cumulative_timing", TIMING_HELP_TEXT, default=False, type="bool")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    retries = None
    retries = config.getoption("--crash-retries")
    if retries is None:
        retries = config.getini("crash_retries")

    if not retries:
        return

    crash_flake = pytest.mark.crash_flake(retries=Defaults.CRASH_RETRIES)
    for item in items:
        if "crash_flake" not in item.keywords:
            item.add_marker(crash_flake)
