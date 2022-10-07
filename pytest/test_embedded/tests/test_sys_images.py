from pathlib import Path
import pytest
from google.protobuf import empty_pb2

from emu.avd import SystemImageDirectoryDoesNotExist, SystemImageDownloadFailed, SystemImages


@pytest.fixture
def default_image():
    s = SystemImages()
    return s.install(abi="arm64-v8a", api="33", tag="google_apis")


def test_at_least_one_available(default_image):
    assert SystemImages().available() is not None


def test_can_find_default(default_image):
    image = SystemImages().find(
        abi=default_image["abi"], api=default_image["api"], tag=default_image["tag"]
    )
    assert image == default_image


def test_can_install_default(default_image):
    image = SystemImages().install(
        abi=default_image["abi"], api=default_image["api"], tag=default_image["tag"]
    )
    assert image == default_image


def test_throw_on_unknown_sdk_root():
    with pytest.raises(SystemImageDirectoryDoesNotExist, match=r".*foo.*"):
        SystemImages("/bar/foo/guusku")


def test_throw_on_unknown_image_root():
    with pytest.raises(SystemImageDownloadFailed):
        SystemImages().install("foo", "bar")
