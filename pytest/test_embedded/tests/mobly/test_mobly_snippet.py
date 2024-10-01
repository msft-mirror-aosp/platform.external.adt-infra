import pytest

from emu.timing import eventually



def test_can_invoke_a_simple_snippet(mobly):
    mobly("animation").getFoo(5) == "foo 5"



async def test_can_use_standard_mobly_snippets(avd, mbs):
    message = "test_can_use_standard_snippets"
    mbs.logI(message)
    async with await avd.adb.logcat(tag="MoblyTestLog") as stream:
        assert await eventually(
            lambda line: message in line, stream
        ), f"Did not see {message} on logcat"
