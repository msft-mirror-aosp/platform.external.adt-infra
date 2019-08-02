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
import android.support.test.uiautomator.By;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiObjectNotFoundException;
import android.support.test.uiautomator.UiSelector;
import com.android.devtools.systemimage.uitest.common.Res;
import com.android.devtools.systemimage.uitest.watchers.AddGoogleAccountWatcher;
import com.android.devtools.systemimage.uitest.watchers.GoogleAppConfirmationWatcher;
import com.android.devtools.systemimage.uitest.watchers.GoogleAppContinueWatcher;
import java.util.concurrent.TimeUnit;
import android.support.test.uiautomator.Until;
import android.util.Log;

import static org.junit.Assert.assertTrue;

/**
 * Static utility method pertaining to Google Apps
 */
public class GoogleAppUtil {

    private GoogleAppUtil() {
        throw new AssertionError();
    }

    private final static String TAG = GoogleAppUtil.class.getName();
    private static final int api = SystemUtil.getApiLevel();
    private static final String email = "pstester1980@gmail.com";
    private static final String password = "pst4lif3";
    private static final long TIMEOUT = 8000;

    /**
     * Log a user into a Google application
     *  @param instrumentation
     *  @return boolean flag indicating success
     */
    public static boolean loginGoogleApp(Instrumentation instrumentation, boolean firstAttempt) throws Exception {
        final UiDevice device = UiDevice.getInstance(instrumentation);

        GoogleAppUtil.openChromeSettings(instrumentation);
        UiObject accountPromoButton = device.findObject(
                new UiSelector().resourceId(Res.CHROME_SIGNIN_PROMO_ACCOUNT_RES));
        if (accountPromoButton.waitForExists(5L)) {
            accountPromoButton.clickAndWaitForNewWindow();
        }
        UiObject signInPromoCloseButton = device.findObject(
                new UiSelector().resourceId(Res.CHROME_SIGNIN_PROMO_CLOSE_RES));
        if (signInPromoCloseButton.waitForExists(5L)) {
            signInPromoCloseButton.clickAndWaitForNewWindow();
        }

        UiObject signInChromeLabel = device.findObject(
                new UiSelector().text("Sign in to Chrome"));
        if (signInChromeLabel.waitForExists(5L)) {
            signInChromeLabel.clickAndWaitForNewWindow();
        }

        UiObject testUserEmail = device.findObject(new UiSelector().text(email));
        if (testUserEmail.waitForExists(5L)) {
            new GoogleAppContinueWatcher(device).checkForCondition();
            UiObject chromePositiveButton = device.findObject(
                    new UiSelector().resourceId(Res.CHROME_POSITIVE_BUTTON_RES));
            if (chromePositiveButton.waitForExists(5L)) {
                chromePositiveButton.clickAndWaitForNewWindow();
            }
            device.pressHome();
            Log.i("Login", "Found existing user");
            return true;
        }

        final UiObject signInButton = device.findObject(
                new UiSelector().textMatches(("(?i)sign in(?-i)")));

        boolean needsSignIn = new Wait().
                until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() throws UiObjectNotFoundException {
                        return signInButton.exists();
                    }
                });

        if (!needsSignIn) {
            Log.i("Login", "Sign in does not exist");
            return true;
        }

        signInButton.clickAndWaitForNewWindow();

        UiObject signedOutButton = device.findObject(
                new UiSelector().descriptionContains("signed out"));
        boolean wasSignedOut = signedOutButton.waitForExists(
                TimeUnit.MILLISECONDS.convert(5L, TimeUnit.SECONDS));
        if (wasSignedOut) {
            Log.i("Login", "was signed out");
            clickNext(device);
        }

        UiObject editInput = device.findObject(new UiSelector().className("android.widget.EditText"));
        boolean hasEditInput = editInput.waitForExists(
                TimeUnit.MILLISECONDS.convert(3L, TimeUnit.SECONDS));
        assertTrue("Email field not found", firstAttempt || hasEditInput);
        if ( !hasEditInput ) {
            Log.i("Login", "Retry google login");
            device.pressHome();
            TimeUnit.SECONDS.sleep(5);
            return loginGoogleApp(instrumentation, false);
        }

        UiObject inputEmailField = device.findObject(new UiSelector().description("Email or phone"));
        UiObject forgotEmailLink = api >= 28 ? device.findObject(new UiSelector().text("Forgot email?")) :
                device.findObject(new UiSelector().description("Forgot email?"));

        boolean needsEmail = api == 24 ? inputEmailField.waitForExists(
                TimeUnit.MILLISECONDS.convert(10L, TimeUnit.SECONDS)) :
                forgotEmailLink.waitForExists(TimeUnit.MILLISECONDS.convert(10L, TimeUnit.SECONDS));
        assertTrue("Forgot email not found", firstAttempt || needsEmail);
        if ( !needsEmail ) {
            Log.i("Login", "Retry google login");
            device.pressHome();
            TimeUnit.SECONDS.sleep(5);
            return loginGoogleApp(instrumentation, false);
        }

        Log.i("Login", "enter email");
        editInput.clearTextField();
        editInput.setText(email);
        clickNext(device);

        UiObject forgotPasswordLink = api >= 28 ? device.findObject(new UiSelector().text("Forgot password?")) :
                device.findObject(new UiSelector().description("Forgot password?"));
        boolean needsPassword = forgotPasswordLink.waitForExists(
                TimeUnit.MILLISECONDS.convert(3L, TimeUnit.SECONDS));
        assertTrue("Forgot password not found", firstAttempt || needsPassword);
        if ( !needsPassword ) {
            Log.i("Login", "Retry google login");
            device.pressHome();
            TimeUnit.SECONDS.sleep(5);
            return loginGoogleApp(instrumentation, false);
        }

        Log.i("Login", "enter password");
        editInput.clearTextField();
        editInput.setText(password);
        clickNext(device);

        boolean isSignedIn = new GoogleAppConfirmationWatcher(device).checkForCondition();
        assertTrue("Login failed", firstAttempt || isSignedIn);
        if ( !isSignedIn ) {
            Log.i("Login", "Retry google login");
            device.pressHome();
            TimeUnit.SECONDS.sleep(5);
            return loginGoogleApp(instrumentation, false);
        }

        UiObject backupSwitch = device.findObject(new UiSelector().resourceId(Res.GOOGLE_BACKUP_SWITCH_RES));
        if (backupSwitch.waitForExists(TimeUnit.MILLISECONDS.convert(3L, TimeUnit.SECONDS))) {
            backupSwitch.click();
        }

        UiObject agreeButton = device.findObject(new UiSelector().resourceId(Res.GOOGLE_SERVICES_ACCEPT_BUTTON_RES));
        if(agreeButton.exists()){
            agreeButton.clickAndWaitForNewWindow();
        }

        UiObject moreButton = device.findObject(new UiSelector().textMatches("(?i)more(?-i)"));
        if (moreButton.waitForExists(TimeUnit.MILLISECONDS.convert(3L, TimeUnit.SECONDS))) {
            moreButton.clickAndWaitForNewWindow();
        }

        new GoogleAppContinueWatcher(device).checkForCondition();

        UiObject backupButton = device.findObject(new UiSelector().textMatches("(?i)agree(?-i)"));
        if (backupButton.waitForExists(TimeUnit.MILLISECONDS.convert(3L, TimeUnit.SECONDS))) {
            backupButton.clickAndWaitForNewWindow();
        }

        device.pressHome();
        TimeUnit.SECONDS.sleep(10);
        return isSignedIn;
    }

    public static boolean logoutGoogleChrome(Instrumentation instrumentation) throws Exception {
        final UiDevice device = UiDevice.getInstance(instrumentation);

        GoogleAppUtil.openChromeSettings(instrumentation);

        final UiObject androidIconButton = device.findObject(
                new UiSelector().resourceId(Res.ANDROID_ICON_RES).
                        className("android.widget.ImageView"));

        if (new Wait().until(new Wait.ExpectedCondition() {
            @Override
            public boolean isTrue() {
                return androidIconButton.exists();
            }})) {
            androidIconButton.clickAndWaitForNewWindow();
        }

        final UiObject signOutLabel = device.findObject(new UiSelector().text("Sign out of Chrome"));

        if (new Wait().until(new Wait.ExpectedCondition() {
            @Override
            public boolean isTrue() {
                return signOutLabel.exists();
            }})) {
            signOutLabel.clickAndWaitForNewWindow();
        } else {
            return true;
        }

        final UiObject signOutButton = device.findObject(new UiSelector().text("SIGN OUT"));

        if (new Wait().until(new Wait.ExpectedCondition() {
            @Override
            public boolean isTrue() {
                return signOutButton.exists();
            }})) {
            signOutButton.clickAndWaitForNewWindow();
        }

        final UiObject signInLabel = device.findObject(new UiSelector().text("Sign in to Chrome"));
        final UiObject signInPromoCloseButton = device.findObject(
                new UiSelector().resourceId(Res.CHROME_SIGNIN_PROMO_CLOSE_RES));

        return signInLabel.exists() || signInPromoCloseButton.exists();
    }

    private static void openChromeSettings(Instrumentation instrumentation) throws Exception {
        UiDevice device = UiDevice.getInstance(instrumentation);

        AppLauncher.launch(instrumentation, "Chrome");

        UiObject termsAcceptButton = device.findObject(new UiSelector().
                resourceId(Res.CHROME_TERMS_ACCEPT_BUTTON_RES));
        if (termsAcceptButton.waitForExists(TimeUnit.MILLISECONDS.convert(3L, TimeUnit.SECONDS))) {
            termsAcceptButton.clickAndWaitForNewWindow();
        }

        UiObject nextButton = device.findObject(new UiSelector().
                resourceId(Res.GOOGLE_SERVICES_NEXT_BUTTON_RES));
        if (nextButton.waitForExists(TimeUnit.MILLISECONDS.convert(3L, TimeUnit.SECONDS))) {
            nextButton.clickAndWaitForNewWindow();
        }

        final UiObject chromeUpdateButton = device.findObject(
                new UiSelector().resourceId(Res.CHROME_MENU_BADGE_RES)
        );

        if (new Wait().until(new Wait.ExpectedCondition() {
            @Override
            public boolean isTrue() {
                return chromeUpdateButton.exists();
            }
        })) {
            chromeUpdateButton.clickAndWaitForNewWindow();
        }

        final UiObject chromeMenuButton = device.findObject(
                new UiSelector().resourceId(Res.CHROME_MENU_BUTTON_RES));

        if (new Wait().until(new Wait.ExpectedCondition() {
            @Override
            public boolean isTrue() {
                return chromeMenuButton.exists();
            }
        })) {
            chromeMenuButton.clickAndWaitForNewWindow();
        }

        final UiObject settingsButton = device.findObject(new UiSelector().text("Settings"));

        if (new Wait().until(new Wait.ExpectedCondition() {
            @Override
            public boolean isTrue() {
                return settingsButton.exists();
            }})) {
            settingsButton.clickAndWaitForNewWindow();
        }
    }

    private static void clickNext(UiDevice device) throws UiObjectNotFoundException{
        UiObject nextButton = device.findObject(new UiSelector().textMatches(("(?i)next(?-i)")));
        if (!nextButton.waitForExists(TimeUnit.MILLISECONDS.convert(3L, TimeUnit.SECONDS))) {
            nextButton = device.findObject(new UiSelector().descriptionMatches(("(?i)next(?-i)")));
        }

        if (nextButton.exists()) {
            nextButton.clickAndWaitForNewWindow(10L);
        }
    }
}
