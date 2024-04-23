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
import androidx.test.uiautomator.UiScrollable;
import androidx.test.uiautomator.UiSelector;

import com.android.devtools.systemimage.uitest.common.Res;
import com.android.devtools.systemimage.uitest.watchers.GoogleAppConfirmationWatcher;
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

    private static final int api = SystemUtil.getApiLevel();
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
    private static void launchGooglePlay(Instrumentation instrumentation, String application)
            throws Exception {
        final UiDevice device = UiDevice.getInstance(instrumentation);
        AppLauncher.launch(instrumentation, "Play Store");
        boolean watcherConditionFound = new GoogleAppConfirmationWatcher(device).checkForCondition();
        if (watcherConditionFound) {
            resetPlayStore(instrumentation);
            AppLauncher.launch(instrumentation, "Play Store");
        }
        boolean idleTextFieldExists = new Wait().until(() -> device.findObject(
                new UiSelector().resourceIdMatches(Res.GOOGLE_PLAY_IDLE_RES)).exists());

        if (idleTextFieldExists) {
            device.findObject(
                    new UiSelector().resourceIdMatches(Res.GOOGLE_PLAY_IDLE_RES)).click();
        }

        UiObject nextButton = device.findObject(
                new UiSelector().description("Next").className("android.widget.Button"));

        if (nextButton.waitForExists(1000L)) {
            nextButton.clickAndWaitForNewWindow();
        }

        UiObject inputTextField = device.findObject(
                new UiSelector()
                        .className("android.widget.TextView")
                        .textContains("Search for"));

        assertTrue("Input text field not found", inputTextField.exists());
        inputTextField.clearTextField();
        inputTextField.click();

        UiObject editTextField = device.findObject(
                new UiSelector()
                        .className("android.widget.EditText")
                        .textContains("Search for"));
        editTextField.setText(application);
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

        final UiObject signInButton = device.findObject(
                new UiSelector().packageName("com.android.vending").textMatches("(?i)sign in(?-i)"));
        if (new Wait().until(signInButton::exists)) {
            signInButton.clickAndWaitForNewWindow();
        }

        new watcher(device, Res.GOOGLE_APP_CONF_WATCHER_PATTERN).checkForCondition();

        boolean loggedIn = new Wait(TimeUnit.SECONDS.toMillis(5)).
                until(() -> device.findObject(
                        new UiSelector().resourceIdMatches(Res.GOOGLE_PLAY_IDLE_RES)).exists() ||
                        device.findObject(
                                new UiSelector().resourceId(Res.GOOGLE_PLAY_ACTIVE_RES)).exists());
        if (loggedIn) {
            UiObject notNowButton = device.findObject(
                    new UiSelector().resourceId(Res.GOOGLE_PLAY_SECONDARY_BUTTON_RES));
            if (notNowButton.waitForExists(5L)) {
                notNowButton.clickAndWaitForNewWindow();
            }
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

        final UiObject freePlayPassButton = device.findObject(
                new UiSelector().packageName(Res.GOOGLE_PLAY_VENDING_RES).text("Not now"));

        boolean hasFreePlayPassButton = new Wait(TimeUnit.SECONDS.toMillis(5)).
                until(onboardButton::exists);

        if (hasFreePlayPassButton) {
            freePlayPassButton.clickAndWaitForNewWindow();
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

        UiObject installButton = api >= 31 ? device.findObject(
                new UiSelector().descriptionMatches("(?i)install(?-i)")) :
                device.findObject(
                        new UiSelector().textMatches("(?i)install(?-i)"));
        boolean isInstallable = new Wait(TimeUnit.MILLISECONDS.convert(
                10L, TimeUnit.SECONDS)).until(installButton::exists);

        if (!isInstallable) {
            UiSelector uninstallButtonSelector = api >= 31 ? new UiSelector().
                    descriptionMatches("(?i)uninstall(?-i)") :
                    new UiSelector().
                            textMatches("(?i)uninstall(?-i)");
            return new Wait().until(() -> device.findObject(uninstallButtonSelector).exists());
        }

        installButton.clickAndWaitForNewWindow();
        new watcher(device, Res.GOOGLE_APP_CONF_WATCHER_PATTERN).checkForCondition();

        UiObject openButton = api >= 31 ? device.findObject(
                new UiSelector().descriptionMatches("(?i)open(?-i)")) :
                device.findObject(
                        new UiSelector().textMatches("(?i)open(?-i)"));

        boolean hasOpenButton = openButton.waitForExists(TimeUnit.SECONDS.toMillis(180));
        return hasOpenButton;
    }


    /**
     * Attempts to uninstall an application from Google Play Store, if it is already installed.
     * Returns true if the application has been uninstalled, false if not.
     */
    public static boolean uninstallApplication(Instrumentation instrumentation) throws Exception {
        final UiDevice device = UiDevice.getInstance(instrumentation);

        UiSelector uninstallSelector = api >= 31 ? new UiSelector()
                .descriptionMatches("(?i)uninstall(?-i)") : new UiSelector()
                .textMatches("(?i)uninstall(?-i)");
        boolean hasUninstall = new Wait(
                TimeUnit.MILLISECONDS.convert(20L, TimeUnit.SECONDS))
                .until(() -> device.findObject(uninstallSelector).exists());

        if (!hasUninstall) {
            UiObject installedLabel = device.findObject(new UiSelector()
                    .textMatches("(?i)installed(?-i)")
                    .packageName(Res.GOOGLE_PLAY_VENDING_RES)
                    .className("android.widget.TextView"));

            boolean hasInstalledLabel = new Wait(
                    TimeUnit.MILLISECONDS.convert(20L, TimeUnit.SECONDS))
                    .until(installedLabel::exists);

            if (hasInstalledLabel) {
                installedLabel.clickAndWaitForNewWindow();
            } else {
                UiSelector installSelector = api >= 31 ? new UiSelector()
                        .descriptionMatches("(?i)install(?-i)") :
                        new UiSelector()
                                .textMatches("(?i)install(?-i)");
                return new Wait().until(() -> device.findObject(installSelector).exists());
            }
        }

        UiObject uninstallButton = api >= 31 ?
                device.findObject(
                        new UiSelector().descriptionMatches("(?i)uninstall(?-i)")) :
                device.findObject(
                        new UiSelector().textMatches("(?i)uninstall(?-i)"));
        if (uninstallButton.waitForExists(TimeUnit.SECONDS.toMillis(10))) {
            uninstallButton.clickAndWaitForNewWindow();
        }
        UiObject okButton = device.findObject(new UiSelector().textMatches("(?i)ok(?-i)"));
        if (okButton.waitForExists(3)) {
            okButton.clickAndWaitForNewWindow();
        }
        if (uninstallButton.waitForExists(3)) {
            uninstallButton.clickAndWaitForNewWindow();
        }

        UiObject installButton = api >= 31 ? device.findObject(new UiSelector()
                .descriptionMatches("(?i)install(?-i)")) :
                device.findObject(new UiSelector()
                        .textMatches("(?i)install(?-i)"));

        return installButton.waitForExists(TimeUnit.SECONDS.toMillis(60));
    }

    /**
     * Attempts to uninstall an application from Google Play Store by name.
     * Returns true if the application has been uninstalled, false if not.
     */
    public static boolean uninstallApplicationByName(Instrumentation instrumentation, String testApplication) throws Exception {
        final UiDevice device = UiDevice.getInstance(instrumentation);
        PlayStoreUtil.selectApplication(instrumentation, testApplication);

        UiObject appLabel = device.findObject(new UiSelector()
                .textContains(testApplication).packageName("com.android.vending").index(1));
        if (new Wait(
                TimeUnit.MILLISECONDS.convert(20L, TimeUnit.SECONDS))
                .until(appLabel::exists)) {
            appLabel.clickAndWaitForNewWindow();
        } else {
            return false;
        }

        UiObject uninstallButton = api >= 31 ?
                device.findObject(
                        new UiSelector().descriptionMatches("(?i)uninstall(?-i)")) :
                device.findObject(
                        new UiSelector().textMatches("(?i)uninstall(?-i)"));
        if (uninstallButton.waitForExists(10)) {
            uninstallButton.clickAndWaitForNewWindow();
        }
        UiObject okButton = device.findObject(new UiSelector().textMatches("(?i)ok(?-i)"));
        if (okButton.waitForExists(3)) {
            okButton.clickAndWaitForNewWindow();
        }
        if (uninstallButton.waitForExists(3)) {
            uninstallButton.clickAndWaitForNewWindow();
        }

        UiObject installButton = api >= 31 ? device.findObject(new UiSelector()
                .descriptionMatches("(?i)install(?-i)")) :
                device.findObject(new UiSelector()
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

        PlayStoreUtil.launchGooglePlay(instrumentation, application);

        new watcher(device, Res.PLAY_STORE_WATCHER_PATTERN).checkForCondition();

        UiObject tryGooglePlay = device.findObject(
                new UiSelector().resourceId(Res.GOOGLE_PLAY_SECONDARY_BUTTON_RES));

        if (tryGooglePlay.waitForExists(10L)) {
            tryGooglePlay.clickAndWaitForNewWindow(10L);
        }

        return device.findObject(new UiSelector()
                        .className("android.view.View")
                        .packageName("com.android.vending")
                        .description(("Install")))
                .waitForExists(10L);
    }

    /**
     * Opens the Parental Controls menu
     */
    private static void openParentalControls(UiDevice testDevice) throws Exception {
        String playStoreUser = GoogleAppUtil.getUserEmail();

        if (api >= 30) {
            UiObject signedInAs = testDevice.findObject(
                    new UiSelector().descriptionContains(playStoreUser));
            if (signedInAs.waitForExists(3)) {
                signedInAs.clickAndWaitForNewWindow();
            }
        } else {
            UiObject backButton = testDevice.findObject(new UiSelector().description("Back"));
            if (backButton.waitForExists(3)) {
                backButton.clickAndWaitForNewWindow();
            }

            UiObject navigationDrawer = testDevice.findObject(new UiSelector().
                    description("Show navigation drawer"));
            if (navigationDrawer.waitForExists(TimeUnit.SECONDS.toMillis(10L))) {
                navigationDrawer.clickAndWaitForNewWindow();
            }
        }

        final UiScrollable scrollable = new UiScrollable(new UiSelector().scrollable(true));
        final UiSelector settingsSelector = api == 30 ?
                new UiSelector().description("Settings") : new UiSelector().text("Settings");
        final UiObject settingsScrollableLink = scrollable.getChild(settingsSelector);
        settingsScrollableLink.waitForExists(3L);
        if (scrollable.exists() && !settingsScrollableLink.exists()) {
            new Wait().until(() -> {
                int swipes = 0;
                while (!settingsScrollableLink.exists() && swipes < 20) {
                    scrollable.flingForward();
                    swipes++;
                }
                return settingsScrollableLink.exists();
            });
        }

        if (settingsScrollableLink.exists()) {
            settingsScrollableLink.clickAndWaitForNewWindow();
        } else {
            UiObject settingsLink = testDevice.findObject(settingsSelector);
            if (settingsLink.exists()) {
                settingsLink.clickAndWaitForNewWindow();
            }
        }

        UiObject parentalControlsButton = api >= 30 ?
                testDevice.findObject(new UiSelector().text("Parental control, parent guide")) :
                scrollable.getChild(new UiSelector().text("Parental controls"));
        if (parentalControlsButton.waitForExists(3L)) {
            parentalControlsButton.clickAndWaitForNewWindow();
            UiObject parentalControlsListItem =
                    testDevice.findObject(new UiSelector().text("Parental controls"));
            if (parentalControlsListItem.exists()) {
                parentalControlsListItem.clickAndWaitForNewWindow();
            }
        } else {
            new Wait().until(() -> {
                scrollable.scrollIntoView(parentalControlsButton);
                return parentalControlsButton.exists();
            });
            if (parentalControlsButton.exists()) {
                parentalControlsButton.clickAndWaitForNewWindow();
            }
        }
    }

    /**
     * Toggles the Parental Controls button; on if true, off if false
     */
    public static void toggleParentalControls(UiDevice testDevice, boolean setChecked) throws Exception {
        openParentalControls(testDevice);

        UiObject toggleButton = testDevice.findObject(new UiSelector().resourceId(
                Res.GOOGLE_PLAY_FILTER_TOGGLE_RES));

        boolean toggleButtonExists = new Wait().until(toggleButton::exists);

        if (!toggleButtonExists) {
            toggleButton = testDevice.findObject(new UiSelector().className("android.widget.Switch")
                    .description("Parental controls"));
            toggleButtonExists = new Wait().until(toggleButton::exists);
        }

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
