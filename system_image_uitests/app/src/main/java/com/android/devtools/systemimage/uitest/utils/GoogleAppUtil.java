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
import android.support.test.uiautomator.UiScrollable;
import com.android.devtools.systemimage.uitest.common.Res;
import com.android.devtools.systemimage.uitest.watchers.AddGoogleAccountWatcher;
import com.android.devtools.systemimage.uitest.watchers.GoogleAppConfirmationWatcher;
import com.android.devtools.systemimage.uitest.watchers.GoogleAppContinueWatcher;

import java.util.concurrent.TimeUnit;

import android.util.Log;
import static com.android.devtools.systemimage.uitest.utils.PackageInstallationUtil.testFramework;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

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
     *  @param instrumentation
     *  @return boolean flag indicating success
     */
    public static boolean loginGoogleApp(Instrumentation instrumentation) throws Exception {
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

        boolean isSignedIn = false;
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

        if (hasEditInput) {
            Log.i("Login", "found email field");
            UiObject inputEmailField = device.findObject(new UiSelector().description("Email or phone"));
            UiObject forgotEmailLink = api >= 28 ? device.findObject(new UiSelector().text("Forgot email?")) :
                    device.findObject(new UiSelector().description("Forgot email?"));

            boolean needsEmail = api == 24 ? inputEmailField.waitForExists(
                    TimeUnit.MILLISECONDS.convert(10L, TimeUnit.SECONDS)) :
                    forgotEmailLink.waitForExists(TimeUnit.MILLISECONDS.convert(10L, TimeUnit.SECONDS));

            Log.i("Login", "enter email");
            editInput.clearTextField();
            editInput.setText(email);
            clickNext(device);

            UiObject forgotPasswordLink = api >= 28 ? device.findObject(new UiSelector().text("Forgot password?")) :
                    device.findObject(new UiSelector().description("Forgot password?"));
            boolean needsPassword = forgotPasswordLink.waitForExists(
                    TimeUnit.MILLISECONDS.convert(3L, TimeUnit.SECONDS));

            Log.i("Login", "enter password");
            editInput.clearTextField();
            editInput.setText(password);
            clickNext(device);
        }

        isSignedIn = new GoogleAppConfirmationWatcher(device).checkForCondition();
        Log.i("Login", "isSignedIn = " + isSignedIn);

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
        TimeUnit.SECONDS.sleep(30);
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


 /**
     * Log user into Google account.
     * @param instrumentation
     * @return
     * @throws Exception
     *
     *  Keeping the test flow very basic with the aim to follow steps to sign-in Google account via Settings.
     * Steps:
     * 1. Go to Settings -> Users & Accounts
     * 2. Check for already existing Google accounts
     * 3. I not found, Add an Account using Google credentials
     */
    public static boolean loginGoogleAccount(Instrumentation instrumentation) throws Exception{

        final UiDevice device = UiDevice.getInstance(instrumentation);

        if (!testFramework.isGoogleApiAndPlayImage() && !testFramework.isGoogleApiImage()) {
            return false;
        }

        AppLauncher.launch(instrumentation, "Settings");
        UiScrollable itemList =
                new UiScrollable(
                        new UiSelector().resourceIdMatches(Res.SETTINGS_LIST_CONTAINER_RES)
                );
        itemList.setAsVerticalList();

        String accountsLabel = "Users & accounts";
        UiObject accounts = itemList.getChildByText(new UiSelector().className("android.widget.TextView"),
                accountsLabel);
        accounts.clickAndWaitForNewWindow();

        // Check for already existing account
        final UiObject emailTextViewClass = device.findObject(new UiSelector().className("android.widget.TextView"));
        final UiObject googleEmailText = device.findObject(new UiSelector().textMatches("Google"));
        boolean hasSignedInEmail = new Wait(10L).
                until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() {
                        return emailTextViewClass.exists() && googleEmailText.exists() ;
                    }
                });
        if(hasSignedInEmail){
            return true;
        }

        device.findObject(new UiSelector().text("Add account")).clickAndWaitForNewWindow();
        device.findObject(new UiSelector().text("Google")).clickAndWaitForNewWindow(10L);

        TimeUnit.SECONDS.sleep(5);
        final UiObject editInputClass = device.findObject(new UiSelector().className("android.widget.EditText"));
        final UiObject editInputText = device.findObject(new UiSelector().textMatches("Email or phone"));
        final UiObject editInputPassword = device.findObject(new UiSelector().textMatches("Enter your password"));
        boolean hasEditEmail = new Wait(10L).
                until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() {
                        return editInputClass.exists() || editInputText.exists() ;
                    }
                });
        assertTrue("Cannot find Email edit text", hasEditEmail);

        editInputText.clearTextField();
        editInputText.setText(email);
        clickNext(device);

        editInputPassword.clearTextField();
        editInputPassword.setText(password);
        clickNext(device);

        // The "I agree" button below confirms Google sign-in. Following code are just the steps in app flow.
        new GoogleAppConfirmationWatcher(device).checkForCondition();

        final UiObject backupSwitch = device.findObject(new UiSelector().resourceId("com.google.android.gms:id/suw_items_switch"));
        final UiObject backupSwitch2 = device.findObject(new UiSelector().resourceId("com.google.android.gms:id/sud_navbar_next"));
        final UiObject backupSwitch3 = device.findObject(new UiSelector().resourceId("com.google.android.gms:id/sud_items_switch"));
        boolean hasBackupSwitch = new Wait(10L).
                until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() {
                        return backupSwitch.exists() || backupSwitch2.exists() || backupSwitch3.exists() ;
                    }
                });
        if(hasBackupSwitch){
            if(backupSwitch.exists()){
                backupSwitch.clickAndWaitForNewWindow(10L);
            }else if(backupSwitch2.exists()){
                backupSwitch2.clickAndWaitForNewWindow(10L);
            }
            else{
                backupSwitch3.clickAndWaitForNewWindow(10L);
            }
        }


        final UiObject moreNavbar = device.findObject(new UiSelector().resourceId(Res.GOOGLE_MORE_NAVBAR_RES));
        final UiObject moreNavbar2 = device.findObject(new UiSelector().resourceId("com.google.android.gms:id/sud_navbar_more"));
        boolean hasNavBar = new Wait(10L).
                until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() {
                        return moreNavbar.exists() || moreNavbar2.exists() ;
                    }
                });
        if(hasNavBar){
            if(moreNavbar.exists()){
                moreNavbar.clickAndWaitForNewWindow();
            }
            else{
                moreNavbar2.clickAndWaitForNewWindow();
            }
        }

        final UiObject acceptButtonTxt = device.findObject(new UiSelector().textMatches("AGREE")); // Fresh avd, first time login
        final UiObject acceptButtonTxt2 = device.findObject(new UiSelector().textMatches("ACCEPT")); // Second time login
        boolean hasAcceptBtn = new Wait(10L).
                until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() {
                        return acceptButtonTxt.exists() || acceptButtonTxt2.exists() ;
                    }
                });
        if(hasAcceptBtn){
            if(acceptButtonTxt.exists()){
                acceptButtonTxt.clickAndWaitForNewWindow(10L);
            }else{
                acceptButtonTxt2.clickAndWaitForNewWindow(10L);
            }

        }

        // Since the next screen is FLAKY and not essentially "Users and account screen", we press home first
        device.pressHome();

        AppLauncher.launch(instrumentation, "Settings");
        UiScrollable itemList2 =
                new UiScrollable(
                        new UiSelector().resourceIdMatches(Res.SETTINGS_LIST_CONTAINER_RES)
                );
        itemList2.setAsVerticalList();

        String accountsLabel2 = "Users & accounts";
        UiObject accounts2 = itemList.getChildByText(new UiSelector().className("android.widget.TextView"),
                accountsLabel2);
        accounts2.clickAndWaitForNewWindow();

 //       assertTrue("Cannot find signed-in email in Users and Account Screen", hasSignedInEmail);

        return new Wait(10L).
                until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() {
                        return  googleEmailText.exists() ;
                    }
                });
    }

    public static boolean logoutGoogleAccount(Instrumentation instrumentation) throws Exception{
        final UiDevice device = UiDevice.getInstance(instrumentation);

        AppLauncher.launch(instrumentation, "Settings");
        UiScrollable itemList =
                new UiScrollable(
                        new UiSelector().resourceIdMatches(Res.SETTINGS_LIST_CONTAINER_RES)
                );
        itemList.setAsVerticalList();

        String accountsLabel = "Users & accounts";
        UiObject accounts = itemList.getChildByText(new UiSelector().className("android.widget.TextView"),
                accountsLabel);
        accounts.clickAndWaitForNewWindow();

        // Check for already existing account
        final UiObject emailTextViewClass = device.findObject(new UiSelector().className("android.widget.TextView"));
        final UiObject googleEmailText = device.findObject(new UiSelector().textMatches("Google"));
        boolean hasSignedInEmail = new Wait(10L).
                until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() {
                        return emailTextViewClass.exists() && googleEmailText.exists() ;
                    }
                });

        if(hasSignedInEmail){
            googleEmailText.clickAndWaitForNewWindow(10L);
            UiObject removeAccount = device.findObject(
                    new UiSelector().textMatches("REMOVE ACCOUNT"));
            removeAccount.clickAndWaitForNewWindow();
            removeAccount.clickAndWaitForNewWindow();
        }

        return new Wait(5L).
                until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() {
                        return !googleEmailText.exists() ;
                    }
                });

    }


    private static void openChromeSettings(Instrumentation instrumentation) throws Exception {
        UiDevice device = UiDevice.getInstance(instrumentation);

        AppLauncher.launch(instrumentation, "Chrome");

        UiObject termsAcceptButton = device.findObject(new UiSelector().
                resourceId(Res.CHROME_TERMS_ACCEPT_BUTTON_RES));
        if (termsAcceptButton.waitForExists(TimeUnit.MILLISECONDS.convert(3L, TimeUnit.SECONDS))) {
            termsAcceptButton.clickAndWaitForNewWindow();
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
