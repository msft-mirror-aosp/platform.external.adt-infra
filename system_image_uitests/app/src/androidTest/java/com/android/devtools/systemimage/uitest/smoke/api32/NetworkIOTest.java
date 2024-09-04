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

package com.android.devtools.systemimage.uitest.smoke.api32;

import android.app.Instrumentation;
import android.util.Log;

import androidx.test.espresso.IdlingResource;
import androidx.test.espresso.IdlingRegistry;
import androidx.test.runner.AndroidJUnit4;
import androidx.test.uiautomator.UiDevice;
import androidx.test.uiautomator.UiObject;
import androidx.test.uiautomator.UiObjectNotFoundException;
import androidx.test.uiautomator.UiScrollable;
import androidx.test.uiautomator.UiSelector;

import com.android.devtools.systemimage.uitest.annotations.TestInfo;
import com.android.devtools.systemimage.uitest.common.Res;
import com.android.devtools.systemimage.uitest.framework.SystemImageTestFramework;
import com.android.devtools.systemimage.uitest.utils.AppLauncher;
import com.android.devtools.systemimage.uitest.utils.NetworkIOTestUtil;
import com.android.devtools.systemimage.uitest.utils.NetworkUtil;
import com.android.devtools.systemimage.uitest.utils.Wait;

import junit.framework.Assert;

import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.Timeout;
import org.junit.runner.RunWith;

