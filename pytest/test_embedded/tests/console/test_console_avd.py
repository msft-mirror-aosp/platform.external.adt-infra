from pathlib import Path

import pytest


@pytest.mark.boot
@pytest.mark.console
@pytest.mark.fast
@pytest.mark.e2e
@pytest.mark.timeout(timeout=10, func_only=True)
def test_avd_canonical_path(emulator, avd, telnet):
    """Test adb emu avd path returns a canonical path"""
    expected_path = Path(
        emulator.android_avd_home, f"{emulator.configuration.name}.avd"
    ).absolute()

    assert str(expected_path) in telnet.send("avd path")


@pytest.mark.boot
@pytest.mark.console
@pytest.mark.e2e
@pytest.mark.timeout(timeout=10, func_only=True)
def test_avd_tracing_is_mounted(emulator, avd, telnet):
    """Test adb shell ls /sys/kernel/tracing/trace_marker valid"""

    no_file = "No such file or directory"
    if no_file in emulator.adb.shell("ls /sys/kernel/tracing/trace_marker"):
        assert no_file not in emulator.adb.shell(
            "ls /sys/kernel/debug/tracing/trace_marker"
        )


def read_property_file(from_file) -> str:
    """Reads a property file and returns a dictionary of the key-value pairs.

    Args:
        from_file: The filename of the property file.

    Returns:
        A dictionary of the key-value pairs in the property file.
    """
    with open(from_file, "r", encoding="utf-8") as f:
        return dict([x.strip().split("=", 2) for x in f.readlines()])


@pytest.mark.boot
@pytest.mark.console
@pytest.mark.e2e
@pytest.mark.timeout(timeout=10, func_only=True)
def test_avd_dir_is_canonical_in_pid_xxx_ini(avd, telnet):
    """Test pid_xxx.ini contains canonical path for avd.dir

    example:
    avd.dir=/Users/me/.android/avd/x.avd
    """
    pid_path = Path(telnet.send("avd discoverypath")[0])
    assert (
        pid_path.exists()
    ), f"We expect the reported discovery path: {pid_path} to exist"

    props = read_property_file(pid_path)
    assert "avd.dir" in props, f"Did not find 'avd.dir' in {props}"

    expected_path = Path(
        avd.android_avd_home, f"{avd.configuration.name}.avd"
    ).absolute()
    assert props["avd.dir"] == str(expected_path)
