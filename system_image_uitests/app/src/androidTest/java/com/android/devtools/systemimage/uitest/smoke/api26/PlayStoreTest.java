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

package com.android.devtools.systemimage.uitest.smoke.api26;

import android.app.Instrumentation;
import android.support.test.runner.AndroidJUnit4;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiSelector;

import com.android.devtools.systemimage.uitest.annotations.TestInfo;
import com.android.devtools.systemimage.uitest.common.Res;
import com.android.devtools.systemimage.uitest.framework.SystemImageTestFramework;
import com.android.devtools.systemimage.uitest.utils.AppLauncher;
import com.android.devtools.systemimage.uitest.utils.PlayStoreUtil;
import com.android.devtools.systemimage.uitest.utils.Wait;
import com.android.devtools.systemimage.uitest.watchers.GoogleAppConfirmationWatcher;

import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.Timeout;
import org.junit.runner.RunWith;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

/**
 * Test to verify that Google services are available on Google API images
 */

@RunWith(AndroidJUnit4.class)
public class PlayStoreTest {
    @Rule
    public final SystemImageTestFramework testFramework = new SystemImageTestFramework();

    @Rule
    public Timeout globalTimeout = Timeout.seconds(500);

    @Before
    public void verifyPlayStore() throws Exception {
        if (testFramework.isGoogleApiAndPlayImage()) {
            Instrumentation instrumentation = testFramework.getInstrumentation();

            boolean playStoreInstalled = PlayStoreUtil.isPlayStoreInstalled_v1(instrumentation);
            boolean loggedInToPlayStore = playStoreInstalled &&
                    PlayStoreUtil.loginGooglePlay(instrumentation);
            assertTrue("PlayStore login failed.", loggedInToPlayStore);
        }
    }

    /**
     * Verify apps can be searched through Play Store search bar.
     * <p>
     * TT ID: 50027a89-8043-44d7-b7ed-33c631903910
     * <p>
     *   <pre>
     *   Test Steps:
     *   1. Start an emulator and launch home screen.
     *   2. Open Apps.
     *   3. Confirm that Play Store is present, then launch.
     *   4. Search for an app name on the main Play Store screen.
     *   Verify:
     *      1. Confirm that app name displays the search string.
     *   </pre>
     */

    @Test
    @TestInfo(id = "50027a89-8043-44d7-b7ed-33c631903910")
    public void testPlaySearch() throws Exception {
        if (testFramework.isGoogleApiAndPlayImage()) {
            Instrumentation instrumentation = testFramework.getInstrumentation();
            final UiDevice device = UiDevice.getInstance(instrumentation);
            final String application = "Wheather Channel";

            assertTrue("Application not found in search.",
                    PlayStoreUtil.hasTestApp(instrumentation, application));
            PlayStoreUtil.resetPlayStore(instrumentation);
            device.pressHome();
        }
    }

    /**
     * Verify that Google Play can install and uninstall a free app on the device.
     * <p>
     * TT ID: cb0ccd97-f045-42fa-8293-a32e94e838aa
     * <p>
     *   <pre>
     *   Test Steps:
     *   1. Start an emulator and launch home screen.
     *   2. Open Apps drawer.
     *   3. Confirm that Play Store is present, then launch.
     *   4. Search for free app in store.
     *   5. If app is available for install, begin installation.
     *   6. Uninstall the app.
     *   Verify:
     *      1a. If Install button was displayed, allow installation to complete then
     *      confirm that the Open button to launch the app is present.
     *      1b. If Install button was not displayed, confirm that the Open button to
     *      launch the app is present.
     *      2. Confirm that the app was subsequently uninstalled.
     *   </pre>
     */

    @Test
    @TestInfo(id = "cb0ccd97-f045-42fa-8293-a32e94e838aa")
    public void testAppInstallation() throws Exception {
        if (testFramework.isGoogleApiAndPlayImage()) {
            Instrumentation instrumentation = testFramework.getInstrumentation();
            final UiDevice device = UiDevice.getInstance(instrumentation);
            final String application = "Google Translate";

            PlayStoreUtil.selectApplication(instrumentation, application);
            new GoogleAppConfirmationWatcher(device).checkForCondition();

            assertTrue("Unable to install the application from Google Play",
                    PlayStoreUtil.installApplication(instrumentation));

            AppLauncher.launch(instrumentation, "Play Store");
            assertTrue("Unable to uninstall the application from Google Play",
                    PlayStoreUtil.uninstallApplication(instrumentation));

            PlayStoreUtil.resetPlayStore(instrumentation);
            device.pressHome();
        }
    }

