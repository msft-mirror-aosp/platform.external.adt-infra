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

package com.android.devtools.systemimage.uitest.smoke;

import android.app.Instrumentation;
import android.support.test.runner.AndroidJUnit4;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObjectNotFoundException;
import android.support.test.uiautomator.UiScrollable;
import android.support.test.uiautomator.UiSelector;

import com.android.devtools.systemimage.uitest.annotations.TestInfo;
import com.android.devtools.systemimage.uitest.common.Res;
import com.android.devtools.systemimage.uitest.framework.SystemImageTestFramework;
import com.android.devtools.systemimage.uitest.utils.PlayStoreUtil;
import com.android.devtools.systemimage.uitest.utils.Wait;
import com.android.devtools.systemimage.uitest.watchers.PlayStoreConfirmationWatcher;

import org.junit.Ignore;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.Timeout;
import org.junit.runner.RunWith;

import java.util.concurrent.TimeUnit;

import static org.junit.Assert.assertTrue;

/**
 * Test to verify that Play Store services are available on Google API with Play Store images.
 */

@RunWith(AndroidJUnit4.class)
public class PlayStoreTest {
    private static final String WIDGET_TEXT_VIEW_CLASS = "android.widget.TextView";

    @Rule
    public final SystemImageTestFramework testFramework = new SystemImageTestFramework();

    @Rule
    public Timeout globalTimeout = Timeout.seconds(120);

    /**
     * Verify that Google Play can install and uninstall a free app on the device.
     * <p>
     * TR ID: C14578827
     * <p>
     *   <pre>
     *   Test Steps:
     *   1. Start an emulator and launch home screen.
     *   2. Open Apps.
     *   3. Confirm that Play Store is present, then launch.
     *   5. Search for free app in store.
     *   6. If app is available for install, begin installation.
     *   7. Uninstall the app.
     *   Verify:
     *      1a. If Install button is displayed, allow installation to complete then
     *      confirm that the Open button to launch the app is present.
     *      1b. If Install button is not displayed, confirm that the Open button to
     *      launch the app is present.
     *      2. Confirm that the app was subsequently uninstalled.
     *   </pre>
     */
    @Ignore("Testing play store requires google login that may trigger 2-auth factor. Test to be initiated manually by tester.")
    @Test
    @TestInfo(id = "14578827")
    public void testAppInstallation() throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();
        final UiDevice device = UiDevice.getInstance(instrumentation);
        final String application = "Google Translate";

