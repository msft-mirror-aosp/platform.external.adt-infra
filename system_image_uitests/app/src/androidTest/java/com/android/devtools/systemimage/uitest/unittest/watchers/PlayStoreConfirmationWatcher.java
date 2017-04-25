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

package com.android.devtools.systemimage.uitest.unittest.watchers;


import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiObjectNotFoundException;
import android.support.test.uiautomator.UiSelector;
import android.support.test.uiautomator.UiWatcher;

import com.android.devtools.systemimage.uitest.common.Res;
import com.android.devtools.systemimage.uitest.utils.Wait;

/**
 * VPN app popup watcher that monitors and dismisses the VPN popup dialog.
 * <p>
 * Note that this watcher should only be registered before playing the VPN app.
 */
public class PlayStoreConfirmationWatcher implements UiWatcher {
    private final UiDevice mDevice;

    public PlayStoreConfirmationWatcher(UiDevice device) {
        this.mDevice = device;
    }

    @Override
    public boolean checkForCondition() {
        UiObject confirmBox = mDevice.findObject(new UiSelector().text("CONFIRM"));
        UiObject okBox = mDevice.findObject(new UiSelector().text("OK"));
        try {
            if (confirmBox.exists()) {
                confirmBox.click();
            }
            if (okBox.exists()) {
                okBox.click();
                return true;
            }
            else {
                return false;
            }
        } catch (UiObjectNotFoundException e) {
            throw new AssertionError("Failed to dismiss the VPN popup dialog");
        }
    }
}