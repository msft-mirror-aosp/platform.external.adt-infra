import pytest
from snippet_uiautomator import uiautomator
from emu.application import Application
from emu.apk import APP_MOBLY_APK

@pytest.fixture
@pytest.mark.async_timeout(90)
async def install_mobly_apk_multi(avds):
    """Installs the Mobly Snippets APK on phone (avds[0])."""
    phone_emu = avds[0]
    mobly_snippets = Application(
        phone_emu,
        apk_path=APP_MOBLY_APK.absolute(),
        package_name="com.google.android.mobly.snippet.bundled",
    )
    await mobly_snippets.install()
    yield mobly_snippets

@pytest.fixture
def mobly_phone(install_mobly_apk_multi, avds):
    phone_emu = avds[0]
    def mobly_package(package: str):
        return phone_emu.mobly(package)
    return mobly_package

@pytest.fixture(scope="function")
async def ad_ui_phone(mobly_phone, avds):
    phone_emu = avds[0]
    ad = phone_emu.mobly_device.get_device()
    ad.services.register(
        uiautomator.ANDROID_SERVICE_NAME, uiautomator.UiAutomatorService
    )
    yield ad.ui

    ad.services.unregister(uiautomator.ANDROID_SERVICE_NAME)
