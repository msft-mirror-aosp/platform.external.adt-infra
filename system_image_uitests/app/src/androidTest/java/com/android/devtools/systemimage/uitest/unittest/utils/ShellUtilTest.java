package com.android.devtools.systemimage.uitest.unittest.utils;

import com.android.devtools.systemimage.uitest.framework.AbstractSystemImageTestCase;
import com.android.devtools.systemimage.uitest.utils.ShellUtil;

import android.support.test.filters.SdkSuppress;

/**
 * Unit test on {@link ShellUtil}.
 */
@SdkSuppress(minSdkVersion = 18)
public class ShellUtilTest extends AbstractSystemImageTestCase {

    public void testAppLauncher() throws Exception {
        ShellUtil.ShellResult result = ShellUtil.invokeCommand("ls");
        assertTrue(result.stderr, result.stdout.length() > 0 && result.stderr.length() == 0);
    }
}
