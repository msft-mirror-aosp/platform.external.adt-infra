import pytest

from emu.avd import (
    AndroidAvdHomeDoesNotExist,
    AvdWriter,
    SystemImageDownloadFailed,
    UnsupportedAbiOrCpu,
)


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
    cfg = writer.create(abi="arm64-v8a", api="33", tag="google_apis")

    assert cfg.name == "33_google_apis_arm64-v8a_Pixel2"
    assert cfg.avd_ini.exists()
    assert (cfg.directory / "config.ini").exists()
