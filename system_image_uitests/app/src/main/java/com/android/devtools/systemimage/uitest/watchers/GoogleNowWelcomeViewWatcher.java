package com.android.devtools.systemimage.uitest.watchers;

import com.android.devtools.systemimage.uitest.common.Res;

import junit.framework.Assert;

import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiSelector;
import android.support.test.uiautomator.UiWatcher;

/**
 * Google Now welcome view watcher.
 */
public class GoogleNowWelcomeViewWatcher implements UiWatcher {
    private UiDevice mDevice;

    public GoogleNowWelcomeViewWatcher(UiDevice device) {
        mDevice = device;
    }

    @Override
    public boolean checkForCondition() {
        UiObject skipButton =
                mDevice.findObject(new UiSelector().resourceId(Res.GOOGLE_NOW_WELCOME_SKIP_RES));
        try {
            if (skipButton.exists()) {
                skipButton.clickAndWaitForNewWindow();
                return true;
            } else {
                return false;
            }
        } catch (Exception e) {
            Assert.fail(e.getStackTrace().toString());
            return false;
        }
    }
}
