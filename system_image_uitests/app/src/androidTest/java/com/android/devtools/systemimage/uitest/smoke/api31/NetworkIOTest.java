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

package com.android.devtools.systemimage.uitest.smoke.api31;

import android.app.Instrumentation;
import androidx.test.runner.AndroidJUnit4;
import androidx.test.uiautomator.By;
import androidx.test.uiautomator.UiDevice;
import androidx.test.uiautomator.UiObject;
import androidx.test.uiautomator.UiObjectNotFoundException;
import androidx.test.uiautomator.UiScrollable;
import androidx.test.uiautomator.UiSelector;
import androidx.test.uiautomator.Until;

import com.android.devtools.systemimage.uitest.annotations.TestInfo;
import com.android.devtools.systemimage.uitest.common.Res;
import com.android.devtools.systemimage.uitest.framework.SystemImageTestFramework;
import com.android.devtools.systemimage.uitest.utils.AppLauncher;
import com.android.devtools.systemimage.uitest.utils.NetworkIOTestUtil;
import com.android.devtools.systemimage.uitest.utils.NetworkUtil;
import com.android.devtools.systemimage.uitest.utils.Wait;
import com.android.devtools.systemimage.uitest.watchers.NetworkUtilPopupWatcher;

import junit.framework.Assert;

import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.Timeout;
import org.junit.runner.RunWith;

import java.util.concurrent.TimeUnit;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

/**
 * Test class for network connection on emulator.
 */
@RunWith(AndroidJUnit4.class)
public class NetworkIOTest {
    @Rule
    public final SystemImageTestFramework testFramework = new SystemImageTestFramework();

    @Rule
    public Timeout globalTimeout = Timeout.seconds(500);

    /**
     * Verifies test browser successfully loads a web page.
     * <p>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p>
     * TR ID: C14578825
     * <p>
     *   <pre>
     *   Test Steps:
     *   1. Start the emulator.
     *   2. Launch browser app.
     *   3. Navigate to a website.
     *   Verify:
     *   Icons indicating working network connection displayed in status bar.
     *   Browser successfully loads the web page.
     *   </pre>
     */
    @Test
    @TestInfo(id = "14578825")
    @ScreenRecord
    public void testBrowserLoadsSite() throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();
        UiDevice device = testFramework.getDevice();

