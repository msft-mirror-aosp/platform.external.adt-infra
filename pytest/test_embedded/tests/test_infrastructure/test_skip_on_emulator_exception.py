import pytest
from unittest.mock import patch
from emu.emulator_exceptions import EmulatorDiedException


@pytest.fixture
def fixture_fail():
    raise EmulatorDiedException("Simulated emulator death")


def test_interceptor_with_fixture_errors(fixture_fail):
    assert False, "We should not get here"


# Dummy test function that simulates an infrastructure error
def test_interceptor_with_infra_error():
    raise EmulatorDiedException("Simulated emulator death")


# Dummy test function that raises a different type of exception
@pytest.mark.xfail
def test_interceptor_with_other_error():
    raise ValueError("Some other error")


@pytest.mark.xfail
def test_interceptor_with_assert_fail():
    assert False, "Wrong! Do it again"
