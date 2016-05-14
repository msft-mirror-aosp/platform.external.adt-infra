package com.android.devtools.systemimage.uitest.smoke;

import com.android.devtools.systemimage.uitest.framework.AbstractSystemImageTestCase;
import com.android.devtools.systemimage.uitest.utils.AppLauncher;
import com.android.devtools.systemimage.uitest.utils.TestUtils;
import com.android.devtools.systemimage.uitest.watchers.BrowserPageLoadedWatcher;

import android.app.Instrumentation;
import android.support.test.filters.SdkSuppress;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiSelector;

/**
 * Test suite for network connection on emulator.
 */
@SdkSuppress(minSdkVersion = 18)
public class NetworkIOTest extends AbstractSystemImageTestCase {
    private static final String TAG = NetworkIOTest.class.getName();
    private static final String BROWSER_URL_TEXT_FIELD = "com.android.browser:id/url";

    @Override
    public void setUp() throws Exception {
        super.setUp();
    }

    @Override
    public void tearDown() throws Exception {
        super.tearDown();
    }

    /**
     * Verifies test browser successfully loads a web page.
     * <p>
     * Test Rail ID: T136017709
     */
    public void testBrowserLoadsSite() throws Exception {
        Instrumentation instrumentation = getInstrumentation();
        UiDevice device = UiDevice.getInstance(instrumentation);
        TestUtils.disableHomeOverlayItems(device);
        // Check network connectivity.
        if (TestUtils.verifyNetworkStatus(device)) {
            TestUtils.disableAppsOverlayItems(device);
            AppLauncher.launch(instrumentation, "Browser");
            device
                    .findObject(new UiSelector().resourceId(BROWSER_URL_TEXT_FIELD))
                    .click();
            device
                    .findObject(new UiSelector().resourceId(BROWSER_URL_TEXT_FIELD))
                    .clearTextField();
            device
                    .findObject(new UiSelector().resourceId(BROWSER_URL_TEXT_FIELD))
                    .setText("google.com");
            device.pressEnter();
            device.registerWatcher(BrowserPageLoadedWatcher.class.getName(),
                    new BrowserPageLoadedWatcher(device));
        }
    }
}