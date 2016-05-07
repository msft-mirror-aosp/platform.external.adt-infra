package com.android.devtools.systemimage.uitest.framework;

import android.app.Instrumentation;
import android.support.test.uiautomator.UiDevice;
import android.test.InstrumentationTestCase;

import com.android.devtools.systemimage.uitest.watchers.AndroidWelcomeClingWatcher;
import com.android.devtools.systemimage.uitest.watchers.CrashWatcher;
import com.android.devtools.systemimage.uitest.watchers.LockScreenWatcher;

/**
 * Abstract class definition of system image test cases.
 */
public class AbstractSystemImageTestCase extends InstrumentationTestCase {
    protected Instrumentation mInstrumentation;
    protected UiDevice mDevice;
    protected CrashWatcher mCrashWatcher;

    @Override
    protected void setUp() throws Exception {
        super.setUp();
        mInstrumentation = getInstrumentation();
        mDevice = UiDevice.getInstance(mInstrumentation);
        mCrashWatcher =
                new CrashWatcher(mDevice, mInstrumentation.getTargetContext().getExternalFilesDir(null));
        // Read a testing Google account credential

        // Power on.
        mDevice.wakeUp();
        assertTrue("Failed to wake up the device.", mDevice.isScreenOn());
        // Dismiss a lock screen if any.
        mDevice.pressMenu();
        // Go to Home.
        mDevice.pressHome();

        // Register crash, lock screen and Android welcome cling watchers.
        mDevice.registerWatcher(CrashWatcher.class.getName(), mCrashWatcher);
        mDevice.registerWatcher(LockScreenWatcher.class.getName(), new LockScreenWatcher(mDevice));
        mDevice.registerWatcher(
                AndroidWelcomeClingWatcher.class.getName(), new AndroidWelcomeClingWatcher(mDevice));
    }

    @Override
    protected void tearDown() throws Exception {
        super.tearDown();

        // Must check the crash watcher again for finalization,
        // or could miss a crash if it happens at the end of a test case.
        mCrashWatcher.checkForCondition();

        // Go to Home.
        mDevice.pressHome();

        // Remove watchers.
        mDevice.removeWatcher(CrashWatcher.class.getName());
        mDevice.removeWatcher(LockScreenWatcher.class.getName());
        mDevice.removeWatcher(AndroidWelcomeClingWatcher.class.getName());
    }
}
