package com.android.devtools.systemimage.uitest.watchers;

import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiSelector;
import android.support.test.uiautomator.UiWatcher;

/**
 * Unlocks the device (assuming no password or puzzle) if the lock screen has activated.
 */
public class LockScreenWatcher implements UiWatcher {
    private UiDevice mDevice;

    public LockScreenWatcher(UiDevice device) {
        this.mDevice = device;
    }

    @Override
    public boolean checkForCondition() {
        UiObject unlock =
                mDevice.findObject(
                        new UiSelector().packageName("com.android.keyboard").descriptionContains
                                ("Slide area"));
        UiObject unlock2 =
                mDevice.findObject(new UiSelector().resourceId("com.android" +
                        ".systemui:id/lock_icon"));
        if (unlock.exists() || unlock2.exists()) {
            mDevice.pressMenu();
            return true;
        }
        return false;
    }
}
