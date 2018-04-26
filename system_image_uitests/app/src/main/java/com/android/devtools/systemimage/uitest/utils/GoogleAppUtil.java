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

package com.android.devtools.systemimage.uitest.utils;

import android.app.Instrumentation;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiObjectNotFoundException;
import android.support.test.uiautomator.UiSelector;

import com.android.devtools.systemimage.uitest.watchers.GoogleAppConfirmationWatcher;

/**
 * Static utility method pertaining to Google Apps
 */
public class GoogleAppUtil {

    private GoogleAppUtil() {
        throw new AssertionError();
    }

    private static final int api = SystemUtil.getApiLevel();
    private static final String email = "pstester1980@gmail.com";
    private static final String password = "pst4lif3";

    /**
     * Log a user into a Google application
     */
    public static void loginGoogleApp(Instrumentation instrumentation) throws Exception {
        final UiDevice device = UiDevice.getInstance(instrumentation);

        final UiObject inputPasswordField = api == 24 ?
                device.findObject(new UiSelector().resourceId("password")) :
                device.findObject(new UiSelector().className("android.widget.EditText"));
        final UiObject inputEmailField = api == 24 ?
                device.findObject(new UiSelector().description("Email or phone")) :
                device.findObject(new UiSelector().text("Email or phone"));

        boolean needsEmail = new Wait().
                until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() throws UiObjectNotFoundException {
                        return inputEmailField.exists();
                    }
                });

        if (needsEmail) {
            inputEmailField.clearTextField();
            inputEmailField.setText(email);
            new GoogleAppConfirmationWatcher(device).checkForCondition();
        }

        inputPasswordField.clearTextField();
        inputPasswordField.setText(password);
        new GoogleAppConfirmationWatcher(device).checkForCondition();

        device.pressHome();
    }
}