from pathlib import Path

import pytest


@pytest.mark.boot
@pytest.mark.console
@pytest.mark.fast
@pytest.mark.e2e
@pytest.mark.async_timeout(10)
async def test_avd_canonical_path(emulator, avd, telnet):
    """Test adb emu avd path returns a canonical path"""
    expected_path = Path(
        emulator.android_avd_home, f"{emulator.configuration.name}.avd"
    ).absolute()
    path = await telnet.send("avd path")
    assert str(expected_path) in path


@pytest.mark.boot
@pytest.mark.console
@pytest.mark.fast
@pytest.mark.e2e
@pytest.mark.async_timeout(10)
async def test_avd_snapshots_path_has_no_dots(telnet):
    """Exposes b/299320133, paths should be normalized."""
    path = await telnet.send("avd snapshotspath")
    assert ".." not in path[0]


@pytest.mark.boot
@pytest.mark.console
@pytest.mark.e2e
@pytest.mark.async_timeout(10)
async def test_avd_tracing_is_mounted(emulator, avd, telnet):
    """Test adb shell ls /sys/kernel/tracing/trace_marker valid"""
    no_file = "No such file or directory"
    ls_file = await emulator.adb.shell("ls /sys/kernel/tracing/trace_marker")
    if no_file in ls_file:
        ls_file = await emulator.adb.shell("ls /sys/kernel/debug/tracing/trace_marker")
        assert no_file not in ls_file


def read_property_file(from_file) -> str:
    """Reads a property file and returns a dictionary of the key-value pairs.

    Args:
        from_file: The filename of the property file.

    Returns:
        A dictionary of the key-value pairs in the property file.
    """
    with open(from_file, "r", encoding="utf-8") as f:
        return dict([x.strip().split("=", 1) for x in f.readlines()])


@pytest.mark.boot
@pytest.mark.console
@pytest.mark.e2e
@pytest.mark.async_timeout(10)
async def test_avd_dir_is_canonical_in_pid_xxx_ini(avd, telnet):
    """Test pid_xxx.ini contains canonical path for avd.dir

    example:
    avd.dir=/Users/me/.android/avd/x.avd
    """
    discovery = await telnet.send("avd discoverypath")
    pid_path = Path(discovery[0])
    assert (
        pid_path.exists()
    ), f"We expect the reported discovery path: {pid_path} to exist"

    props = read_property_file(pid_path)
    assert "avd.dir" in props, f"Did not find 'avd.dir' in {props}"

    expected_path = Path(
        avd.android_avd_home, f"{avd.configuration.name}.avd"
    ).absolute()
    assert props["avd.dir"] == str(expected_path)
