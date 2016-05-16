package com.android.devtools.systemimage.uitest.unittest.watchers;

import com.android.devtools.systemimage.uitest.framework.AbstractSystemImageTestCase;
import com.android.devtools.systemimage.uitest.utils.AppLauncher;
import com.android.devtools.systemimage.uitest.utils.AppManager;

import android.support.test.uiautomator.UiSelector;

/**
 * Unit test on {@link com.android.devtools.systemimage.uitest.watchers.CrashWatcher CrashWatcher}.
 * <p>
 * This unit test is expected to throw an assertion error. Note that Java catch block cannot
 * catch the {@link AssertionError} that the {@link org.junit.Assert} throws if fails.
 * Thus, remember that this unit test is expected to fail.
 */
public class CrashWatcherTest extends AbstractSystemImageTestCase {

    public void testCrashWatcher() throws Exception {
        // CrashWatcher has been registered in AbstractSystemImageTestCase#setUp()
        // Here we only need to trigger the crash event, and get the expected assertion failure.
        AppManager.installApp(mInstrumentation, "CrashExample.apk");
        AppLauncher.launch(mInstrumentation, "DisplayingBitmaps");
        // Catch the crash by clicking an image.
        mDevice.findObject(new UiSelector().className("android.widget.ImageView")).click();
    }
}
