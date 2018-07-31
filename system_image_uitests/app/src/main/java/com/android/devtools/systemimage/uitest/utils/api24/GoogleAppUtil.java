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

package com.android.devtools.systemimage.uitest.utils.api24;

import android.app.Instrumentation;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiObjectNotFoundException;
import android.support.test.uiautomator.UiSelector;

import com.android.devtools.systemimage.uitest.common.Res;
import com.android.devtools.systemimage.uitest.watchers.GoogleAppConfirmationWatcher;

import java.util.concurrent.TimeUnit;

/**
 * Static utility method pertaining to Google Apps
 */
public class GoogleAppUtil {

    private GoogleAppUtil() {
        throw new AssertionError();
    }

    private static final String email = "pstester1980@gmail.com";
    private static final String password = "pst4lif3";

    /**
     * Log a user into a Google application
     */
    public static void loginGoogleApp(Instrumentation instrumentation) throws Exception {
        final UiDevice device = UiDevice.getInstance(instrumentation);
        final UiObject signInButton = device.findObject(
                new UiSelector().textMatches(("(?i)sign in(?-i)")));
        boolean needsSignIn = new Wait().
                until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() throws UiObjectNotFoundException {
                        return signInButton.exists();
                    }
                });
        if (needsSignIn) {
            signInButton.clickAndWaitForNewWindow();
        }

        UiObject inputEmailField = device.findObject(new UiSelector().description("Email or phone"));

        boolean needsEmail = inputEmailField.waitForExists(
                TimeUnit.MILLISECONDS.convert(10L, TimeUnit.SECONDS));

        UiObject editInput = device.findObject(new UiSelector().className("android.widget.EditText"));
        boolean hasEditInput = editInput.waitForExists(
                TimeUnit.MILLISECONDS.convert(3L, TimeUnit.SECONDS));

        if (needsEmail && hasEditInput) {
            editInput.clearTextField();
            editInput.setText(email);
            clickNext(device);
        } else {
            boolean wasSignedOut = device.findObject(
                    new UiSelector().descriptionContains("signed out")).exists();
            if (wasSignedOut) {
                clickNext(device);
            }
        }

        UiObject forgotPasswordLink = device.findObject(new UiSelector().description("Forgot password?"));
        boolean needsPassword = forgotPasswordLink.waitForExists(
                TimeUnit.MILLISECONDS.convert(3L, TimeUnit.SECONDS));

        hasEditInput = editInput.waitForExists(
                TimeUnit.MILLISECONDS.convert(3L, TimeUnit.SECONDS));

        if (needsPassword && hasEditInput) {
            editInput.clearTextField();
            editInput.setText(password);
            clickNext(device);
        }

        new GoogleAppConfirmationWatcher(device).checkForCondition();
        UiObject signInConsentAgreeButton = device.findObject(new UiSelector().resourceId(Res.NOW_SIGNIN_ACCEPT_BUTTON_RES));

        if (signInConsentAgreeButton.waitForExists(TimeUnit.MILLISECONDS.convert(3L, TimeUnit.SECONDS))) {
            signInConsentAgreeButton.clickAndWaitForNewWindow();
        }

        UiObject backupSwitch = device.findObject(new UiSelector().resourceId(Res.GOOGLE_BACKUP_SWITCH_RES));
        if (backupSwitch.waitForExists(TimeUnit.MILLISECONDS.convert(3L, TimeUnit.SECONDS))) {
            backupSwitch.clickAndWaitForNewWindow();
        }

        UiObject moreButton = device.findObject(new UiSelector().textMatches("(?i)more(?-i)"));
        if (moreButton.waitForExists(TimeUnit.MILLISECONDS.convert(3L, TimeUnit.SECONDS))) {
            moreButton.clickAndWaitForNewWindow();
        }

        UiObject backupButton = device.findObject(new UiSelector().textMatches("(?i)agree(?-i)"));
        if (backupButton.waitForExists(TimeUnit.MILLISECONDS.convert(3L, TimeUnit.SECONDS))) {
            backupButton.clickAndWaitForNewWindow();
        }

        device.pressHome();
    }

    private static void clickNext(UiDevice device) throws UiObjectNotFoundException{
        UiObject nextButton = device.findObject(new UiSelector().textMatches(("(?i)next(?-i)")));
        if (!nextButton.waitForExists(TimeUnit.MILLISECONDS.convert(3L, TimeUnit.SECONDS))) {
            nextButton = device.findObject(new UiSelector().descriptionMatches(("(?i)next(?-i)")));
        }

        if (nextButton.exists()) {
            nextButton.clickAndWaitForNewWindow();
        }
    }
}
