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
import static org.junit.Assert.assertTrue;

/**
 * Static utility methods pertaining to the Google Play Store
 */
public class PlayStoreUtil {

    private PlayStoreUtil() {
        throw new AssertionError();
    }

    /**
     * Version 1 for api = 24
     *
     * Checks if Play Store has been installed.
     * Returns true if Play Store has been installed, false if not.
     */
    public static boolean isPlayStoreInstalled_v1(Instrumentation instrumentation) throws Exception {
        final UiDevice device = UiDevice.getInstance(instrumentation);
        boolean isInstalled;
        final String playStore = "Play Store";

        device.pressHome();
        device.findObject(new UiSelector().descriptionContains("Apps")).clickAndWaitForNewWindow();

        final UiScrollable scrollable = new UiScrollable(new UiSelector().scrollable(true));
        isInstalled = new Wait().until(() -> {
            scrollable.scrollIntoView(new UiSelector().text(playStore));
            return scrollable.getChild(new UiSelector().text(playStore)).exists();
        });

        return isInstalled;
    }

    /**
     * Version 2 for 25 <= api
     *
     * Checks if Play Store has been installed.
     * Returns true if Play Store has been installed, false if not.
     */
    public static boolean isPlayStoreInstalled_v2(Instrumentation instrumentation) throws Exception {
        final UiDevice device = UiDevice.getInstance(instrumentation);
        boolean isInstalled;
        final String playStore = "Play Store";

        device.pressHome();

        isInstalled = new Wait(TimeUnit.MILLISECONDS.convert(3L, TimeUnit.SECONDS)).
            until(() -> device.findObject(new UiSelector().text(playStore)).exists() ||
                device.findObject(new UiSelector().description(playStore)).exists());

        return isInstalled;
    }

    /**
     * Backtracks to the opening Play Store screen.
     */
    public static void resetPlayStore(Instrumentation instrumentation) {
        final UiDevice device = UiDevice.getInstance(instrumentation);

        for (int i = 0; i < 5; i++) {
            device.pressBack();
        }
    }

    /**
     * Launches Google Play Store, opening to the given application
     */
    private static void launchGooglePlay(Instrumentation instrumentation, String appName) throws Exception {
        final UiDevice device = UiDevice.getInstance(instrumentation);
        AppLauncher.launch(instrumentation, "Play Store");

        resetPlayStore(instrumentation);
        AppLauncher.launch(instrumentation, "Play Store");

        boolean idleTextFieldExists = new Wait().until(() -> device.findObject(
            new UiSelector().resourceIdMatches(Res.GOOGLE_PLAY_IDLE_RES)).exists());

        if (idleTextFieldExists) {
            device.findObject(
                new UiSelector().resourceIdMatches(Res.GOOGLE_PLAY_IDLE_RES)).click();
        }

        boolean inputTextFieldExists = new Wait().until(() -> device.findObject(
            new UiSelector().resourceIdMatches(Res.GOOGLE_PLAY_INPUT_RES)).exists());

        assertTrue("Input text field not found", inputTextFieldExists);

        UiObject inputTextField = device.findObject(
            new UiSelector().resourceIdMatches(Res.GOOGLE_PLAY_INPUT_RES));
        inputTextField.clearTextField();
        inputTextField.setText(appName);
        device.pressEnter();
    }

    /**
     * Checks if test user is logged in to Google Play.  Logs in if not.
     */
    public static boolean loginGooglePlay(Instrumentation instrumentation) throws Exception {
        final UiDevice device = UiDevice.getInstance(instrumentation);
        resetPlayStore(instrumentation);
        AppLauncher.launch(instrumentation, "Play Store");
        new watcher(device, Res.GOOGLE_APP_CONF_WATCHER_PATTERN).checkForCondition();

        boolean loggedIn = new Wait(TimeUnit.SECONDS.toMillis(5)).
            until(() -> device.findObject(
                new UiSelector().resourceIdMatches(Res.GOOGLE_PLAY_IDLE_RES)).exists() ||
                device.findObject(
                    new UiSelector().resourceId(Res.GOOGLE_PLAY_ACTIVE_RES)).exists());
        if (loggedIn) {
            return true;
        }

        final UiObject unauthorizedUserButton = device.findObject(
            new UiSelector().resourceId((Res.GOOGLE_UNAUTHORIZED_SIGN_IN_RES)));
        boolean unauthorizedUser = new Wait().
            until(unauthorizedUserButton::exists);
        if (unauthorizedUser) {
            unauthorizedUserButton.clickAndWaitForNewWindow();
        }

        loggedIn = GoogleAppUtil.loginGoogleApp(instrumentation, true);
        AppLauncher.launch(instrumentation, "Play Store");

        new watcher(device, Res.GOOGLE_APP_CONF_WATCHER_PATTERN).checkForCondition();

        final UiObject onboardButton = device.findObject(
            new UiSelector().resourceId(Res.GOOGLE_PLAY_ONBOARD_BUTTON_RES));

        boolean hasOnboardButton = new Wait(TimeUnit.SECONDS.toMillis(5)).
            until(onboardButton::exists);

        if (hasOnboardButton) {
            onboardButton.clickAndWaitForNewWindow();
        }

        new watcher(device, Res.GOOGLE_APP_CONF_WATCHER_PATTERN).checkForCondition();

        return loggedIn;
    }

