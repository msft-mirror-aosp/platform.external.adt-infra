package com.android.devtools.systemimage.uitest.unittest.watchers;

import com.android.devtools.systemimage.uitest.framework.AbstractSystemImageTestCase;
import com.android.devtools.systemimage.uitest.utils.AppLauncher;
import com.android.devtools.systemimage.uitest.watchers.GoogleAccountLoginWatcher;

/**
 * Unit test on {@link GoogleAccountLoginWatcher}
 */
public class GoogleAccountLoginWatcherTest extends AbstractSystemImageTestCase {

    @Override
    public void setUp() throws Exception {
        super.setUp();
        mDevice.registerWatcher(
                GoogleAccountLoginWatcher.class.getName(),
                new GoogleAccountLoginWatcher(mDevice, null, null));
    }

    @Override
    public void tearDown() throws Exception {
        super.tearDown();
        mDevice.removeWatcher(GoogleAccountLoginWatcher.class.getName());
    }

    public void testGoogleAccountLoginWatcher() throws Exception {
        AppLauncher.launch(mInstrumentation, "Contacts");
    }
}
