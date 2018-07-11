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

package com.android.devtools.systemimage.uitest.utils.api21;

import android.app.Instrumentation;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiSelector;

import com.android.devtools.systemimage.uitest.common.Res;
import com.android.devtools.systemimage.uitest.watchers.GoogleAppConfirmationWatcher;

/**
 * Test to verify that Google services are available on Google API images
 */

public class GoogleServicesTestUtils {
    /**
     * Logs into Chrome if the Sign In button is presented
     */
    public static void signInToChrome(Instrumentation instrumentation) throws Exception {
        final UiDevice device = UiDevice.getInstance(instrumentation);
        final UiObject signInButton = device.findObject(new UiSelector().text("SIGN IN"));
        boolean hasSignInButton = new Wait(5L).until(new Wait.ExpectedCondition() {
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

        final UiObject moreButton = device.findObject(
                new UiSelector().resourceId(Res.CHROME_MORE_BUTTON_RES));

        if (new Wait().until(new Wait.ExpectedCondition() {
            @Override
            public boolean isTrue() {
                return moreButton.exists();
            }})) {
            moreButton.clickAndWaitForNewWindow();
        }

        final UiObject continueButton = device.findObject(new UiSelector().text("CONTINUE"));

        if (new Wait().until(new Wait.ExpectedCondition() {
            @Override
            public boolean isTrue() {
                return continueButton.exists();
            }})) {
            continueButton.clickAndWaitForNewWindow();
        }

        final UiObject gotItButton = device.findObject(new UiSelector().text("OK, GOT IT"));

        if (new Wait().until(new Wait.ExpectedCondition() {
            @Override
            public boolean isTrue() {
                return gotItButton.exists();
            }})) {
            gotItButton.clickAndWaitForNewWindow();
        }
    }
}
