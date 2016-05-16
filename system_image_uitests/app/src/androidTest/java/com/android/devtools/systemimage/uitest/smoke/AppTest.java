package com.android.devtools.systemimage.uitest.smoke;

import com.android.devtools.systemimage.uitest.framework.AbstractSystemImageTestCase;
import com.android.devtools.systemimage.uitest.utils.AppLauncher;
import com.android.devtools.systemimage.uitest.utils.AppManager;
import com.android.devtools.systemimage.uitest.utils.TestUtils;

import android.app.Instrumentation;
import android.support.test.filters.SdkSuppress;
import android.support.test.uiautomator.UiDevice;

/**
 * Test suite for app interactions.
 */
@SdkSuppress(minSdkVersion = 18)
public class AppTest extends AbstractSystemImageTestCase {
    private static final String TAG = AppTest.class.getName();

    @Override
    public void setUp() throws Exception {
        super.setUp();
    }

    @Override
    public void tearDown() throws Exception {
        super.tearDown();
    }

    /**
     * Verifies the renderscript app runs on the emulator.
     * <p>
     * The test installs, launches, and uninstalls the app.
     * Test Rail ID: T136017707
     */
    public void testAppInstallAndLaunch() throws Exception {
        Instrumentation instrumentation = getInstrumentation();
        UiDevice device = UiDevice.getInstance(instrumentation);
        TestUtils.disableHomeOverlayItems(device);
        AppManager.installApp(instrumentation, "HelloCompute.apk");
        TestUtils.disableAppsOverlayItems(device);
        AppLauncher.launch(instrumentation, "RsHelloCompute");
        AppManager.uninstallApp(instrumentation, "RsHelloCompute", null);
    }
}
