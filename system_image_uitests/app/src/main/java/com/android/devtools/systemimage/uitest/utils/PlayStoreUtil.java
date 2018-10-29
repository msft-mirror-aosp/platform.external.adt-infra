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
import android.view.KeyEvent;

import com.android.devtools.systemimage.uitest.common.Res;
import com.android.devtools.systemimage.uitest.watchers.GoogleAppConfirmationWatcher;
import com.android.devtools.systemimage.uitest.watchers.PlayStoreControlsWatcher;

import java.util.concurrent.TimeUnit;

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
        isInstalled = new Wait().until(new Wait.ExpectedCondition() {
            @Override
            public boolean isTrue() throws UiObjectNotFoundException {
                scrollable.scrollIntoView(new UiSelector().text(playStore));
                return scrollable.getChild(new UiSelector().text(playStore)).exists();
            }
        });

        return isInstalled;
    }

    /**
     * Version 2 for 25 <= api <= 27
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
                until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() {
                        return device.findObject(new UiSelector().text(playStore)).exists() ||
                                device.findObject(new UiSelector().description(playStore)).exists();
                    }
                });

        return isInstalled;
    }

    /**
     * Version 3 for api >= 28
     *
     * Checks if Play Store has been installed.
     * Returns true if Play Store has been installed, false if not.
     */
    public static boolean isPlayStoreInstalled_v3(Instrumentation instrumentation) throws Exception {
        final UiDevice device = UiDevice.getInstance(instrumentation);
        boolean isInstalled;
        final String playStore = "Play Store";

        device.pressHome();
        device.pressKeyCode(KeyEvent.KEYCODE_A, KeyEvent.META_CTRL_ON);

        isInstalled = new Wait(TimeUnit.MILLISECONDS.convert(3L, TimeUnit.SECONDS)).
                until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() {
                        return device.findObject(new UiSelector().text(playStore)).exists() ||
                                device.findObject(new UiSelector().description(playStore)).exists();
                    }
                });

        device.pressHome();

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

        boolean idleTextFieldExists = new Wait().until(new Wait.ExpectedCondition() {
            @Override
            public boolean isTrue() throws UiObjectNotFoundException {
                return device.findObject(
                        new UiSelector().resourceId(Res.GOOGLE_PLAY_IDLE_RES)).exists();
            }
        });

        if (idleTextFieldExists) {
            device.findObject(
                    new UiSelector().resourceId(Res.GOOGLE_PLAY_IDLE_RES)).click();
        }

        boolean inputTextFieldExists = new Wait().until(new Wait.ExpectedCondition() {
            @Override
            public boolean isTrue() throws UiObjectNotFoundException {
                return device.findObject(
                        new UiSelector().resourceId(Res.GOOGLE_PLAY_INPUT_RES)).exists();
            }
        });

        if (inputTextFieldExists) {
            UiObject inputTextField = device.findObject(
                    new UiSelector().resourceId(Res.GOOGLE_PLAY_INPUT_RES));
            inputTextField.clearTextField();
            inputTextField.setText(appName);
            device.pressEnter();
        }
    }

    /**
     * Checks if test user is logged in to Google Play.  Logs in if not.
     */
    public static void loginGooglePlay(Instrumentation instrumentation) throws Exception {
        final UiDevice device = UiDevice.getInstance(instrumentation);
        resetPlayStore(instrumentation);
        AppLauncher.launch(instrumentation, "Play Store");
        new GoogleAppConfirmationWatcher(device).checkForCondition();

        boolean hasSearchBox = new Wait(TimeUnit.SECONDS.toMillis(5)).
                until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() throws UiObjectNotFoundException {
                        return device.findObject(
                                new UiSelector().resourceId(Res.GOOGLE_PLAY_IDLE_RES)).exists() ||
                                device.findObject(
                                        new UiSelector().resourceId(Res.GOOGLE_PLAY_ACTIVE_RES)).exists();
                    }
                });
        if (hasSearchBox) {
            device.pressHome();
            return;
        }

        GoogleAppUtil.loginGoogleApp(instrumentation);

        AppLauncher.launch(instrumentation, "Play Store");
        new GoogleAppConfirmationWatcher(device).checkForCondition();
        device.pressHome();
    }

    /**
     * Attempts to install an application from Google Play Store, if it is not already installed.
     * Returns true if the application has been installed, false if not.
     */
    public static boolean installApplication(Instrumentation instrumentation) throws Exception {
        final UiDevice device = UiDevice.getInstance(instrumentation);

        boolean isInstallable = new Wait(TimeUnit.MILLISECONDS.convert(10L, TimeUnit.SECONDS)).until(new Wait.ExpectedCondition() {
            @Override
            public boolean isTrue() throws UiObjectNotFoundException {
                return device.findObject(new UiSelector()
                        .text("INSTALL")).exists();
            }
        });

        if (!isInstallable) {
            return new Wait().until(new Wait.ExpectedCondition() {
                @Override
                public boolean isTrue() throws UiObjectNotFoundException {
                    return device.findObject(new UiSelector()
                            .text("UNINSTALL")).exists();
                }
            });
        }

        device.findObject(new UiSelector().text("INSTALL")).clickAndWaitForNewWindow();
        new GoogleAppConfirmationWatcher(device).checkForCondition();

        UiObject openButton = device.findObject(new UiSelector().text("OPEN"));
        boolean isAppInstalled = openButton.waitForExists(TimeUnit.SECONDS.toMillis(60));

        return isAppInstalled;
    }

    /**
     * Attempts to uninstall an application from Google Play Store, if it is already installed.
     * Returns true if the application has been uninstalled, false if not.
     */
    public static boolean uninstallApplication(Instrumentation instrumentation) throws Exception {
        final UiDevice device = UiDevice.getInstance(instrumentation);

        boolean isUninstallable = new Wait(TimeUnit.MILLISECONDS.convert(10L, TimeUnit.SECONDS)).until(new Wait.ExpectedCondition() {
            @Override
            public boolean isTrue() throws UiObjectNotFoundException {
                return device.findObject(new UiSelector()
                        .text("UNINSTALL")).exists();
            }
        });

        if (!isUninstallable) {
            return new Wait().until(new Wait.ExpectedCondition() {
                @Override
                public boolean isTrue() throws UiObjectNotFoundException {
                    return device.findObject(new UiSelector()
                            .text("INSTALL")).exists();
                }
            });
        }

        device.findObject(new UiSelector().text("UNINSTALL")).clickAndWaitForNewWindow();
        device.findObject(new UiSelector().text("OK")).clickAndWaitForNewWindow();

        UiObject installButton = device.findObject(new UiSelector()
                .text("INSTALL"));
        boolean isAppUninstalled = installButton.waitForExists(TimeUnit.SECONDS.toMillis(60));

        return isAppUninstalled;
    }

    /**
     * Selects an application listed in Play Store, if found.
     */
    public static void selectApplication(Instrumentation instrumentation,
                                          String application) throws Exception {
        final UiDevice device = UiDevice.getInstance(instrumentation);

        boolean isFound = hasTestApp(instrumentation, application, false);
        if (isFound) {
            device.findObject(new UiSelector()
                    .descriptionContains(application)).clickAndWaitForNewWindow();
        }
    }

    /**
     * Helper to search Google Play for an application by description.
     * Return true if found, false if not.
     */
    public static boolean hasTestApp(Instrumentation instrumentation, String application, boolean strict)
            throws Exception {
        final UiDevice device = UiDevice.getInstance(instrumentation);
        final String appTitle = application;
        final boolean exactMatch = strict;

        device.pressHome();
        PlayStoreUtil.launchGooglePlay(instrumentation, appTitle);

        return new Wait().until(new Wait.ExpectedCondition() {
            @Override
            public boolean isTrue() {
                boolean hasApplication = exactMatch ?
                        device.findObject(new UiSelector().text(appTitle).
                                resourceId(Res.GOOGLE_PLAY_LIST_TITLE_RES)).exists() :
                        device.findObject(new UiSelector().textContains(appTitle).
                                resourceId(Res.GOOGLE_PLAY_LIST_TITLE_RES)).exists();
                return hasApplication;
            }
        });
    }
    /**
     * Opens the Parental Controls menu
     */
    private static void openParentalControls(UiDevice testDevice) throws Exception {
        final UiDevice device = testDevice;
        device.findObject(new UiSelector().description("Back")).clickAndWaitForNewWindow();
        device.findObject(new UiSelector().description("Show navigation drawer"))
                .waitForExists(TimeUnit.SECONDS.toMillis(3));
        device.findObject(new UiSelector().description("Show navigation drawer"))
                .clickAndWaitForNewWindow();

        final UiScrollable scrollable = new UiScrollable(new UiSelector().scrollable(true));
        final UiObject settingsLink = scrollable.getChild(new UiSelector().text("Settings"));
        settingsLink.waitForExists(3L);
        if (!settingsLink.exists()) {
            new Wait().until(new Wait.ExpectedCondition() {
                @Override
                public boolean isTrue() throws UiObjectNotFoundException {
                    int swipes = 0;
                    while (!settingsLink.exists() && swipes < 20) {
                        scrollable.flingForward();
                        swipes++;
                    }
                    return settingsLink.exists();
                }
            });
        }
        if (settingsLink.exists()) {
            settingsLink.clickAndWaitForNewWindow();
        }

        final UiObject parentalControlsButton = scrollable.getChild(new UiSelector().text(
                "Parental controls"));
        parentalControlsButton.waitForExists(3L);
        if (!parentalControlsButton.exists()) {
            new Wait().until(new Wait.ExpectedCondition() {
                @Override
                public boolean isTrue() throws UiObjectNotFoundException {
                    scrollable.scrollIntoView(parentalControlsButton);
                    return parentalControlsButton.exists();
                }
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
        final UiDevice device = testDevice;
        openParentalControls(device);

        final UiObject toggleButton = device.findObject(new UiSelector().resourceId(
                Res.GOOGLE_PLAY_FILTER_TOGGLE_RES));

        boolean toggleButtonExists = new Wait().until(new Wait.ExpectedCondition() {
            @Override
            public boolean isTrue() {
                return toggleButton.exists();
            }
        });

        if (toggleButtonExists && toggleButton.isChecked() != setChecked) {
            toggleButton.clickAndWaitForNewWindow();
            setParentalControlPin(device, "1111");
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

        new Wait().until(new Wait.ExpectedCondition() {
            @Override
            public boolean isTrue() {
                return device.findObject(new UiSelector().textStartsWith(appCategory)).exists();
            }
        });
        device.findObject(new UiSelector().textStartsWith(appCategory)).clickAndWaitForNewWindow();
        setParentalControlPin(device, "1111");
        device.findObject(new UiSelector().text(ages))
                .waitForExists(TimeUnit.SECONDS.toMillis(3));
        device.findObject(new UiSelector().text(ages))
                .clickAndWaitForNewWindow();
        new PlayStoreControlsWatcher(device).checkForCondition();
        UiScrollable scrollable = new UiScrollable(new UiSelector().scrollable(true));
        scrollable.waitForExists(3L);
        if (scrollable.exists()) {
            scrollable.flingToEnd(5);
        }
        new PlayStoreControlsWatcher(device).checkForCondition();
        PlayStoreUtil.resetPlayStore(instrumentation);
        device.pressHome();
    }
    /**
     * Sets and then confirms a parental control pin
     */
    private static void setParentalControlPin(UiDevice testDevice, String pin) throws Exception {
        final UiDevice device = testDevice;

        boolean hasPinDialog = new Wait().until(new Wait.ExpectedCondition() {
            @Override
            public boolean isTrue() throws UiObjectNotFoundException {
                return device.findObject(new UiSelector().text("Type PIN")).exists();
            }
        });

        if (!hasPinDialog) {
            return;
        }

        device.findObject(new UiSelector().text("Type PIN")).setText(pin);
        device.findObject(new UiSelector().text("OK")).clickAndWaitForNewWindow();

        boolean needsConfirmation = new Wait().until(new Wait.ExpectedCondition() {
            @Override
            public boolean isTrue() throws UiObjectNotFoundException {
                return device.findObject(new UiSelector().text("Type PIN")).exists();
            }
        });

        if (needsConfirmation) {
            device.findObject(new UiSelector().text("Type PIN")).setText(pin);
            device.findObject(new UiSelector().text("OK")).clickAndWaitForNewWindow();
        }
    }
}