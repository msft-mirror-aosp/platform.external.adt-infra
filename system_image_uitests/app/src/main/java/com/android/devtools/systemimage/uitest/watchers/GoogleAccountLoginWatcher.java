package com.android.devtools.systemimage.uitest.watchers;

import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiSelector;
import android.support.test.uiautomator.UiWatcher;

import com.android.devtools.systemimage.uitest.utils.AccountManager;

import junit.framework.Assert;

import java.util.concurrent.TimeUnit;

/**
 * Google account login watcher.
 */
public class GoogleAccountLoginWatcher implements UiWatcher {
    private UiDevice mDevice;
    private String mUsername;
    private String mPassword;

    public GoogleAccountLoginWatcher(UiDevice device, String username, String password) {
        this.mDevice = device;
        this.mUsername = username;
        this.mPassword = password;
    }

    @Override
    public boolean checkForCondition() {
        try {
            // This label is the identifier of this watcher.
            // But it takes a while to check in and load the label.
            boolean isSuccess =
                    mDevice
                            .findObject(new UiSelector().text("Add your account"))
                            .waitForExists(TimeUnit.MILLISECONDS.convert(5L, TimeUnit.SECONDS));
            if (!isSuccess) {
                return false;
            }
            AccountManager.loginGoogleAccount(mDevice, mUsername, mPassword);
            return true;
        } catch (Exception e) {
            Assert.fail(e.getStackTrace().toString());
        }
        return false;
    }
}
