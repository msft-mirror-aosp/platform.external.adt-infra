import pytest

from emu.avd import (
    AndroidAvdHomeDoesNotExist,
    AvdWriter,
    SystemImageDownloadFailed,
    UnsupportedAbiOrCpu,
)


@pytest.mark.test_infra
def test_throw_on_unknown_avd_root(pytestconfig):
    with pytest.raises(AndroidAvdHomeDoesNotExist):
        AvdWriter(avd_home="/bar/foo/guusku", fetcher=pytestconfig.getoption("fetcher"))


@pytest.mark.test_infra
def test_throw_on_unknown_cpu(pytestconfig, tmp_path):
    writer = AvdWriter(avd_home=tmp_path, fetcher=pytestconfig.getoption("fetcher"))
    with pytest.raises(UnsupportedAbiOrCpu):
        writer.create(abi="BADCPU", api="33", tag="google_apis")


@pytest.mark.test_infra
def test_throw_on_unknown_tag(pytestconfig, tmp_path):
    writer = AvdWriter(avd_home=tmp_path, fetcher=pytestconfig.getoption("fetcher"))
    with pytest.raises(SystemImageDownloadFailed):
        writer.create(abi="arm64-v8a", api="33", tag="wanou?")


@pytest.mark.test_infra
def test_can_write_avd(pytestconfig, tmp_path):
    writer = AvdWriter(avd_home=tmp_path, fetcher=pytestconfig.getoption("fetcher"))
    cfg = writer.create(abi="arm64-v8a", api="33", tag="google_apis")

    assert cfg.name == "33_google_apis_arm64-v8a_Pixel2"
    assert cfg.avd_ini.exists()
    assert (cfg.directory / "config.ini").exists()
