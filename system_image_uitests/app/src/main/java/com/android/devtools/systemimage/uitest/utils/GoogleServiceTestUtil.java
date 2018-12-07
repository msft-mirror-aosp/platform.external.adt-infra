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

import com.android.devtools.systemimage.uitest.common.Res;
import com.android.devtools.systemimage.uitest.watchers.GoogleAppConfirmationWatcher;
import com.android.devtools.systemimage.uitest.watchers.GoogleAppContinueWatcher;

import android.app.Instrumentation;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiSelector;

public class GoogleServiceTestUtil {

    private GoogleServiceTestUtil() {
        throw new AssertionError();
    }

    /**
     * Logs into Chrome if the Sign In button is presented
     */
    public static void signInToChrome(Instrumentation instrumentation) throws Exception {
        final UiDevice device = UiDevice.getInstance(instrumentation);
        final UiObject signInButton = device.findObject(new UiSelector().
                resourceId(Res.CHROME_POSITIVE_BUTTON_RES));
        boolean hasSignInButton = new Wait(25L).until(new Wait.ExpectedCondition() {
            @Override
            public boolean isTrue() {
                return signInButton.exists();
            }
        });

        if (hasSignInButton) {
            signInButton.clickAndWaitForNewWindow();
            GoogleAppUtil.loginGoogleApp(instrumentation);
            AppLauncher.launch(instrumentation, "Chrome");
            new GoogleAppConfirmationWatcher(device).checkForCondition();
        }
    }
}