    /**
     * Attempts to install an application from Google Play Store, if it is not already installed.
     * Returns true if the application has been installed, false if not.
     */
    public static boolean installApplication(Instrumentation instrumentation) throws Exception {
        final UiDevice device = UiDevice.getInstance(instrumentation);

        boolean isInstallable = new Wait(TimeUnit.MILLISECONDS.convert(10L, TimeUnit.SECONDS)).until(new Wait.ExpectedCondition() {
            @Override
            public boolean isTrue() {
                return device.findObject(new UiSelector().textMatches("(?i)install(?-i)")).exists();
            }
        });

        if (!isInstallable) {
            return new Wait().until(() -> device.findObject(new UiSelector().textMatches("(?i)uninstall(?-i)")).exists());
        }

        device.findObject(new UiSelector().textMatches("(?i)install(?-i)")).clickAndWaitForNewWindow();
        new watcher(device, Res.GOOGLE_APP_CONF_WATCHER_PATTERN).checkForCondition();

        UiObject openButton = device.findObject(new UiSelector().textMatches("(?i)open(?-i)"));

        return openButton.waitForExists(TimeUnit.SECONDS.toMillis(180));
    }

    /**
     * Attempts to uninstall an application from Google Play Store, if it is already installed.
     * Returns true if the application has been uninstalled, false if not.
     */
    public static boolean uninstallApplication(Instrumentation instrumentation) throws Exception {
        final UiDevice device = UiDevice.getInstance(instrumentation);

        boolean isUninstallable = new Wait(
            TimeUnit.MILLISECONDS.convert(10L, TimeUnit.SECONDS))
            .until(() -> device.findObject(new UiSelector()
                .textMatches("(?i)uninstall(?-i)")).exists());

        if (!isUninstallable) {
            return new Wait().until(() -> device.findObject(new UiSelector()
                .textMatches("(?i)install(?-i)")).exists());
        }

        device.findObject(new UiSelector().textMatches("(?i)uninstall(?-i)")).clickAndWaitForNewWindow();
        device.findObject(new UiSelector().textMatches("(?i)ok(?-i)")).clickAndWaitForNewWindow();

        UiObject installButton = device.findObject(new UiSelector()
            .textMatches("(?i)install(?-i)"));

        return installButton.waitForExists(TimeUnit.SECONDS.toMillis(60));
    }

    /**
     * Selects an application listed in Play Store, if found.
     */
    public static void selectApplication(Instrumentation instrumentation,
        String application) throws Exception {
        final UiDevice device = UiDevice.getInstance(instrumentation);

        boolean isFound = hasTestApp(instrumentation, application);
        if (isFound) {
            UiObject testAppListing = device.findObject(new UiSelector()
                .descriptionContains(application).resourceId(Res.GOOGLE_PLAY_VENDING_CARD_RES));
            if (testAppListing.waitForExists(5L)) {
                testAppListing.clickAndWaitForNewWindow();
            }

            UiObject testAppPage = device.findObject(new UiSelector()
                .textContains(application).resourceId(Res.GOOGLE_PLAY_VENDING_TITLE_RES));
            if (testAppPage.waitForExists(5L)) {
                testAppPage.clickAndWaitForNewWindow();
            }
        }
    }

