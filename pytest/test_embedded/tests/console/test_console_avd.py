import logging
import pytest
from pathlib import Path


@pytest.mark.boot
@pytest.mark.console
@pytest.mark.e2e
@pytest.mark.timeout(timeout=300, func_only=True)
@pytest.mark.flaky(reruns=3, reruns_delay=5)  # b/278273476 flaky on linux_x64.
def test_avd_canonical_path(emulator, avd):
    """Test adb emu avd path returns a canonical path"""

    path = Path(emulator.android_avd_home, f"{emulator.configuration.name}.avd")
    expected_path = f"{path.absolute()}"

    result = [x.rstrip() for x in avd.adb.run(["emu", "avd", "path"]).splitlines()]
    logging.info("adb avd path returned '%s'", result)
    assert expected_path in result


@pytest.mark.boot
@pytest.mark.console
@pytest.mark.e2e
@pytest.mark.timeout(timeout=300, func_only=True)
@pytest.mark.flaky(reruns=3, reruns_delay=5)
def test_avd_dir_is_canonical_in_pid_xxx_ini(emulator, avd):
    """Test pid_xxx.ini contains canonical path for avd.dir

    example:
    avd.dir=/Users/me/.android/avd/x.avd
    """

    path = Path(emulator.android_avd_home, f"{emulator.configuration.name}.avd")
    expected_path = f"{path.absolute()}"

    result = [x.rstrip() for x in avd.adb.run(["emu", "avd", "discoverypath"]).splitlines()]
    pid_path = result[-2].rstrip() # Last line should be OK
    avd_dir = ""
    with open(pid_path) as f:
        for line in f:
            if "avd.dir" in line:
                avd_dir = line.split("=", 2)[1].rstrip()
                logging.info("found avd_dir as %s", avd_dir)
                break

    assert avd_dir == expected_path
