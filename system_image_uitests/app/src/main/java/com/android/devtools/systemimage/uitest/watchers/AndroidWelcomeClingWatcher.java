package com.android.devtools.systemimage.uitest.watchers;

import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiObjectNotFoundException;
import android.support.test.uiautomator.UiSelector;
import android.support.test.uiautomator.UiWatcher;

import com.android.devtools.systemimage.uitest.common.Res;

import junit.framework.Assert;

/**
 * Android welcome cling watcher.
 */
public class AndroidWelcomeClingWatcher implements UiWatcher {
    private UiDevice mDevice;

    public AndroidWelcomeClingWatcher(UiDevice device) {
        mDevice = device;
    }

    @Override
    public boolean checkForCondition() {
        UiObject androidCling =
                mDevice.findObject(new UiSelector().resourceId(Res.ANDROID_WELCOME_CLING_RES));
        UiObject launcherCling =
                mDevice.findObject(new UiSelector().resourceId(Res.ANDROID_LAUNCHER_WELCOME_CLING_RES));
        try {
            if (androidCling.exists()) {
                androidCling.click();
                return true;
            } else if (launcherCling.exists()) {
                launcherCling.click();
                return true;
            } else {
                return false;
            }
        } catch (UiObjectNotFoundException e) {
            Assert.fail(e.getStackTrace().toString());
            return false;
        }
    }
}