    /**
     * Helper to search Google Play for an application by description.
     * Return true if found, false if not.
     */
    public static boolean hasTestApp(Instrumentation instrumentation, final String application)
        throws Exception {
        final UiDevice device = UiDevice.getInstance(instrumentation);
        device.pressHome();

        String appName = application.toLowerCase();
        PlayStoreUtil.launchGooglePlay(instrumentation, appName);

        new watcher(device, Res.PLAY_STORE_WATCHER_PATTERN).checkForCondition();
        return device.findObject(new UiSelector().resourceId("com.android.vending:id/right_button"))
            .waitForExists(10L);
    }
    /**
     * Opens the Parental Controls menu
     */
    private static void openParentalControls(UiDevice testDevice) throws Exception {

        UiObject backButton =  testDevice.findObject(new UiSelector().description("Back"));
        if (backButton.waitForExists(3)) {
            backButton.clickAndWaitForNewWindow();
        }

        UiObject navigationDrawer = testDevice.findObject(new UiSelector().
            description("Show navigation drawer"));
        if (navigationDrawer.waitForExists(TimeUnit.SECONDS.toMillis(10L))) {
            navigationDrawer.clickAndWaitForNewWindow();
        }

        final UiScrollable scrollable = new UiScrollable(new UiSelector().scrollable(true));
        final UiObject settingsLink = scrollable.getChild(new UiSelector().text("Settings"));
        settingsLink.waitForExists(3L);
        if (!settingsLink.exists()) {
            new Wait().until(() -> {
                int swipes = 0;
                while (!settingsLink.exists() && swipes < 20) {
                    scrollable.flingForward();
                    swipes++;
                }
                return settingsLink.exists();
            });
        }
        if (settingsLink.exists()) {
            settingsLink.clickAndWaitForNewWindow();
        }

        final UiObject parentalControlsButton = scrollable.getChild(new UiSelector().text(
            "Parental controls"));
        parentalControlsButton.waitForExists(3L);
        if (!parentalControlsButton.exists()) {
            new Wait().until(() -> {
                scrollable.scrollIntoView(parentalControlsButton);
                return parentalControlsButton.exists();
            });
        }
        if (parentalControlsButton.exists()) {
            parentalControlsButton.clickAndWaitForNewWindow();
        }
    }

    /**
     * Toggles the Parental Controls button; on if true, off if false
     */
    public static void toggleParentalControls(UiDevice testDevice, boolean setChecked) throws Exception {
        openParentalControls(testDevice);

        final UiObject toggleButton = testDevice.findObject(new UiSelector().resourceId(
            Res.GOOGLE_PLAY_FILTER_TOGGLE_RES));

        boolean toggleButtonExists = new Wait().until(toggleButton::exists);

        if (toggleButtonExists && toggleButton.isChecked() != setChecked) {
            toggleButton.clickAndWaitForNewWindow();
            setParentalControlPin(testDevice);
        }
    }

    /**
     * Change parental control restrictions in an application category to the given ages
     */
    public static void setRestrictions(Instrumentation instrumentation,
        String category, String ages) throws Exception {
        final UiDevice device = UiDevice.getInstance(instrumentation);
        final String appCategory = category;
        toggleParentalControls(device, true);

        new Wait().until(() -> device.findObject(new UiSelector().textStartsWith(appCategory)).exists());
        device.findObject(new UiSelector().textStartsWith(appCategory)).clickAndWaitForNewWindow();
        setParentalControlPin(device);
        device.findObject(new UiSelector().text(ages))
            .waitForExists(TimeUnit.SECONDS.toMillis(3));
        device.findObject(new UiSelector().text(ages))
            .clickAndWaitForNewWindow();
        new watcher(device, Res.PLAY_STORE_WATCHER_PATTERN).checkForCondition();
        UiScrollable scrollable = new UiScrollable(new UiSelector().scrollable(true));
        scrollable.waitForExists(3L);
        if (scrollable.exists()) {
            scrollable.flingToEnd(5);
        }
        new watcher(device, Res.PLAY_STORE_WATCHER_PATTERN).checkForCondition();
        PlayStoreUtil.resetPlayStore(instrumentation);
        device.pressHome();
    }
    /**
     * Sets and then confirms a parental control pin
     */
    private static void setParentalControlPin(UiDevice testDevice) throws Exception {
        final UiDevice device = testDevice;

        boolean hasPinDialog = new Wait().until(() ->
            device.findObject(new UiSelector().text("Type PIN")).exists());

        if (!hasPinDialog) {
            return;
        }

        device.findObject(new UiSelector().text("Type PIN")).setText("1111");
        device.findObject(new UiSelector().text("OK")).clickAndWaitForNewWindow();

        boolean needsConfirmation = new Wait().until(() ->
            device.findObject(new UiSelector().text("Type PIN")).exists());

        if (needsConfirmation) {
            device.findObject(new UiSelector().text("Type PIN")).setText("1111");
            device.findObject(new UiSelector().text("OK")).clickAndWaitForNewWindow();
        }
    }
}