import java.io.IOException;
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
    public Timeout globalTimeout = Timeout.seconds(1000);

    private final String TAG = "NetworkIOTest";

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

        SettingsIdlingResource idlingResource = null;
        try {
            UiScrollable scrollableContainer = new UiScrollable(new UiSelector().resourceIdMatches(Res.CONTENT_FRAME_CONTAINER_RES));
            new UiScrollable(new UiSelector().resourceIdMatches(Res.CONTENT_FRAME_CONTAINER_RES));
            idlingResource = new SettingsIdlingResource(scrollableContainer);
            IdlingRegistry.getInstance().register(idlingResource);
            String mobileDataSwitch = "Mobile data";
            String mobileDataWarning = "Data warning & limit";

            if (!(navigateToSettingsPath(device, "Network & internet", "SIMs"))) {
                fail("Failed to navigate to Network & internet > SIMs settings.");
            }

            UiScrollable scrollable = new UiScrollable(new UiSelector().scrollable(true));
            final UiObject dataWarning = device.findObject(new UiSelector().text(mobileDataWarning));

            boolean isCellularDataEnabled = false;
            try {
                scrollable.scrollIntoView(dataWarning);
                isCellularDataEnabled = new Wait().until(dataWarning::isEnabled);
            } catch (UiObjectNotFoundException e) {
                fail("Data warning & limit setting not found.");
            }

            if (!isCellularDataEnabled) {
                assertTrue("Mobile data switch not enabled.", clickAndConfirmSwitch(device, mobileDataSwitch));
                assertTrue("Scrollable view not found", new Wait().until(scrollable::exists));
                try {
                    scrollable.scrollIntoView(dataWarning);
                    assertTrue("Data warning label cannot be enabled at the beginning.",
                            new Wait().until(dataWarning::isEnabled));
                } catch (UiObjectNotFoundException e) {
                    fail("Enabled data warning label not found at the end.");
                }
            }

            assertTrue("Mobile data switch not disabled.", clickAndConfirmSwitch(device, mobileDataSwitch));
            try {
                scrollable.scrollIntoView(dataWarning);
                assertFalse("Data warning label cannot be disabled.",
                        new Wait().until(dataWarning::isEnabled));
            } catch (UiObjectNotFoundException e) {
                fail("Disabled data warning label not found.");
            }
            assertTrue("Mobile data switch not reset.", clickAndConfirmSwitch(device, mobileDataSwitch));
            try {
                scrollable.scrollIntoView(dataWarning);
                assertTrue("Data warning label cannot be enabled at the end",
                        new Wait().until(dataWarning::isEnabled));
            } catch (UiObjectNotFoundException e) {
                fail("Disabled data warning label not found at the end.");
            }
        }

        finally {
            if (idlingResource != null) {
                IdlingRegistry.getInstance().unregister(idlingResource);
            }
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
        SettingsIdlingResource idlingResource = null;
        try {
            UiScrollable scrollableContainer = new UiScrollable(new UiSelector().resourceIdMatches(Res.CONTENT_FRAME_CONTAINER_RES));
            new UiScrollable(new UiSelector().resourceIdMatches(Res.CONTENT_FRAME_CONTAINER_RES));
            idlingResource = new SettingsIdlingResource(scrollableContainer);
            IdlingRegistry.getInstance().register(idlingResource);
            UiObject airplaneModeIcon = NetworkUtil.getAirplaneModeIcon_v3(device);

            if (!(navigateToSettingsPath(device, "Network & internet"))) {
                fail("Failed to navigate to Network & internet settings.");
            }

            // Test requires "Airplane mode" switch widget to start in the off state.
            if (NetworkUtil.isAirplaneModeEnabled_v3(device, airplaneModeIcon)) {
                navigateToSettingsPath(device, "Network & internet", "Airplane mode");
            }
            assertFalse("Airplane mode is not disabled.",
                    NetworkUtil.isAirplaneModeEnabled_v3(device, airplaneModeIcon));

            // Enable airplane mode.
            navigateToSettingsPath(device, "Network & internet", "Airplane mode");
            assertTrue("Airplane mode is not enabled.",
                    NetworkUtil.isAirplaneModeEnabled_v3(device, airplaneModeIcon));

            // Disable airplane mode.
            navigateToSettingsPath(device, "Network & internet", "Airplane mode");
            assertFalse("Airplane mode is not disabled.",
                    NetworkUtil.isAirplaneModeEnabled_v3(device, airplaneModeIcon));
        }
        finally {
            if (idlingResource != null) {
                IdlingRegistry.getInstance().unregister(idlingResource);
            }
        }
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

        String dataSwitchLTE = "LTE (recommended)";
        String dataSwitch3G = "3G";
        String dataSwitch2G = "2G";

        if (!(navigateToSettingsPath(device, "Network & internet", "SIMs", "Preferred network type"))) {
            fail("Failed to navigate to Network & internet > SIMs settings > Preferred network type.");
        }
        clickAndConfirmSwitch(device, dataSwitchLTE);

        navigateToSettingsPath(device, "Network & internet", "SIMs", "Preferred network type");
        clickAndConfirmSwitch(device, dataSwitch3G, dataSwitchLTE);

        navigateToSettingsPath(device, "Network & internet", "SIMs", "Preferred network type");
        clickAndConfirmSwitch(device, dataSwitch2G, dataSwitch3G);

        navigateToSettingsPath(device, "Network & internet", "SIMs", "Preferred network type");
        assertTrue("LTE switch not reset.", clickAndConfirmSwitch(device, dataSwitchLTE, dataSwitch2G));
    }

    /**
     * Navigates to a specified path in the Settings app.
     *
     * This method launches the Settings app and then navigates to a specified path by clicking on the options
     * in the order they are provided. The navigation is performed by scrolling through either the
     * 'main_content_scrollable_container' or the 'content_frame' depending on the pass of the loop.
     *
     * @param device The UiDevice instance that represents an emulator or a connected device.
     * @param path An array of Strings where each String is the name of an option in the Settings app.
     * @return true if the method was able to find and click on all the options in the path array, false otherwise.
     * @throws UiObjectNotFoundException if an option in the path array is not found.
     */
    private boolean navigateToSettingsPath(UiDevice device, String... path) throws UiObjectNotFoundException {
        device.pressHome();

        try {
            device.executeShellCommand("am start -a android.settings.SETTINGS");
        } catch (IOException e) {
            Log.w(TAG, "Failed to launch Settings", e);
            return false;
        }
        for (int i = 0; i < path.length; i++) {
            String location = path[i];
            UiScrollable scrollableContainer = i == 0 ?
                    new UiScrollable(new UiSelector().resourceIdMatches(Res.SETTINGS_LIST_CONTAINER_RES)) :
                    new UiScrollable(new UiSelector().resourceIdMatches(Res.CONTENT_FRAME_CONTAINER_RES));
            SettingsIdlingResource idlingResource = new SettingsIdlingResource(scrollableContainer);
            IdlingRegistry.getInstance().register(idlingResource);
            assertTrue("Scrollable view not found", scrollableContainer.waitForExists(15000));
            UiSelector optionSelector = new UiSelector().text(location);
            UiObject option = device.findObject(optionSelector);

            dismissUnresponsivePopup(device);

            if (!option.waitForExists(10000L)) {
                boolean scrolled = scrollableContainer.scrollIntoView(optionSelector);
                if (!scrolled) {
                    Log.w(TAG, "Failed to navigate to " + location);
                    IdlingRegistry.getInstance().unregister(idlingResource);

                    return false;
                }
            }
            if (!option.clickAndWaitForNewWindow(15000L)) {
                Log.w(TAG, "Failed to click on " + location);
                IdlingRegistry.getInstance().unregister(idlingResource);

                return false;
            }

            IdlingRegistry.getInstance().unregister(idlingResource);
        }

        return true;
    }

    /**
     * This method is used to click on a switch in the Settings app and confirm that the switch has been clicked.
     * It first checks if the previous switches (if any) exist and then clicks on the target switch.
     * If any of the previous switches or the target switch do not exist, it logs a warning and returns false.
     * If all switches exist and the target switch is clicked successfully, it returns true.
     *
     * @param device The UiDevice instance that represents an emulator or a connected device.
     * @param switchLabel The label of the switch that this method will click on.
     * @param previousSwitchLabels The labels of the switches that this method will check for existence before clicking on the target switch.
     * @return true if all switches exist and the target switch is clicked successfully, false otherwise.
     */
    private boolean clickAndConfirmSwitch(UiDevice device, String switchLabel, String ...previousSwitchLabels) {
        UiScrollable scrollableContainer = new UiScrollable(new UiSelector().resourceIdMatches(Res.CONTENT_FRAME_CONTAINER_RES));
        SettingsIdlingResource idlingResource = new SettingsIdlingResource(scrollableContainer);
        IdlingRegistry.getInstance().register(idlingResource);

        try {
            dismissUnresponsivePopup(device);

            for (String previousSwitchLabel : previousSwitchLabels) {
                UiObject previousSwitchObject = device.findObject(new UiSelector().text(previousSwitchLabel));
                if (!previousSwitchObject.waitForExists(10000L)) {
                    Log.w(TAG, "Failed to find previous switch object" + previousSwitchLabel);
                    IdlingRegistry.getInstance().unregister(idlingResource);
                    return false;
                }
            }

            UiObject switchObject = device.findObject(new UiSelector().text(switchLabel));
            if (switchObject.waitForExists(10000L)) {
                switchObject.clickAndWaitForNewWindow(10000L);
            }
            IdlingRegistry.getInstance().unregister(idlingResource);

            return true;
        } catch (UiObjectNotFoundException e) {
            Log.w(TAG, "Failed to find switch object" + switchLabel, e);
            IdlingRegistry.getInstance().unregister(idlingResource);

            return false;
        }
    }

    /**
     * This method is used to dismiss any unresponsive popup that might appear during the execution of the tests.
     * It first tries to find the unresponsive popup by its resource id. If the popup exists, it clicks on it to dismiss it.
     *
     * @param device The UiDevice instance that represents an emulator or a connected device.
     * @throws UiObjectNotFoundException if the unresponsive popup is not found.
     */
    private void dismissUnresponsivePopup(UiDevice device) throws UiObjectNotFoundException {
        UiObject notRespondingError = device.findObject(
                new UiSelector().resourceId(Res.ANDROID_ERROR_WAIT_RES));
        if (notRespondingError.waitForExists(5000L)) {
            notRespondingError.click();
            notRespondingError.waitUntilGone(5000L);
        }
    }

    /**
     * An implementation of the IdlingResource interface. This class is used to notify Espresso that the app is idle or busy.
     * An instance of this class is created with a UiObject.
     * The UiObject is the object that this idling resource will be waiting on (i.e., it will wait until this object exists).
     */
    private class SettingsIdlingResource implements IdlingResource {
        private ResourceCallback resourceCallback;
        private final UiObject idleTarget;

        /**
         * Constructs a SettingsIdlingResource with the given UiDevice and UiObject.
         *
         * @param idleTarget The object that this idling resource will be waiting on.
         */
        public SettingsIdlingResource(UiObject idleTarget) {
            this.idleTarget = idleTarget;
        }

        /**
         * Returns the name of the idling resource.
         *
         * @return The name of the idling resource.
         */
        @Override
        public String getName() {
            return SettingsIdlingResource.class.getName();
        }

        /**
         * Checks if the app is idle. In this case, the app is considered idle if the idleTarget exists.
         *
         * @return true if the app is idle, false otherwise.
         */
        @Override
        public boolean isIdleNow() {
            boolean isIdle = idleTarget.exists();

            if (isIdle && resourceCallback != null) {
                resourceCallback.onTransitionToIdle();
            }

            return isIdle;
        }

        /**
         * Registers the callback to be invoked when the app transitions from busy to idle.
         *
         * @param resourceCallback The callback to be invoked when the app transitions from busy to idle.
         */
        @Override
        public void registerIdleTransitionCallback(ResourceCallback resourceCallback) {
            this.resourceCallback = resourceCallback;
        }
    }
}
