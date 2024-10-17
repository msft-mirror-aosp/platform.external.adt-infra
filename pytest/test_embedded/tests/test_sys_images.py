import pytest

from emu.avd import SystemImageDownloadFailed, SystemImages

pytestmark = pytest.mark.std


@pytest.fixture
def default_image():
    s = SystemImages()
    return s.install(abi="arm64-v8a", api="33", tag="google_apis")


@pytest.mark.skipos("all", "Not related to emulator.")
@pytest.mark.flaky(reruns=0)  # b/278294760 flaky on mac_aarch64.
def test_at_least_one_available(default_image):
    assert SystemImages().available() is not None


@pytest.mark.skipos("all", "Not related to emulator.")
@pytest.mark.flaky(reruns=0)  # b/278294760 flaky on mac_aarch64.
def test_can_find_default(default_image):
    image = SystemImages().find(
        abi=default_image["abi"], api=default_image["api"], tag=default_image["tag"]
    )
    assert image == default_image


@pytest.mark.skipos("all", "Not related to emulator.")
@pytest.mark.flaky(reruns=0)  # b/278294760 flaky on mac_aarch64.
def test_can_install_default(default_image):
    image = SystemImages().install(
        abi=default_image["abi"], api=default_image["api"], tag=default_image["tag"]
    )
    assert image == default_image


@pytest.mark.skipos("all", "Not related to emulator.")
def test_throw_on_unknown_image_root():
    with pytest.raises(SystemImageDownloadFailed):
        SystemImages().install("foo", "bar")
