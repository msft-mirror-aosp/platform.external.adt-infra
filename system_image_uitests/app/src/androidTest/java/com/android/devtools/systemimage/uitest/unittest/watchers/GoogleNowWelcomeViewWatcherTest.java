package com.android.devtools.systemimage.uitest.unittest.watchers;

import com.android.devtools.systemimage.uitest.framework.AbstractSystemImageTestCase;
import com.android.devtools.systemimage.uitest.utils.AppLauncher;
import com.android.devtools.systemimage.uitest.watchers.GoogleNowWelcomeViewWatcher;

/**
 * Unit test on {@link GoogleNowWelcomeViewWatcher}.
 */
public class GoogleNowWelcomeViewWatcherTest extends AbstractSystemImageTestCase {

    @Override
    public void setUp() throws Exception {
        super.setUp();
        mDevice.registerWatcher(
                GoogleNowWelcomeViewWatcher.class.getName(), new GoogleNowWelcomeViewWatcher(mDevice));
    }

    @Override
    public void tearDown() throws Exception {
        super.tearDown();
        mDevice.removeWatcher(GoogleNowWelcomeViewWatcher.class.getName());
    }

    public void testGoogleNowWelcomeViewWatcher() throws Exception {
        AppLauncher.launch(mInstrumentation, "Google");
    }
}
