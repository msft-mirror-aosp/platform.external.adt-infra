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
import androidx.test.uiautomator.UiDevice;
import androidx.test.uiautomator.UiObject;
import androidx.test.uiautomator.UiObjectNotFoundException;
import androidx.test.uiautomator.UiScrollable;
import androidx.test.uiautomator.UiSelector;
import com.android.devtools.systemimage.uitest.common.Res;
import com.android.devtools.systemimage.uitest.watchers.watcher;
import java.util.concurrent.TimeUnit;
import android.util.Log;

import org.junit.Assert;

import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

/**
 * Static utility method pertaining to Google Apps
 */
public class GoogleAppUtil {

    private GoogleAppUtil() {
        throw new AssertionError();
    }

    private static final int api = SystemUtil.getApiLevel();
    private static final String email = "sysimgui.tester1@gmail.com";
    private static final String password = "kejpj6dmzj";

    public static String getUserEmail() {
        return email;
    }
    public static String getUserPassword() {
        return password;
    }

    /**
     * Log a user into a Google application
     *
     * @param instrumentation the instrumentation instance
     * @param firstAttempt indicates if it's the first attempt to log in
     * @return boolean flag indicating success
     * @throws Exception if an error occurs during the login process
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
        if (accountPromoButton.waitForExists(10L)) {
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
        UiObject chromePositiveButton = device.findObject(
                new UiSelector().resourceId(Res.CHROME_POSITIVE_BUTTON_RES));

        UiObject testUserEmail = device.findObject(new UiSelector().text(getUserEmail()));
        UiObject accountSelectionMark = device.findObject(new UiSelector().resourceId(
                Res.CHROME_ACCOUNT_SELECTION_MARK_RES));
        UiObject continueButton = device.findObject(
                new UiSelector()
                        .text("Continue")
                        .className("android.widget.Button")
                        .resourceId(Res.CHROME_POSITIVE_BUTTON_RES));
        if (testUserEmail.waitForExists(5L)
                && accountSelectionMark.waitForExists(3L) &&
                continueButton.waitForExists(3L)) {
            continueButton.clickAndWaitForNewWindow();
            if (chromePositiveButton.waitForExists(5L)) {
                chromePositiveButton.clickAndWaitForNewWindow();
                return true;
            }
        }

        UiObject addAccountLabel = device.findObject(
                new UiSelector().text("Add account"));
        if (addAccountLabel.waitForExists(5L)) {
            addAccountLabel.clickAndWaitForNewWindow();
        }

        if (testUserEmail.waitForExists(5L)) {
            new watcher(device, Res.GOOGLE_APP_CONT_WATCHER_PATTERN).checkForCondition();
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
        editInput.setText(getUserEmail());
        clickNext(device);

        assertTrue("Forgot email link not dismissed.",
                forgotEmailLink.waitUntilGone(90000L));

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
        editInput.setText(getUserPassword());
        clickNext(device);

        assertTrue("Forgot password link not dismissed.",
                forgotPasswordLink.waitUntilGone(90000L));

        boolean isSignedIn =
                new watcher(device, Res.GOOGLE_APP_CONF_WATCHER_PATTERN).checkForCondition();

        if ((api >= 24 && api <= 29) || api >= 31) {
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

        if (!isSignedIn) {
            if (firstAttempt) {
                Log.i("Login", "Retry google login");
                device.pressHome();
                TimeUnit.SECONDS.sleep(5);
                return loginGoogleApp(instrumentation, false);
            } else {
                fail("Google Services account login attempt failed");
            }
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

        UiObject acceptButton = api >= 29 ?
                device.findObject(new UiSelector().textMatches("(?i)accept(?-i)")) :
                device.findObject(
                        new UiSelector().resourceId(Res.GOOGLE_SERVICES_ACCEPT_BUTTON_RES));

        UiObject agreeButton = device.findObject(
                new UiSelector().textMatches("(?i)agree(?-i)"));

        if (acceptButton.exists()) {
            acceptButton.clickAndWaitForNewWindow();
        } else if (agreeButton.exists()) {
            agreeButton.clickAndWaitForNewWindow();
        }

        UiObject moreButton = device.findObject(new UiSelector().textMatches("(?i)more(?-i)"));
        if (moreButton.waitForExists(TimeUnit.MILLISECONDS.convert(3L, TimeUnit.SECONDS))) {
            moreButton.clickAndWaitForNewWindow();
        }

        new watcher(device, Res.GOOGLE_APP_CONT_WATCHER_PATTERN).checkForCondition();

        if (acceptButton.waitForExists(TimeUnit.MILLISECONDS.convert(3L, TimeUnit.SECONDS))) {
            agreeButton.clickAndWaitForNewWindow();
        } else if (agreeButton.waitForExists(TimeUnit.MILLISECONDS.convert(3L, TimeUnit.SECONDS))) {
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

    /**
     * Log a user out of the Google Chrome application
     *
     * @param instrumentation the instrumentation instance
     * @return boolean flag indicating success
     * @throws Exception if an error occurs during the logout process
     */
    public static boolean logoutGoogleChrome(Instrumentation instrumentation) throws Exception {
        boolean result = false;

        try {
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
                        new UiSelector().text(getUserEmail()).resourceId(Res.ANDROID_SUMMARY_RES));
                if (new Wait().until(emailLabel::exists)) {
                    emailLabel.clickAndWaitForNewWindow();
                    emailLabel.waitUntilGone(3000L);
                }
            }

