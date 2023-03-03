import pytest
import time
import sys
import logging
from emu.timing import TimeoutExceptionTrigger
from emu.process.command import Command, TimeoutKillProcessTrigger


def test_timeout_raises():
    start = time.time()

    with pytest.raises(TimeoutError):
        with TimeoutExceptionTrigger(0.5):
            for i in range(0, 20):
                time.sleep(0.1)
            assert False, "The timeout is 1 second, so this should not happen"

    # Should have escaped fast enough..
    assert time.time() - start < 1


@pytest.fixture
def sleep_time():
    return lambda time_in_seconds: (
        ["timeout", str(time_in_seconds)]
        if sys.platform == "win32"
        else ["sleep", str(time_in_seconds)]
    )


def test_timeout_proc_terminates(sleep_time, caplog):
    """The sleep command should be forcefully terminated by our external kill mechanism."""
    start = time.time()

    caplog.set_level(logging.DEBUG)
    proc = Command(sleep_time(20)).run()
    with TimeoutKillProcessTrigger(proc.pid, timeout=1):
        proc.wait(timeout=20)

    # We got killed by our external observer
    assert "Killing" in caplog.text
    assert time.time() - start < 2


def test_timeout_proc_finishes_does_not_terminate(sleep_time, caplog):
    """We should exit normally."""
    start = time.time()

    caplog.set_level(logging.DEBUG)
    proc = Command(sleep_time(1)).run()
    with TimeoutKillProcessTrigger(proc.pid, timeout=2):
        proc.wait(timeout=20)

    # We did not get  killed by our external observer
    assert "Killing" not in caplog.text
    assert time.time() - start < 2
