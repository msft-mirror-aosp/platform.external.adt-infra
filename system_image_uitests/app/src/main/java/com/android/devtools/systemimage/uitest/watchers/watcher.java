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

import androidx.test.uiautomator.UiDevice;
import androidx.test.uiautomator.UiObject;
import androidx.test.uiautomator.UiObjectNotFoundException;
import androidx.test.uiautomator.UiSelector;
import androidx.test.uiautomator.UiWatcher;

import java.util.concurrent.TimeUnit;

import static org.junit.Assert.assertTrue;

/**
 * A generic popup watcher which will try to dismiss
 * any dialogue matching with the provided pattern.
 */
public class watcher implements UiWatcher {
    private final UiDevice mDevice;
    private final String mRegEx;   //should be a valid java style regex
    private final long mTimeout;   //should be in milliseconds

    private static final long DEFAULT_TIMEOUT = TimeUnit.MILLISECONDS.convert(3L, TimeUnit.SECONDS);

    public watcher(UiDevice device, String pattern) {
        this(device, pattern, DEFAULT_TIMEOUT);
    }

    public watcher(UiDevice device, String pattern, long timeout) {
        this.mDevice = device;
        this.mRegEx = pattern;
        this.mTimeout = timeout;
    }

    @Override
    public boolean checkForCondition() {
        boolean condition = false;
        int count = 0;

        try {
            // try to dismiss popup 10 times at max
            while (count <= 10) {
                UiObject popUp = mDevice.findObject(new UiSelector().textMatches((mRegEx)).clickable(true));
                if (popUp.waitForExists(mTimeout)) {
                    popUp.click();
                    condition = true;
                }
                else {
                    break;
                }
                count++;
            }
        }
        catch (UiObjectNotFoundException e) {
            throw new AssertionError("Failed to dismiss popup dialogs");
        }

        return condition;
    }
}