        // Check network connectivity.
        if (NetworkUtil.hasCellularNetworkConnection(instrumentation)) {
            if (testFramework.isGoogleApiImage() || testFramework.isGoogleApiAndPlayImage()) {
                device.openNotification();
                UiObject internetTile = device.findObject(new UiSelector().resourceId(
                        Res.NOTIFICATIONS_TILE_LABEL).text("Internet"));
                assertTrue("Could not connect to the network.",
                        new Wait().until(internetTile::exists));
                internetTile.click();
                UiObject connectWifiSummary = device.findObject(new UiSelector().resourceId(
                        Res.ANDROID_SUMMARY_RES).text("Connected"));
                assertTrue("Could not connect to the network.",
                        new Wait().until(connectWifiSummary::exists));
                device.pressHome();

                AppLauncher.launch(instrumentation, "Chrome");
                // If this is the first launch, dismiss the "Welcome to Chrome" screen.
                UiObject acceptButton = device.findObject(new UiSelector().resourceId(
                        Res.CHROME_TERMS_ACCEPT_BUTTON_RES));
                if (acceptButton.exists()) {
                    acceptButton.clickAndWaitForNewWindow();
                }

                // Dismiss the "Sign in to Chrome" screen if it's there.
                UiObject noThanksButton = device.findObject(new UiSelector().resourceIdMatches(
                        Res.CHROME_NO_THANKS_BUTTON_RES));
                if (noThanksButton.waitForExists(TimeUnit.SECONDS.toMillis(3))) {
                    noThanksButton.clickAndWaitForNewWindow();
                }

                UiObject searchBox = device.findObject(new UiSelector().resourceId(
                        Res.CHROME_SEARCH_BOX_RES));
                if (searchBox.exists()) {
                    searchBox.clickAndWaitForNewWindow();
                }

                final UiObject textField = device.findObject(new UiSelector().resourceId(
                        Res.CHROME_URL_BAR_RES));
                Assert.assertTrue("Chrome URL bar not found",
                        new Wait().until(textField::exists));

                textField.click();
                textField.clearTextField();
                textField.setText("google.com");
                device.pressEnter();

                // Verify if the load bar is there at first. Then verify if the loading bar
                // finishes within the default timeout on Wait().
                final UiObject progress =
                        device.findObject(new UiSelector().resourceId(Res.CHROME_PROGRESS_BAR_RES));
                boolean isSuccess =
                        new Wait().until(() -> !progress.exists());
                assertTrue("Failed to dismiss the loading bar.", isSuccess);
            }
        }
    }

    /**
     * Verifies cellular data can be enabled and disabled.
     * <p>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p>
     * TR ID: C14581152
     * <p>
     *   <pre>
     *   Test Steps:
     *   1. Start the emulator.
     *   2. Open Settings > Wireless and Networks > Data Usage
     *   3. Check if 'Data warning & limit' is enabled, toggle Cellular data switch on if not.
     *   4. Toggle Cellular data switch off.
     *   5. Toggle Cellular data switch on.
     *   Verify:
     *   1. Cellular data is turned off.
     *   1. Cellular data is turned on.
     *   </pre>
     * <p>
     */
    @Test
    @TestInfo(id = "14581152")
    public void toggleCellularDataMode() throws Exception {
        final Instrumentation instrumentation = testFramework.getInstrumentation();
        UiDevice device = UiDevice.getInstance(instrumentation);

        String[] path = new String[]{"Settings", "Network & internet", "SIMs"};
        AppLauncher.launchPath(instrumentation, true, path);
        UiScrollable scrollable = new UiScrollable(new UiSelector().scrollable(true));
        final UiObject mobileData = device.findObject(new UiSelector().text("Mobile data"));
        final UiObject dataWarning = device.findObject(new UiSelector().text("Data warning & limit"));

        assertTrue("Scrollable view not found", new Wait().until(scrollable::exists));
        try {
            scrollable.scrollIntoView(mobileData);
        } catch (UiObjectNotFoundException e) {
            fail("Mobile data switch not found initially.");
        }

        try {
            scrollable.scrollIntoView(dataWarning);
            if (!new Wait().until(dataWarning::isEnabled)) {
                scrollable.scrollIntoView(mobileData);
                mobileData.click();
                assertTrue("Data warning label cannot be enabled at the beginning.",
                        new Wait().until(dataWarning::isEnabled));
            }
        } catch (UiObjectNotFoundException e) {
            fail("Enabled data warning label not found at the end.");
        }

        // Disable Cellular data.
        try {
            scrollable.scrollIntoView(mobileData);
            mobileData.click();
            scrollable.scrollIntoView(dataWarning);
            assertFalse("Data warning label cannot be disabled.",
                    new Wait().until(dataWarning::isEnabled));
            TimeUnit.SECONDS.sleep(3); //  Require a sleep to avoid flakiness on buildbot.
        } catch (UiObjectNotFoundException e) {
            fail("Disabled data warning label not found.");
        }

        // Enable Cellular data.
        try {
            scrollable.scrollIntoView(mobileData);
            mobileData.click();
            scrollable.scrollIntoView(dataWarning);
            assertTrue("Data warning label cannot be enabled at the end",
                    new Wait().until(dataWarning::isEnabled));
            TimeUnit.SECONDS.sleep(3); //  Require a sleep to avoid flakiness on buildbot.
        } catch (UiObjectNotFoundException e) {
            fail("Disabled data warning label not found at the end.");
        }

    }

    /**
     * Verifies enabling airplane mode
     *   <pre>
     *   Test Steps:
     *   1. Start the emulator.
     *   2. Open Settings
     *   3. Locate Airplane mode toggle switch.
     *   4. Toggle Airplane mode on.
     *   Verify:
     *   Airplane mode icon is present and enabled in notification tray
     *   5. Toggle Airplane mode off.
     *   </pre>
     * <p>
     */
    @Test
    @TestInfo(id = "14581152")
    public void enableAirplaneMode() throws Exception {
        final Instrumentation instrumentation = testFramework.getInstrumentation();
        UiDevice device = UiDevice.getInstance(instrumentation);

        String[] path = new String[]{"Settings", "Network & internet"};
        AppLauncher.launchPath(instrumentation, true, path);

        UiObject airplaneModeIcon = NetworkUtil.getAirplaneModeIcon_v3(device);

        // Test requires "Airplane mode" switch widget to start in the off state.
        if (NetworkUtil.isAirplaneModeEnabled_v3(device, airplaneModeIcon)) {
            AppLauncher.launchPath(instrumentation, true, path);
            NetworkIOTestUtil.toggleAirplaneMode(device);
        }
        assertFalse("Airplane mode is not disabled.",
                NetworkUtil.isAirplaneModeEnabled_v3(device, airplaneModeIcon));

        AppLauncher.launchPath(instrumentation, true, path);
        NetworkIOTestUtil.toggleAirplaneMode(device);
        assertTrue("Airplane mode is not enabled.",
                NetworkUtil.isAirplaneModeEnabled_v3(device, airplaneModeIcon));

        // Disable airplane mode.
        AppLauncher.launchPath(instrumentation, true, path);
        NetworkIOTestUtil.toggleAirplaneMode(device);
    }

    /**
     * Verifies repeatedly enabling and disabling airplane mode
     *   <pre>
     *   Test Steps:
     *   1. Start the emulator.
     *   2. Open Settings
     *   3. Locate Airplane mode toggle switch.
     *   4. Toggle Airplane mode on.
     *   Verify:
     *   Airplane mode icon is present and enabled in notification tray
     *   5. Toggle Airplane mode off.
     *   6  Repeat steps 3-6 four more times.
     *   </pre>
     * <p>
     */
    @Test
    @TestInfo(id = "14581152")
    public void stressTestAirplaneMode() throws Exception {
        final Instrumentation instrumentation = testFramework.getInstrumentation();
        UiDevice device = UiDevice.getInstance(instrumentation);
        int stressCount = 4;

        String[] path = new String[]{"Settings", "Network & internet"};
        AppLauncher.launchPath(instrumentation, true, path);

        UiObject airplaneModeIcon = NetworkUtil.getAirplaneModeIcon_v3(device);

        // Test requires "Airplane mode" switch widget to start in the off state.
        if (NetworkUtil.isAirplaneModeEnabled_v3(device, airplaneModeIcon)) {
            AppLauncher.launchPath(instrumentation, true, path);
            NetworkIOTestUtil.toggleAirplaneMode(device);
        }
        assertFalse("Airplane mode is not disabled.",
                NetworkUtil.isAirplaneModeEnabled_v2(device, airplaneModeIcon));

        for (int i = 0; i < stressCount; i++) {
            AppLauncher.launchPath(instrumentation, true, path);
            NetworkIOTestUtil.toggleAirplaneMode(device);
            assertTrue("Airplane mode is not enabled.",
                    NetworkUtil.isAirplaneModeEnabled_v3(device, airplaneModeIcon));

            // Disable airplane mode.
            AppLauncher.launchPath(instrumentation, true, path);
            NetworkIOTestUtil.toggleAirplaneMode(device);

            assertFalse("Airplane mode is not disabled.",
                    NetworkUtil.isAirplaneModeEnabled_v3(device, airplaneModeIcon));
        }
    }

    /**
     * Verifies setting Preferred Network Type
     *   <pre>
     *   Test Steps:
     *   1. Start the emulator.
     *   2. Open Settings > Network & internet > SIMs > Preferred Network Type
     *   3. Enable LTE Data mode, if not enabled.
     *   4. Enable 3G Data mode.
     *   5. Enable 2G Data mode.
     *   6. Re-enable LTE Data mode.
     *   Verify:
     *   1. LTE is set as preferred network type.
     *   2. 3G is set as preferred network type.
     *   3. 2G is set as preferred network type.
     *   </pre>
     * <p>
     */
    @Test
    @TestInfo(id = "14581152")
    public void togglePreferredNetworkType() throws Exception {
        final Instrumentation instrumentation = testFramework.getInstrumentation();
        UiDevice device = UiDevice.getInstance(instrumentation);

        String[] path = new String[]{"Settings", "Network & internet", "SIMs"};
        AppLauncher.launchPath(instrumentation, true, path);

        UiObject appByRegex = device.findObject(new UiSelector().textMatches("SIMs"));
        appByRegex.waitUntilGone(5L);

        UiScrollable scrollable = new UiScrollable(new UiSelector().scrollable(true));
        assertTrue("Scrollable view not found", new Wait().until(scrollable::exists));

        UiSelector preferredNetworkTypeSelector = new UiSelector().text("Preferred network type");

        try {
            scrollable.scrollIntoView(preferredNetworkTypeSelector);
        } catch (UiObjectNotFoundException e) {
            fail("Preferred network type not found");
        }

        UiObject preferredNetworkType = device.findObject(preferredNetworkTypeSelector);

        Wait wait = new Wait();
        wait.until(preferredNetworkType::exists);
        preferredNetworkType.clickAndWaitForNewWindow();

        UiObject dataSwitchLTE = device.findObject(new UiSelector().text("LTE (recommended)"));
        if (dataSwitchLTE.waitForExists(5L)) {
            if (!dataSwitchLTE.isChecked()) {
                dataSwitchLTE.clickAndWaitForNewWindow(5L);
            } else {
                device.pressBack();
            }
        }
        assertTrue("LTE data mode is not enabled.", new Wait().until(dataSwitchLTE::exists));
        new Wait().until(preferredNetworkType::exists);
        preferredNetworkType.clickAndWaitForNewWindow();

        UiObject dataSwitch3G = device.findObject(new UiSelector().text("3G"));
        if (dataSwitch3G.waitForExists(5L)) {
            if (!dataSwitch3G.isChecked()) {
                dataSwitch3G.clickAndWaitForNewWindow(5L);
            } else {
                device.pressBack();
            }
        }
        assertTrue("3G data mode is not enabled.", new Wait().until(dataSwitch3G::exists));

        new Wait().until(preferredNetworkType::exists);
        preferredNetworkType.clickAndWaitForNewWindow();

        UiObject dataSwitch2G = device.findObject(new UiSelector().text("2G"));
        if (dataSwitch2G.waitForExists(5L)) {
            if (!dataSwitch2G.isChecked()) {
                dataSwitch2G.clickAndWaitForNewWindow(5L);
            }
            else {
                device.pressBack();
            }
        }
        assertTrue("2G data mode is not enabled.", new Wait().until(dataSwitch2G::exists));

        new Wait().until(preferredNetworkType::exists);
        preferredNetworkType.clickAndWaitForNewWindow();

        if (dataSwitchLTE.waitForExists(5L)) {
            if (!dataSwitchLTE.isChecked()) {
                dataSwitchLTE.clickAndWaitForNewWindow(5L);
            } else {
                device.pressBack();
            }
        }
        assertTrue("LTE data mode is not re-enabled.", new Wait().until(dataSwitchLTE::exists));
    }
}
