package com.android.devtools.systemimage.uitest.unittest.watchers;

import com.android.devtools.systemimage.uitest.framework.AbstractSystemImageTestCase;
import com.android.devtools.systemimage.uitest.utils.AppLauncher;
import com.android.devtools.systemimage.uitest.watchers.LockScreenWatcher;

/**
 * Unit test on {@link LockScreenWatcher}.
 */
public class LockScreenWatcherTest extends AbstractSystemImageTestCase {

    @Override
    public void setUp() throws Exception {
        super.setUp();
        mDevice.registerWatcher(LockScreenWatcher.class.getName(), new LockScreenWatcher(mDevice));
    }

    @Override
    public void tearDown() throws Exception {
        super.tearDown();
        mDevice.removeWatcher(LockScreenWatcher.class.getName());
    }

    public void testLockScreenWatcher() throws Exception {
        // For some system images (e.g., API 21), sleep and wakeup can produce a lock screen.
        // Note for some other system images (e.g., API 23), there is no lock screen by default.
        mDevice.sleep();
        mDevice.wakeUp();
        AppLauncher.launch(mInstrumentation, "Email");
    }
}
