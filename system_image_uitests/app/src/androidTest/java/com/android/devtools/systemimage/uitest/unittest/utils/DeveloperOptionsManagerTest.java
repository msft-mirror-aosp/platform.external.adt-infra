package com.android.devtools.systemimage.uitest.unittest.utils;

import com.android.devtools.systemimage.uitest.framework.AbstractSystemImageTestCase;
import com.android.devtools.systemimage.uitest.utils.DeveloperOptionsManager;

import android.support.test.filters.SdkSuppress;

/**
 * Unit test on {@link DeveloperOptionsManager}.
 */
@SdkSuppress(minSdkVersion = 18)
public class DeveloperOptionsManagerTest extends AbstractSystemImageTestCase {

    public void testDeveloperOptionsManager() throws Exception {
        DeveloperOptionsManager.enableDeveloperOptions(mInstrumentation);
        assertTrue(
                "Failed to enable developer options.",
                DeveloperOptionsManager.isDeveloperOptionsEnabled(mInstrumentation));
    }
}