    /**
     * Verify that Google Play can install and launch an app, then uninstall the app on the device.
     * <p>
     * TT ID: 924a0428-4e07-4794-b6a7-2c9d407204aa
     * <p>
     *   <pre>
     *   Test Steps:
     *   1. Start an emulator and launch home screen.
     *   2. Open Apps.
     *   3. Confirm that Play Store is present, then launch.
     *   5. Search for free app in store.
     *   6. If app is available for install, begin installation.
     *   7. Launch the application.
     *   8. Close and uninstall the app.
     *   Verify:
     *      1a. If Install button was displayed, allow installation to complete then
     *      confirm that the Open button to launch the app is present.
     *      1b. If Install button was not displayed, confirm that the Open button to
     *      launch the app is present.
     *      2. Confirm that application launch was successful.
     *      3. Confirm that the app was subsequently uninstalled.
     *   </pre>
     */

    @Test
    @TestInfo(id = "924a0428-4e07-4794-b6a7-2c9d407204aa")
    public void testAppInstallationAndLaunch() throws Exception {
        if (testFramework.isGoogleApiAndPlayImage()) {
            Instrumentation instrumentation = testFramework.getInstrumentation();
            final UiDevice device = UiDevice.getInstance(instrumentation);
            final String application = "Wheather Channel";

            PlayStoreUtil.selectApplication(instrumentation, application);
            new GoogleAppConfirmationWatcher(device).checkForCondition();

            assertTrue("Unable to install the application from Google Play",
                    PlayStoreUtil.installApplication(instrumentation));

            AppLauncher.launch(instrumentation, "Play Store");
            device.findObject(new UiSelector().textMatches("(?i)open(?-i)")).clickAndWaitForNewWindow();
            assertTrue("App could not be opened",
                    new Wait().until(() -> device.findObject(new UiSelector()
                            .textContains(application)).exists()));

            AppLauncher.launch(instrumentation, "Play Store");
            assertTrue("Unable to uninstall the application from Google Play",
                    PlayStoreUtil.uninstallApplication(instrumentation));

            PlayStoreUtil.resetPlayStore(instrumentation);
            device.pressHome();
        }
    }

    /**
     * Verify that Google Play can reach the payment method prompt during paid app installation
     * <p>
     * TT ID: bd9460a8-7b07-4cfc-901f-a99564533e51
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

    @Test
    @TestInfo(id = "bd9460a8-7b07-4cfc-901f-a99564533e51")
    public void testPayAppVerification() throws Exception {
        if (testFramework.isGoogleApiAndPlayImage()) {
            Instrumentation instrumentation = testFramework.getInstrumentation();
            final UiDevice device = UiDevice.getInstance(instrumentation);
            final String application = "PowerAudio Pro";

            PlayStoreUtil.selectApplication(instrumentation, application);
            new GoogleAppConfirmationWatcher(device).checkForCondition();

            assertTrue("Target application is not a pay app",
                    device.findObject(new UiSelector()
                            .className("android.widget.Button")
                            .packageName(Res.GOOGLE_PLAY_VENDING_RES)
                            .textContains("$")).waitForExists(10L));

            PlayStoreUtil.resetPlayStore(instrumentation);
            device.pressHome();
        }
    }

    /**
     * Verify that Google Play search can be limited through parental controls
     * <p>
     * TT ID: fe78dba5-a0f2-4acf-bcbb-10b1c15d3484
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
     *   9. Set controls to Everyone 10+.
     *   10. Search for adult app and family app in Play Store, finding only family app.
     *   11. Turn off Parental Controls.
     *   Verify:
     *      1. Confirm that search returns adult version of app without parental controls set.
     *      2. Confirm that search does not return adult version of app with parental controls set,
     *          but does return family version of app.
     *   </pre>
     */

    @Test
    @TestInfo(id = "fe78dba5-a0f2-4acf-bcbb-10b1c15d3484")
    public void testParentalControls() throws Exception {
        if (testFramework.isGoogleApiAndPlayImage()) {
            final Instrumentation instrumentation = testFramework.getInstrumentation();
            final UiDevice device = UiDevice.getInstance(instrumentation);
            final String familyApplication = "Weather Channel";
            final String restrictedApplication = "Reddit";

            assertTrue("Adult application is found in search.",
                    PlayStoreUtil.hasTestApp(instrumentation, restrictedApplication));

            device.pressBack();

            PlayStoreUtil.setRestrictions(instrumentation,  "Apps", "Everyone 10+");

            assertFalse("Adult application is not found in restricted search.",
                    PlayStoreUtil.hasTestApp(instrumentation, restrictedApplication));

            device.pressBack();

            assertTrue("Family application is found in restricted search.",
                    PlayStoreUtil.hasTestApp(instrumentation, familyApplication));


            device.pressBack();

            PlayStoreUtil.toggleParentalControls(device, false);
            device.pressHome();
        }
    }
}
