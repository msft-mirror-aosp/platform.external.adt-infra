import pytest
from emu.avd import (
    AndroidAvdHomeDoesNotExist,
    AvdWriter,
    SystemImageDirectoryDoesNotExist,
    SystemImageDownloadFailed,
    UnsupportedAbiOrCpu,
)


def test_throw_on_unknown_sdk_root():
    with pytest.raises(SystemImageDirectoryDoesNotExist):
        AvdWriter(sdk_root="/bar/foo/guusku")


def test_throw_on_unknown_avd_root():
    with pytest.raises(AndroidAvdHomeDoesNotExist):
        AvdWriter(avd_home="/bar/foo/guusku")


def test_throw_on_unknown_cpu(tmp_path):
    writer = AvdWriter(avd_home=tmp_path)
    with pytest.raises(UnsupportedAbiOrCpu):
        writer.create(abi="BADCPU", api="33", tag="google_apis")


def test_throw_on_unknown_tag(tmp_path):
    writer = AvdWriter(avd_home=tmp_path)
    with pytest.raises(SystemImageDownloadFailed):
        writer.create(abi="arm64-v8a", api="33", tag="wanou?")


def test_can_write_avd(tmp_path):
    writer = AvdWriter(avd_home=tmp_path)
    name = writer.create(abi="arm64-v8a", api="33", tag="google_apis")

    assert name == "33_google_apis_arm64-v8a"
    assert (tmp_path / f"{name}.ini").exists()
    assert (tmp_path / f"{name}.avd" / "config.ini").exists()
