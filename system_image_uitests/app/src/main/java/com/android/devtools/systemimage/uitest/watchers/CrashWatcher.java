/*
 * Copyright (c) 2016 The Android Open Source Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.android.devtools.systemimage.uitest.watchers;

import org.junit.Assert;

import android.support.test.uiautomator.By;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObjectNotFoundException;
import android.support.test.uiautomator.UiSelector;
import android.support.test.uiautomator.UiWatcher;

import java.io.File;

/**
 * Crash watcher that detects the dialog appearing when an app crashes.
 */
public class CrashWatcher implements UiWatcher {
    private final UiDevice mDevice;
    private final File mStorageDirPath;

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
            } else {
                Assert.fail("Failed to dismiss the crash popup!");
            }
        } catch (UiObjectNotFoundException e) {
            Assert.fail("Failed to dismiss the crash popup!");
        }
        Assert.fail("Caught an application crash. Screenshot saved to " + ss.getAbsolutePath());
    }
}