            final UiObject signOutLabel = api >= 31 ?
                    device.findObject(new UiSelector().text("Sign out and turn off sync")) :
                    device.findObject(new UiSelector().text("Sign out of Chrome"));

            if (new Wait().until(signOutLabel::exists)) {
                signOutLabel.clickAndWaitForNewWindow();
                signOutLabel.waitUntilGone(3000L);
                new watcher(device, Res.GOOGLE_APP_CONT_WATCHER_PATTERN).checkForCondition();
            }

            final UiObject signOutButton = device.findObject(new UiSelector().textMatches("(?i)(SIGN OUT)(?-i)"));

            if (new Wait().until(signOutButton::exists)) {
                signOutButton.clickAndWaitForNewWindow();
                signOutButton.waitUntilGone(3000L);
            }

            for (int i = 0; i < 3; i++) {
                UiObject loggedInUser =
                        device.findObject(new UiSelector().text(getUserEmail()));
                if (new Wait().until(loggedInUser::exists)) {
                    loggedInUser.clickAndWaitForNewWindow();
                }
            }

            for (int i = 0; i < 2; i++) {
                UiObject removeAccountButton = device.findObject(
                        new UiSelector().textMatches("(?i)remove account(?-i)").className("android.widget.Button"));
                if (new Wait().until(removeAccountButton::exists)) {
                    removeAccountButton.clickAndWaitForNewWindow();
                    removeAccountButton.waitUntilGone(3000L);
                }
            }


            String signInText = api >= 30 ? "Turn on sync" : "Sign in to Chrome";
            final UiObject signInLabel = device.findObject(new UiSelector().text(signInText));
            final UiObject signInPromoCloseButton = device.findObject(
                    new UiSelector().resourceId(Res.CHROME_SIGNIN_PROMO_CLOSE_RES));
            final UiObject addAccountButton = device.findObject(
                    new UiSelector().text("Add account"));

            result =  new Wait().until(signInLabel::exists) || new Wait().until(signInPromoCloseButton::exists)
                    || new Wait().until(addAccountButton::exists);

        } catch (Exception e) {
            Assert.fail("Failed to logout from Google Chrome with exception: " + e);
        }
        return result;
    }

    /**
     * Open the settings of the Google Chrome application.
     * This method interacts with the UI of the Google Chrome app on an Android device
     * and opens the settings menu.
     *
     * @param instrumentation the instrumentation instance
     * @throws Exception if an error occurs during the operation
     */
    private static void openChromeSettings(Instrumentation instrumentation) throws Exception {
        UiDevice device = UiDevice.getInstance(instrumentation);

        AppLauncher.launch(instrumentation, "Chrome");

        UiObject addAccountToDeviceButton = device.findObject(
                new UiSelector().resourceId("com.android.chrome:id/signin_fre_continue_button"));
        if (addAccountToDeviceButton.waitForExists(TimeUnit.SECONDS.toMillis(20))) {
            addAccountToDeviceButton.clickAndWaitForNewWindow();
        }

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

    /**
     * Clicks on the "Next" button in the UI of the Android device.
     * This method is used to automate UI interactions, specifically when a "Next" button needs to be clicked.
     *
     * @param device the UiDevice instance representing the device on which the test is currently running
     * @throws UiObjectNotFoundException if the "Next" button is not found in the UI
     */
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

    /**
     * Refuses the sync operation in the Google Chrome application.
     * This method interacts with the UI of the Google Chrome app on an Android device
     * and clicks on the "No Thanks" button when the sync operation prompt appears.
     *
     * @param device the UiDevice instance representing the device on which the test is currently running
     * @throws Exception if any error occurs during the operation
    */
    public static void refuseSync(UiDevice device) throws Exception {
        UiObject noThanksButton = device.findObject(new UiSelector().
                resourceIdMatches(Res.CHROME_NO_THANKS_BUTTON_RES));
        if (noThanksButton.waitForExists(TimeUnit.MILLISECONDS.convert(3L, TimeUnit.SECONDS))) {
            noThanksButton.clickAndWaitForNewWindow();
        }
    }
}
