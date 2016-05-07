package com.android.devtools.systemimage.uitest.unittest.utils;

import android.support.test.filters.SdkSuppress;

import com.android.devtools.systemimage.uitest.framework.AbstractSystemImageTestCase;
import com.android.devtools.systemimage.uitest.utils.AppManager;

/**
 * Unit test on {@link AppManager}.
 */
@SdkSuppress(minSdkVersion = 18)
public class AppManagerTest extends AbstractSystemImageTestCase {

    public void testAppManager() throws Exception {
        AppManager.installApp(mInstrumentation, "FredVPN.apk");
        AppManager.installApp(mInstrumentation, "HelloCompute.apk");
        assertTrue(
                "Failed to find FredVPN.", AppManager.isAppInstalled(mInstrumentation, "TestVPN", null));
        assertTrue(
                "Failed to find RsHelloCompute.",
                AppManager.isAppInstalled(mInstrumentation, "RsHelloCompute", null));
        AppManager.uninstallApp(mInstrumentation, "TestVPN", null);
        AppManager.uninstallApp(mInstrumentation, "RsHelloCompute", null);
    }
}
