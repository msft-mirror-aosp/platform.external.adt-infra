import pytest

from emu.timing import eventually, wait_until


@pytest.mark.e2e
@pytest.mark.timeout(timeout=10, func_only=True)
def test_can_invoke_a_simple_snippet(mobly):
    mobly("animation").getFoo(5) == "foo 5"


@pytest.mark.e2e
@pytest.mark.timeout(timeout=10, func_only=True)
def test_can_use_standard_mobly_snippets(avd, mbs):
    message = "test_can_use_standard_snippets"
    mbs.logI(message)
    with avd.adb.logcat(tag="MoblyTestLog") as stream:
        assert eventually(
            lambda line: message in line, stream
        ), f"Did not see {message} on logcat"