        if (testFramework.getApi() >= 24 && testFramework.isGoogleApiAndPlayImage()) {
            device.pressHome();
            device.findObject(new UiSelector().description("Apps")).clickAndWaitForNewWindow();

            boolean playStoreInstalled = PlayStoreUtil.isPlayStoreInstalled(instrumentation);

            if (playStoreInstalled) {
                PlayStoreUtil.searchGooglePlay(instrumentation, application);
                selectFromGooglePlay(device, "App: "+application);

                new PlayStoreConfirmationWatcher(device).checkForCondition();

                assertTrue("Unable to install the application from Google Play",
                        PlayStoreUtil.installApplication(instrumentation));

                assertTrue("Unable to uninstall the application from Google Play",
                        PlayStoreUtil.uninstallApplication(instrumentation));

                PlayStoreUtil.resetPlayStore(instrumentation);
                device.pressHome();
            }
        }
    }

    /**
     * Verify that an app can be installed and launched from Play Store.
     * <p>
     * TR ID: C14603433
     * <p>
     *   <pre>
     *   Test Steps:
     *   1. Start an emulator and launch home screen.
     *   2. Open Apps.
     *   3. Confirm that Play Store is present, then launch.
     *   5. Search for free app in store.
     *   6. If app is available for install, begin installation.
     *   7. Launch the application.
     *   7. Close and uninstall the app.
     *   Verify:
     *      1. App is installed without errors.
     *      2. App is launched without errors.
     *   </pre>
     */
    @Ignore("Testing play store requires google login that may trigger 2-auth factor. Test to be initiated manually by tester.")
    @Test
    @TestInfo(id = "14603433")
    public void testAppInstallationAndLaunch() throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();
        final UiDevice device = UiDevice.getInstance(instrumentation);
        final String application = "Trello";

        if (testFramework.getApi() >= 24 && testFramework.isGoogleApiImage()) {
            device.pressHome();
            device.findObject(new UiSelector().description("Apps")).clickAndWaitForNewWindow();

            boolean playStoreInstalled = PlayStoreUtil.isPlayStoreInstalled(instrumentation);

            if (playStoreInstalled) {
                PlayStoreUtil.searchGooglePlay(instrumentation, application);
                selectFromGooglePlay(device, "App: "+application);

                new PlayStoreConfirmationWatcher(device).checkForCondition();

                assertTrue("Unable to install the application from Google Play",
                        PlayStoreUtil.installApplication(instrumentation));

                device.findObject(new UiSelector().text("OPEN")).clickAndWaitForNewWindow();
                assertTrue("App could not be opened",
                        new Wait().until(new Wait.ExpectedCondition() {
                            @Override
                            public boolean isTrue() throws UiObjectNotFoundException {
                                return device.findObject(new UiSelector()
                                        .packageName("com.trello")).exists();
                            }
                        }));

                device.pressBack();

                assertTrue("Unable to uninstall the application from Google Play",
                        PlayStoreUtil.uninstallApplication(instrumentation));

                PlayStoreUtil.resetPlayStore(instrumentation);
                device.pressHome();
            }
        }
    }

    /**
     * Verify that Google Play can reach the payment method prompt during paid app installation.
     * <p>
     * TR ID: C14603432
     * <p>
     *   <pre>
     *   Test Steps:
     *   1. Start an emulator and launch home screen.
     *   2. Open Apps.
     *   3. Confirm that Play Store is present, then launch.
     *   4. Search for pay app in store.
     *   Verify:
     *      1. Confirm that user is presented with a Pay Button with a $.
     *   </pre>
     */
    @Ignore("Testing play store requires google login that may trigger 2-auth factor. Test to be initiated manually by tester.")
    @Test
    @TestInfo(id = "1460343")
    public void testPayAppVerification() throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();
        final UiDevice device = UiDevice.getInstance(instrumentation);
        final String application = "Weather Live";

        if (testFramework.getApi() >= 24 && testFramework.isGoogleApiImage()) {
            device.pressHome();
            device.findObject(new UiSelector().description("Apps")).clickAndWaitForNewWindow();

            boolean playStoreInstalled = PlayStoreUtil.isPlayStoreInstalled(instrumentation);

            if (playStoreInstalled) {
                PlayStoreUtil.searchGooglePlay(instrumentation, application);
                selectFromGooglePlay(device, "App: "+application);

                new PlayStoreConfirmationWatcher(device).checkForCondition();

                assertTrue(
                        "Target application is not a pay app",  new Wait().until(
                                new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() throws UiObjectNotFoundException {
                        return device.findObject(new UiSelector()
                                .resourceId(
                                        Res.GOOGLE_PLAY_BUY_BUTTON_RES).textContains("$")).exists();
                    }
                }));

                PlayStoreUtil.resetPlayStore(instrumentation);
                device.pressHome();
            }
        }
    }

    /**
     * Verify apps can be searched through Play Store search bar.
     * <p>
     * TR ID: C14605490
     * <p>
     *   <pre>
     *   Test Steps:
     *   1. Start an emulator and launch home screen.
     *   2. Open Apps.
     *   3. Confirm that Play Store is present, then launch.
     *   4. Search for an app name on the main Play Store screen.
     *   Verify:
     *      1. Confirm app name displays the search string.
     *   </pre>
     */

    @Ignore("Testing play store requires google login that may trigger 2-auth factor. Test to be initiated manually by tester.")
    @Test
    @TestInfo(id = "14605490")
    public void testPlaySearch() throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();
        final UiDevice device = UiDevice.getInstance(instrumentation);
        final String application = "Facebook";

        if (testFramework.getApi() >= 24 && testFramework.isGoogleApiImage()) {
            device.pressHome();
            device.findObject(new UiSelector().description("Apps")).clickAndWaitForNewWindow();

            boolean playStoreInstalled = PlayStoreUtil.isPlayStoreInstalled(instrumentation);

            if (playStoreInstalled) {
                PlayStoreUtil.searchGooglePlay(instrumentation, application);
                assertTrue("Target application not found in search.",  new Wait().until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() throws Exception {
                        return findInGooglePlay(device, "App: "+application);
                    }
                }));
                PlayStoreUtil.resetPlayStore(instrumentation);
                device.pressHome();
            }
        }
    }

    /**
     * Verify that Google Play search can be limited through parental controls
     * <p>
     * TR ID: C14605497
     * <p>
     *   <pre>
     *   Test Steps:
     *   1. Start an emulator and launch home screen.
     *   2. Open Apps.
     *   3. Confirm that Play Store is present, then launch.
     *   4. Search for adult app in Play Store, successfully.
     *   5. Open Play Store settings.
     *   6. Turn on Parental Controls.
     *   7. Select restrictions for Apps and Games.
     *   8. Set and confirm a content PIN.
     *   9. Set controls to Everone 10+.
     *   10. Search for adult app in Play Store, unsuccessfully.
     *   11. Search for family app in Play Store, successfully.
     *   12. Turn off Parental Controls.
     *   Verify:
     *      1. Confirm that search returns adult version of app without parental controls set.
     *      2. Confirm that search does not return adult version of app with parental controls set.
     *      3. Confirm that search does return family version of app with parental controls set.
     *   </pre>
     */
    @Ignore("Testing play store requires google login that may trigger 2-auth factor. Test to be initiated manually by tester.")
    @Test
    @TestInfo(id = "14605497")
    public void testParentalControls() throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();
        final UiDevice device = UiDevice.getInstance(instrumentation);
        final String application = "Truth or Dare";

        if (testFramework.getApi() >= 24 && testFramework.isGoogleApiImage()) {
            device.pressHome();
            device.findObject(new UiSelector().description("Apps")).clickAndWaitForNewWindow();

            boolean playStoreInstalled = PlayStoreUtil.isPlayStoreInstalled(instrumentation);

            if (playStoreInstalled) {
                PlayStoreUtil.searchGooglePlay(instrumentation, application);
                assertTrue("Adult application not found in search.",  new Wait().until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() throws Exception {
                        return findInGooglePlay(device, "App: "+ application + " Adults");
                    }
                }));

                openParentalControls(device);

                boolean controlsOff = new Wait().until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() throws UiObjectNotFoundException {
                        return device.findObject(new UiSelector().text("Parental controls are off")).exists();
                    }
                });

                if (controlsOff) {
                    device.findObject(new UiSelector().text("Parental controls are off")).clickAndWaitForNewWindow();
                    setParentalControlPin(device, "1111");
                }

                device.findObject(new UiSelector().text("Apps & games"))
                        .waitForExists(TimeUnit.SECONDS.toMillis(3));
                device.findObject(new UiSelector().text("Apps & games"))
                        .clickAndWaitForNewWindow();

                device.findObject(new UiSelector().text("Everyone 10+"))
                        .waitForExists(TimeUnit.SECONDS.toMillis(3));
                device.findObject(new UiSelector().text("Everyone 10+"))
                        .clickAndWaitForNewWindow();

                device.findObject(new UiSelector().text("OK"))
                        .waitForExists(TimeUnit.SECONDS.toMillis(3));
                device.findObject(new UiSelector().text("OK"))
                        .clickAndWaitForNewWindow();

                device.findObject(new UiSelector().text("SAVE"))
                        .waitForExists(TimeUnit.SECONDS.toMillis(3));
                device.findObject(new UiSelector().text("SAVE"))
                        .clickAndWaitForNewWindow();

                device.pressHome();

                PlayStoreUtil.searchGooglePlay(instrumentation, application);
                assertTrue("Adult application found in search.",  new Wait().until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() throws Exception {
                        return !findInGooglePlay(device, "App: "+ application + " Adults");
                    }
                }));

                assertTrue("Family application not found in search.",  new Wait().until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() throws Exception {
                        return findInGooglePlay(device, "App: "+ application + " Kids");
                    }
                }));

                openParentalControls(device);
                new Wait().until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() throws UiObjectNotFoundException {
                        return device.findObject(new UiSelector().text("Apps & games")).exists();
                    }
                });
                device.findObject(new UiSelector().text("Apps & games")).clickAndWaitForNewWindow();
                setParentalControlPin(device, "1111");

                device.findObject(new UiSelector().text("Allow all, including unrated"))
                        .waitForExists(TimeUnit.SECONDS.toMillis(3));
                device.findObject(new UiSelector().text("Allow all, including unrated"))
                        .clickAndWaitForNewWindow();

                device.findObject(new UiSelector().text("OK"))
                        .waitForExists(TimeUnit.SECONDS.toMillis(3));
                device.findObject(new UiSelector().text("OK"))
                        .clickAndWaitForNewWindow();

                device.findObject(new UiSelector().text("SAVE"))
                        .waitForExists(TimeUnit.SECONDS.toMillis(3));
                device.findObject(new UiSelector().text("SAVE"))
                        .clickAndWaitForNewWindow();

                new Wait().until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() throws UiObjectNotFoundException {
                        return device.findObject(new UiSelector().text("Parental controls are on")).exists();
                    }
                });

                device.findObject(new UiSelector().text("Parental controls are on")).clickAndWaitForNewWindow();

                PlayStoreUtil.resetPlayStore(instrumentation);
                device.pressHome();
            }
        }
    }

    /**
     * Selects an application listed in Play Store.
     */
    private static void selectFromGooglePlay(UiDevice testDevice, String appDescription) throws Exception {
        final UiDevice device = testDevice;
        final String application = appDescription;

        boolean isFound = findInGooglePlay(device, appDescription);

        if (isFound) {
            device.findObject(new UiSelector()
                    .description(application)).clickAndWaitForNewWindow();
        }
    }

    /**
     * Finds and application in Play Store. Returns true if it was found, false if not.
     */
    private static boolean findInGooglePlay(UiDevice testDevice, String appDescription) throws Exception {
        final UiDevice device = testDevice;
        final String application = appDescription;

        return new Wait().until(new Wait.ExpectedCondition() {
            @Override
            public boolean isTrue() throws UiObjectNotFoundException {
                return device.findObject(new UiSelector()
                        .description(application)).exists();
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

        new Wait().until(new Wait.ExpectedCondition() {
            @Override
            public boolean isTrue() throws UiObjectNotFoundException {
                scrollable.scrollIntoView(new UiSelector().text("Settings"));
                return scrollable.getChild(new UiSelector().text("Settings")).exists();
            }
        });

        scrollable.getChild(new UiSelector().text("Settings")).clickAndWaitForNewWindow();

        new Wait().until(new Wait.ExpectedCondition() {
            @Override
            public boolean isTrue() throws UiObjectNotFoundException {
                scrollable.scrollIntoView(new UiSelector().text("Parental controls"));
                return device.findObject(new UiSelector().text("Parental controls")).exists();
            }
        });
        scrollable.getChild(new UiSelector().text("Parental controls")).clickAndWaitForNewWindow();
    }

    /**
     * Sets and then confirms a parental control pin
     */
    private static void setParentalControlPin(UiDevice testDevice, String pin) throws Exception {
        final UiDevice device = testDevice;

        new Wait().until(new Wait.ExpectedCondition() {
            @Override
            public boolean isTrue() throws UiObjectNotFoundException {
                return device.findObject(new UiSelector().text("Type PIN")).exists();
            }
        });

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