package com.android.devtools.systemimage.uitest.unittest.utils;

import android.support.test.filters.SdkSuppress;

import com.android.devtools.systemimage.uitest.framework.AbstractSystemImageTestCase;
import com.android.devtools.systemimage.uitest.utils.AppLauncher;

/**
 * Unit test on {@link AppLauncher}.
 */
@SdkSuppress(minSdkVersion = 18)
public class AppLauncherTest extends AbstractSystemImageTestCase {

    public void testAppLauncher() throws Exception {
        // Common apps
        AppLauncher.launch(mInstrumentation, "Contacts");
        AppLauncher.launch(mInstrumentation, "Calendar");
        AppLauncher.launch(mInstrumentation, "Email");
        AppLauncher.launch(mInstrumentation, "Settings");
        // Camera App crashes in many system images.
        // So, we skip it for our unit tests and will add it back when it is fixed.
        // AppLauncher.launchByLauncher(getInstrumentation(), "Camera");

        // Developer apps
        AppLauncher.launch(mInstrumentation, "API Demos");
        // BACKUP TEST App is not installed on some old system images.
        // AppLauncher.launchByLauncher(getInstrumentation(), "BACKUP TEST");
        AppLauncher.launch(mInstrumentation, "Custom Locale");
        AppLauncher.launch(mInstrumentation, "Dev Tools");
        AppLauncher.launch(mInstrumentation, "Dev Settings");
        AppLauncher.launch(mInstrumentation, "Gestures Builder");
        AppLauncher.launch(mInstrumentation, "Widget Preview");
    }
}
