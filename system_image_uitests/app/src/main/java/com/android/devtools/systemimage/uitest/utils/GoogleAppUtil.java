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
import android.support.test.uiautomator.UiScrollable;
import android.support.test.uiautomator.UiSelector;
import com.android.devtools.systemimage.uitest.common.Res;
import com.android.devtools.systemimage.uitest.watchers.watcher;
import java.util.concurrent.TimeUnit;
import android.util.Log;
import android.view.KeyEvent;

import static org.junit.Assert.assertTrue;

/**
 * Static utility method pertaining to Google Apps
 */
public class GoogleAppUtil {

    private GoogleAppUtil() {
        throw new AssertionError();
    }

    private static final int api = SystemUtil.getApiLevel();
    private static final String email = "demo.sysimg.user1@gmail.com";

    /**
     * Log a user into a Google application
     *  @param instrumentation
     *  @return boolean flag indicating success
     */
    public static boolean loginGoogleApp(Instrumentation instrumentation, boolean firstAttempt) throws Exception {
        final UiDevice device = UiDevice.getInstance(instrumentation);

        GoogleAppUtil.openChromeSettings(instrumentation);
        UiObject syncAndPersonalizeButton = device.findObject(
                new UiSelector().text("Sync and personalize across devices"));
        if (syncAndPersonalizeButton.waitForExists(5L)) {
            syncAndPersonalizeButton.clickAndWaitForNewWindow();
        }

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
        UiObject accountSelectionMark = device.findObject(new UiSelector().resourceId(
                Res.CHROME_ACCOUNT_SELECTION_MARK_RES));
        if (testUserEmail.waitForExists(5L) && accountSelectionMark.waitForExists(5L)) {
            return true;
        }

        UiObject addAccountLabel = device.findObject(
                new UiSelector().text("Add account"));
        if (addAccountLabel.waitForExists(5L)) {
            addAccountLabel.clickAndWaitForNewWindow();
        }

        if (testUserEmail.waitForExists(5L)) {
            new watcher(device, Res.GOOGLE_APP_CONT_WATCHER_PATTERN).checkForCondition();
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

        boolean needsSignIn = new Wait(30000L).
                until(signInButton::exists);

        if (!needsSignIn) {
            Log.i("Login", "Sign in does not exist");
            return true;
        }

        signInButton.clickAndWaitForNewWindow();

        UiObject signedOutButton = device.findObject(
                new UiSelector().descriptionContains("signed out"));
        boolean wasSignedOut = signedOutButton.waitForExists(
                TimeUnit.MILLISECONDS.convert(15L, TimeUnit.SECONDS));
        UiObject createAccount = device.findObject(new UiSelector().
                textMatches("(?i)create account(?-i)"));
        if (wasSignedOut || createAccount.exists()) {
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

        UiObject forgotEmailLink = api >= 28 ? device.findObject(new UiSelector().text("Forgot email?")) :
                device.findObject(new UiSelector().description("Forgot email?"));

        boolean needsEmail = forgotEmailLink.waitForExists(
                TimeUnit.MILLISECONDS.convert(10L, TimeUnit.SECONDS));
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

        UiObject forgotPasswordLink;

        if (api == 27 || api == 28) {
            forgotPasswordLink = device.findObject(new UiSelector().resourceId("forgotPassword"));
        } else if (api == 29 || api == 30) {
            forgotPasswordLink = device.findObject(new UiSelector().text("Forgot password?"));
        } else if (api >= 31) {
            forgotPasswordLink = device.findObject(new UiSelector().resourceId("forgotPassword"));
        } else {
            forgotPasswordLink = device.findObject(new UiSelector().description("Forgot password?"));
        }

        boolean needsPassword = forgotPasswordLink.waitForExists(
                TimeUnit.MILLISECONDS.convert(1000L, TimeUnit.SECONDS));
        assertTrue("Forgot password not found", firstAttempt ||needsPassword);
        if ( !needsPassword ) {
            Log.i("Login", "Retry google login");
            device.pressHome();
            TimeUnit.SECONDS.sleep(5);
            return loginGoogleApp(instrumentation, false);
        }

        Log.i("Login", "enter password");
        editInput.setText("2u0of9osen");
        clickNext(device);

        boolean isSignedIn =
                new watcher(device, Res.GOOGLE_APP_CONF_WATCHER_PATTERN).checkForCondition();

        if ((api >= 24 && api <= 28) || api == 32) {
            UiObject signInConsentButton = api == 32 ?
                    device.findObject(
                            new UiSelector().resourceId(Res.CHROME_TERMS_ACCEPT_BUTTON_RES)) :
                    device.findObject(
                            new UiSelector().resourceId(Res.GOOGLE_SIGN_IN_CONSENT_NEXT_RES));
            if (signInConsentButton.waitForExists(20L)) {
                signInConsentButton.click();
                isSignedIn = true;
            }
        }

        assertTrue("Login failed", firstAttempt || isSignedIn);
        if ( !isSignedIn ) {
            Log.i("Login", "Retry google login");
            device.pressHome();
            TimeUnit.SECONDS.sleep(5);
            return loginGoogleApp(instrumentation, false);
        }

        final UiScrollable scrollable = new UiScrollable(new UiSelector().scrollable(true));
        scrollable.setAsVerticalList();
        if (scrollable.exists()) {
            scrollable.scrollToEnd(10);
        }

        UiObject backupSwitch = device.findObject(new UiSelector().resourceId(Res.GOOGLE_BACKUP_SWITCH_RES));
        if (backupSwitch.waitForExists(TimeUnit.MILLISECONDS.convert(3L, TimeUnit.SECONDS))) {
            backupSwitch.click();
        }

        UiObject agreeButton = api >= 31 ?
                device.findObject(
                        new UiSelector().className("android.widget.Button").text("I agree")) :
                device.findObject(
                        new UiSelector().resourceId(Res.GOOGLE_SERVICES_ACCEPT_BUTTON_RES));

        if (agreeButton.exists()){
            agreeButton.clickAndWaitForNewWindow();
        }

        UiObject moreButton = device.findObject(new UiSelector().textMatches("(?i)more(?-i)"));
        if (moreButton.waitForExists(TimeUnit.MILLISECONDS.convert(3L, TimeUnit.SECONDS))) {
            moreButton.clickAndWaitForNewWindow();
        }

        new watcher(device, Res.GOOGLE_APP_CONT_WATCHER_PATTERN).checkForCondition();

        agreeButton = device.findObject(new UiSelector().textMatches("(?i)agree(?-i)"));
        if (agreeButton.waitForExists(TimeUnit.MILLISECONDS.convert(3L, TimeUnit.SECONDS))) {
            agreeButton.clickAndWaitForNewWindow();
        }

        UiObject gotItButton = device.findObject(new UiSelector().textMatches("(?i)ok, got it(?-i)"));
        if (gotItButton.waitForExists(TimeUnit.MILLISECONDS.convert(3L, TimeUnit.SECONDS))) {
            gotItButton.clickAndWaitForNewWindow();
        }

        UiObject yesImInButton = device.findObject(new UiSelector().textMatches("(?i)yes, i'm in(?-i)"));
        if (yesImInButton.waitForExists(TimeUnit.MILLISECONDS.convert(3L, TimeUnit.SECONDS))) {
            yesImInButton.clickAndWaitForNewWindow();
        }

        device.pressHome();
        TimeUnit.SECONDS.sleep(10);
        return true;
    }

    public static boolean logoutGoogleChrome(Instrumentation instrumentation) throws Exception {
        final UiDevice device = UiDevice.getInstance(instrumentation);

        GoogleAppUtil.openChromeSettings(instrumentation);

        final UiObject androidIconButton = api == 31 ?
                device.findObject(
                        new UiSelector().resourceId(Res.CHROME_SIGNIN_PROMO_BUTTON_RES)) :
                device.findObject(
                        new UiSelector().resourceId(Res.ANDROID_ICON_RES).
                                className("android.widget.ImageView"));

        if (new Wait().until(androidIconButton::exists)) {
            androidIconButton.clickAndWaitForNewWindow();
        }

        refuseSync(device);

        if (api >= 31) {
            final UiObject emailLabel = device.findObject(
                    new UiSelector().text(email).resourceId(Res.ANDROID_SUMMARY_RES));
            if (new Wait().until(emailLabel::exists)) {
                emailLabel.clickAndWaitForNewWindow();
            }
        }

        final UiObject signOutLabel = api >= 31 ?
                device.findObject(new UiSelector().text("Sign out and turn off sync")) :
                device.findObject(new UiSelector().text("Sign out of Chrome"));

        if (new Wait().until(signOutLabel::exists)) {
            signOutLabel.clickAndWaitForNewWindow();
            new watcher(device, Res.GOOGLE_APP_CONT_WATCHER_PATTERN).checkForCondition();
        }

        final UiObject signOutButton = device.findObject(new UiSelector().textMatches("(?i)(SIGN OUT)(?-i)"));

        if (new Wait().until(signOutButton::exists)) {
            signOutButton.clickAndWaitForNewWindow();
        }


        for (int i = 0; i < 3; i++) {
            UiObject loggedInUser =
                    device.findObject(new UiSelector().text(email));
            if (new Wait().until(loggedInUser::exists)) {
                loggedInUser.clickAndWaitForNewWindow();
            }
        }

        for (int i = 0; i < 2; i++) {
            UiObject removeAccountButton = device.findObject(
                    new UiSelector().textMatches("(?i)remove account(?-i)").className("android.widget.Button"));
            if (new Wait().until(removeAccountButton::exists)) {
                removeAccountButton.clickAndWaitForNewWindow();
            }
        }


        String signInText = api >= 30 ? "Turn on sync" : "Sign in to Chrome";
        final UiObject signInLabel = device.findObject(new UiSelector().text(signInText));
        final UiObject signInPromoCloseButton = device.findObject(
                new UiSelector().resourceId(Res.CHROME_SIGNIN_PROMO_CLOSE_RES));
        final UiObject addAccountButton = device.findObject(
                new UiSelector().text("Add account"));

        return new Wait().until(signInLabel::exists) || new Wait().until(signInPromoCloseButton::exists)
                || new Wait().until(addAccountButton::exists);
    }

    private static void openChromeSettings(Instrumentation instrumentation) throws Exception {
        UiDevice device = UiDevice.getInstance(instrumentation);

        AppLauncher.launch(instrumentation, "Chrome");

        UiObject termsAcceptButton = device.findObject(new UiSelector().
                resourceId(Res.CHROME_TERMS_ACCEPT_BUTTON_RES));
        if (termsAcceptButton.waitForExists(TimeUnit.MILLISECONDS.convert(3L, TimeUnit.SECONDS))) {
            termsAcceptButton.clickAndWaitForNewWindow();
        }

        refuseSync(device);

        UiObject nextButton = device.findObject(new UiSelector().
                resourceId(Res.GOOGLE_SERVICES_NEXT_BUTTON_RES));
        if (nextButton.waitForExists(TimeUnit.MILLISECONDS.convert(3L, TimeUnit.SECONDS))) {
            nextButton.clickAndWaitForNewWindow();
        }

        final UiObject chromeUpdateButton = device.findObject(
                new UiSelector().resourceId(Res.CHROME_MENU_BADGE_RES)
        );

        if (new Wait().until(chromeUpdateButton::exists)) {
            chromeUpdateButton.clickAndWaitForNewWindow();
        }

        final UiObject chromeMenuButton = device.findObject(
                new UiSelector().resourceId(Res.CHROME_MENU_BUTTON_RES));

        if (new Wait().until(chromeMenuButton::exists)) {
            chromeMenuButton.clickAndWaitForNewWindow();
        }

        final UiObject settingsButton = device.findObject(new UiSelector().text("Settings"));

        if (new Wait().until(settingsButton::exists)) {
            settingsButton.clickAndWaitForNewWindow();
        }
    }

    private static void clickNext(UiDevice device) throws UiObjectNotFoundException{
        UiObject nextButton = device.findObject(new UiSelector().textMatches(("(?i)next(?-i)")));
        if (!nextButton.waitForExists(TimeUnit.MILLISECONDS.convert(3L, TimeUnit.SECONDS))) {
            nextButton = device.findObject(new UiSelector().descriptionMatches(("(?i)next(?-i)")));
        }

        if (!nextButton.exists()) {
            nextButton = device.findObject(new UiSelector().resourceId(("identifierNext")));
        }

        if (!nextButton.exists()) {
            nextButton = device.findObject(new UiSelector().resourceId(("passwordNext")));
        }

        if (nextButton.exists()) {
            nextButton.clickAndWaitForNewWindow(10L);
        }
    }

    public static void refuseSync(UiDevice device) throws Exception {
        UiObject noThanksButton = device.findObject(new UiSelector().
                resourceIdMatches(Res.CHROME_NO_THANKS_BUTTON_RES));
        if (noThanksButton.waitForExists(TimeUnit.MILLISECONDS.convert(3L, TimeUnit.SECONDS))) {
            noThanksButton.clickAndWaitForNewWindow();
        }
    }

    public static String getUserEmail() {
        return email;
    }
}