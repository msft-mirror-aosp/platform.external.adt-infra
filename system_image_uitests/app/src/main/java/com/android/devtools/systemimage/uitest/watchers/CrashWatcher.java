package com.android.devtools.systemimage.uitest.watchers;

import junit.framework.Assert;

import android.support.test.uiautomator.By;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObjectNotFoundException;
import android.support.test.uiautomator.UiSelector;
import android.support.test.uiautomator.UiWatcher;

import java.io.File;

/**
 * Detects the dialog that appears when an app crashes.
 */
public class CrashWatcher implements UiWatcher {
    private UiDevice mDevice;
    private File mStorageDirPath;

    public CrashWatcher(UiDevice device, File storageDirPath) {
        this.mDevice = device;
        this.mStorageDirPath = storageDirPath;
    }

    @Override
    public boolean checkForCondition() {
        if (mDevice.hasObject(By.textContains(("has stopped")))
                || mDevice.hasObject(By.textContains("isn't responding"))
                || mDevice.hasObject(By.clazz("com.android.server.am.AppNotRespondingDialog"))
                || mDevice.hasObject(By.clazz("com.android.server.am.AppErrorDialog"))
                || mDevice.hasObject(By.textContains("keeps stopping"))) {
            reportCrashAndDismiss();
        }
        return false;
    }

    private void reportCrashAndDismiss() {
        File ss = new File(mStorageDirPath, "crash.png");
        mDevice.takeScreenshot(ss);
        try {
            if (mDevice.hasObject(By.text("OK"))) {
                mDevice.findObject(new UiSelector().text("OK")).click();
            } else if (mDevice.hasObject(By.text("Close"))) {
                mDevice.findObject(new UiSelector().text("Close")).click();
            }
        } catch (UiObjectNotFoundException e) {
            Assert.fail(
                    "Failed to dismiss the crash popup. This is a critical bug to fix, or the "
                            + "following tests will catch the same crash over and over!");
        }
        Assert.fail("Caught an application crash. Screenshot saved to " + ss.getAbsolutePath());
    }
}
