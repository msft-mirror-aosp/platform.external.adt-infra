package com.android.devtools.systemimage.uitest.unittest.utils;

import com.android.devtools.systemimage.uitest.framework.AbstractSystemImageTestCase;
import com.android.devtools.systemimage.uitest.utils.AccountManager;

import android.support.test.filters.SdkSuppress;

/**
 * Unit test on {@link AccountManager}.
 */
@SdkSuppress(minSdkVersion = 18)
public class AccountManagerTest extends AbstractSystemImageTestCase {

    public void testAccountManager() throws Exception {
        AccountManager.addGoogleAccount(mInstrumentation, null, null);
        AccountManager.removeAccount(mInstrumentation, null);
    }
}
