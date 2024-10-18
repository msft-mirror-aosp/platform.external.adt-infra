import pytest
from pytest_crashretry.retry_plugin import ForceRetryException

attempt = 0
fixture_attempt = 0


@pytest.fixture
def first_force_retry():
    global fixture_attempt
    fixture_attempt += 1
    if fixture_attempt == 1:
        raise ForceRetryException("Fixture failure, please try again!")


@pytest.mark.crash_flake(retries=2, delay=1)
def test_force_fixture_retry(first_force_retry):
    assert True, "woohoo"


@pytest.mark.crash_flake(retries=2, delay=1)
def test_force_retry():
    global attempt
    attempt += 1
    if attempt == 1:
        raise ForceRetryException("Test failure, please try again!")

    assert True, "woohoo"
