import logging
import pytest
from pathlib import Path


@pytest.mark.boot
@pytest.mark.e2e
@pytest.mark.timeout(timeout=300, func_only=True)
def test_avd_canonical_path(emulator, avd):
    """ Test adb emu avd path returns a canonical path

    """

    path = Path(emulator.android_avd_home, f"{emulator.configuration.name}.avd")
    expected_path = f"{path.absolute()}"

    result = avd.adb.run(["emu","avd", "path"]).rstrip()
    got_path = result[:-2].rstrip() # get rid of "\nOK"
    got_path = got_path.rstrip("'") # get rid of enclosing single quote on windows
    got_path = got_path.lstrip("'")

    logging.info("adb avd path returned '%s'", got_path)
    assert got_path == expected_path

