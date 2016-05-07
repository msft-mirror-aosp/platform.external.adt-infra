package com.android.devtools.systemimage.uitest.smoke;

import android.support.test.filters.SdkSuppress;
import android.support.test.uiautomator.By;
import android.support.test.uiautomator.UiSelector;
import android.support.test.uiautomator.Until;

import com.android.devtools.systemimage.uitest.framework.AbstractSystemImageTestCase;
import com.android.devtools.systemimage.uitest.utils.AppLauncher;
import com.android.devtools.systemimage.uitest.utils.AppManager;
import com.android.devtools.systemimage.uitest.watchers.VpnPopupWatcher;

import java.util.concurrent.TimeUnit;

/**
 * Test suite on VPN app.
 */
@SdkSuppress(minSdkVersion = 18)
public class VpnTest extends AbstractSystemImageTestCase {
    private static final String VPN_PACKAGE_NAME = "com.test.vpn";
    private static final String START_VPN_BUTTON_RES = "com.test.vpn:id/start_vpn";
    private static final String VPN_LOCK_ICON_RES = "com.android.systemui:id/vpn";

    /**
     * Tests if VPN works as expected.
     */
    public void testVpn() throws Exception {
        // Check if VPN is on. If true, skip.
        if (!verifyVpnStatus()) {
            AppManager.installApp(mInstrumentation, "FredVPN.apk");
            AppLauncher.launch(mInstrumentation, "TestVPN");

            // Register a watcher to dismiss the popup dialog when starting VPN.
            mDevice.registerWatcher(VpnPopupWatcher.class.getName(), new VpnPopupWatcher(mDevice));
            mDevice
                    .findObject(new UiSelector().resourceId(START_VPN_BUTTON_RES))
                    .clickAndWaitForNewWindow();
            assertTrue("Failed to find the VPN lock icon after starting VPN!", verifyVpnStatus());
            mDevice.removeWatcher(VpnPopupWatcher.class.getName());
        }
        AppManager.uninstallApp(mInstrumentation, "TestVPN", null);
    }

    private boolean verifyVpnStatus() {
        // Verify that a VPN lock icon is on the status bar.
        mDevice.openNotification();
        // Need to wait for a while to check the notification bar items
        // because opening notification is an animation.
        boolean isTrue =
                mDevice.wait(
                        Until.hasObject(By.res(VPN_LOCK_ICON_RES)),
                        TimeUnit.MILLISECONDS.convert(3L, TimeUnit.SECONDS));
        mDevice.pressHome();
        return isTrue;
    }
}
