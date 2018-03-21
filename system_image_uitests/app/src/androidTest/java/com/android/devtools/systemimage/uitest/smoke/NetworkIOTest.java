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

import com.android.devtools.systemimage.uitest.annotations.TestInfo;
import com.android.devtools.systemimage.uitest.common.Res;
import com.android.devtools.systemimage.uitest.framework.SystemImageTestFramework;
import com.android.devtools.systemimage.uitest.utils.AppLauncher;
import com.android.devtools.systemimage.uitest.utils.NetworkUtil;
import com.android.devtools.systemimage.uitest.utils.UiAutomatorPlus;
import com.android.devtools.systemimage.uitest.utils.Wait;
import com.android.devtools.systemimage.uitest.watchers.NetworkUtilPopupWatcher;

import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.Timeout;
import org.junit.runner.RunWith;
import static org.junit.Assert.*;

import android.app.Instrumentation;
import android.content.ContentResolver;
import android.content.Context;
import android.support.test.runner.AndroidJUnit4;
import android.support.test.uiautomator.By;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiObject2;
import android.support.test.uiautomator.UiObjectNotFoundException;
import android.support.test.uiautomator.UiSelector;
import android.support.test.uiautomator.Until;
import android.telephony.TelephonyManager;
import android.provider.Settings;

import java.util.concurrent.TimeUnit;

/**
 * Test class for network connection on emulator.
 */
@RunWith(AndroidJUnit4.class)
public class NetworkIOTest {
    private final String TAG = "NetworkIOTest";

    @Rule
    public final SystemImageTestFramework testFramework = new SystemImageTestFramework();

    @Rule
    public Timeout globalTimeout = Timeout.seconds(240);

    public final TelephonyManager tm = (TelephonyManager)
            testFramework.getInstrumentation().getContext().getSystemService(
                    Context.TELEPHONY_SERVICE);


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
        if (NetworkUtil.hasCellularNetworkConnection(instrumentation) && testFramework.getApi() < 24) {
            AppLauncher.launch(instrumentation, "Browser");
            device.findObject(new UiSelector().resourceId(
                    Res.BROWSER_URL_TEXT_FIELD_RES)).click();
            device.findObject(new UiSelector().resourceId(Res.BROWSER_URL_TEXT_FIELD_RES))
                    .clearTextField();
            device.findObject(new UiSelector().resourceId(Res.BROWSER_URL_TEXT_FIELD_RES))
                    .setText("google.com");
            device.pressEnter();

            // Verify if the load bar is there at first,
            // then verify if the loading bar finishes in 3 seconds (default timeout on Wait()).
            final UiObject progress =
                    device.findObject(new UiSelector().resourceId(Res.BROWSER_SEARCH_ICON_RES));
            boolean isSuccess =
                    new Wait().until(new Wait.ExpectedCondition() {
                        @Override
                        public boolean isTrue() throws Exception {
                            return !progress.exists();
                        }
                    });
            assertTrue("Failed to dismiss the loading bar.", isSuccess);
        }
        // verifyNetworkStatus does not work in API 24. No text or resource ID present in UI.
        if (testFramework.getApi() >= 24 && testFramework.isGoogleApiAndPlayImage()) {
            device.openNotification();
            String cellularData = testFramework.getApi() >= 26 ? "Mobile data" : "Mobile Cellular Data";
            boolean hasCellularData =
                    device.wait(
                            Until.hasObject(By.descContains(cellularData)),
                            TimeUnit.MILLISECONDS.convert(3L, TimeUnit.SECONDS)
                    );
            assertTrue("Could not connect to the network.", hasCellularData);
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
            if (noThanksButton.waitForExists(TimeUnit.SECONDS.toMillis(3))  ) {
                noThanksButton.clickAndWaitForNewWindow();
            }

            UiObject searchBox = device.findObject(new UiSelector().resourceId(
                    Res.CHROME_SEARCH_BOX_RES));
            if (searchBox.exists()) {
                searchBox.clickAndWaitForNewWindow();
            }

            UiObject textField = device.findObject(new UiSelector().resourceId(
                    Res.CHROME_URL_BAR_RES));
            textField.click();
            textField.clearTextField();
            textField.setText("google.com");
            device.pressEnter();

            // Verify if the load bar is there at first. Then verify if the loading bar
            // finishes within the default timeout on Wait().
            final UiObject progress =
                    device.findObject(new UiSelector().resourceId(Res.CHROME_PROGRESS_BAR_RES));
            boolean isSuccess =
                    new Wait().until(new Wait.ExpectedCondition() {
                        @Override
                        public boolean isTrue() throws Exception {
                            return !progress.exists();
                        }
                    });
            assertTrue("Failed to dismiss the loading bar.", isSuccess);
        }
    }



    private UiObject2 navigateToDataSwitch(Instrumentation instrumentation, String label) throws UiObjectNotFoundException {
        String containerRes = (testFramework.getApi() >= 24) ? Res.NETWORK_SWITCHES_RECYCLER_VIEW_RES :
                Res.NETWORK_SWITCHES_CONTAINER_RES;
        String[] path = testFramework.getApi() >= 26 ? new String[] {"Settings", "Network & Internet", "Data usage"} :
                new String[] {"Settings", "Data usage"};

        AppLauncher.launchPath(instrumentation, path);

        return UiAutomatorPlus.findObjectByRelative(
                instrumentation,
                By.clazz("android.widget.Switch"),
                By.text(label),
                By.res(containerRes));
    }

    /**
     * Verifies cellular data can be toggled off.
     * <p>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p>
     * TR ID: C14581152
     * <p>
     *   <pre>
     *   Test Steps:
     *   1. Start the emulator.
     *   2. Open Settings > Wireless and Networks > Data Usage
     *   3. Toggle Cellular data off.
     *   Verify:
     *   Cellular data is turned off.
     *   Text "Set cellular data limit" is on the page.
     *   </pre>
     * <p>
     * The test works on API 23 and greater.
     */
    @Test
    @TestInfo(id = "14581152")
    public void toggleCellularDataOff() throws Exception {
        final Instrumentation instrumentation = testFramework.getInstrumentation();
        UiDevice device = UiDevice.getInstance(instrumentation);
        int api = testFramework.getApi();
        String label = api >= 26 ? "Mobile data" : "Cellular data";

        if (api >= 23) {
            UiObject2 dataSwitch = navigateToDataSwitch(instrumentation, label);

            // Test requires "Cellular data" switch widget to start in the on state.
            if (!dataSwitch.isChecked()) {
                dataSwitch.click();
                new NetworkUtilPopupWatcher(device).checkForCondition();

                // Wait for data connection to turn on.
                boolean isDataOn = new Wait().until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() throws Exception {
                        return NetworkUtil.hasCellularNetworkConnection(instrumentation);
                    }
                });
                assertTrue("Cellular data is disabled.", isDataOn);
            }

            // Disable "Cellular data" option.
            dataSwitch.click();
            new NetworkUtilPopupWatcher(device).checkForCondition();

            // Wait for data connection to turn off.
            boolean isDataOff = new Wait().until(new Wait.ExpectedCondition() {
                @Override
                public boolean isTrue() throws Exception {
                    return !NetworkUtil.hasCellularNetworkConnection(instrumentation);
                }
            });

            assertTrue("Cellular data is enabled.", isDataOff);
            if (api == 23) {
                assertFalse("Set cellular data limit text is visible.", device.findObject(
                        new UiSelector().textContains("Set cellular data limit")).exists());
            } else {
                assertFalse("Set cellular data is not turned off.", device.findObject(
                        new UiSelector().textContains("ON").resourceId(
                                Res.ANDROID_DATA_SWITCH_RES).className(
                                "android.widget.Switch")).exists());
            }

            // Enable Cellular data.
            dataSwitch.click();
        }
    }

    /**
     * Verifies cellular data can be toggled on.
     * <p>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p>
     * TR ID: C14581408
     * <p>
     *   <pre>
     *   Test Steps:
     *   1. Start the emulator.
     *   2. Open Settings > Wireless and Networks > Data Usage
     *   3. Toggle Cellular data on.
     *   Verify:
     *   Cellular data is turned on.
     *   Text "Set cellular data limit" is not on the page.
     *   </pre>
     * <p>
     * The test works on API 23 and greater.
     */
    @Test
    @TestInfo(id = "14581408")
    public void toggleCellularDataOn() throws Exception {
        final Instrumentation instrumentation = testFramework.getInstrumentation();
        UiDevice device = UiDevice.getInstance(instrumentation);
        int api = testFramework.getApi();
        String label = api >= 26 ? "Mobile data" : "Cellular data";

        if (api >= 23) {
            UiObject2 dataSwitch = navigateToDataSwitch(instrumentation, label);

            // Test requires "Cellular data" switch widget to start in the off state.
            if (dataSwitch.isChecked()) {
                dataSwitch.click();
                new NetworkUtilPopupWatcher(device).checkForCondition();

                // Wait for data connection to turn off.
                boolean isDataOff = new Wait().until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() throws Exception {
                        return !NetworkUtil.hasCellularNetworkConnection(instrumentation);
                    }
                });
                assertTrue("Cellular data is enabled.", isDataOff);
            }

            // Enable Cellular data.
            dataSwitch.click();
            new NetworkUtilPopupWatcher(device).checkForCondition();

            // Wait for data connection to turn on.
            boolean isDataOn = new Wait().until(new Wait.ExpectedCondition() {
                @Override
                public boolean isTrue() throws Exception {
                    return NetworkUtil.hasCellularNetworkConnection(instrumentation);
                }
            });
            assertTrue("Cellular data is disabled.", isDataOn);

            if (api == 23) {
                assertTrue("Set cellular data limit text is not visible.", device.findObject(
                        new UiSelector().textContains("Set cellular data limit")).exists());
            } else {
                assertTrue("Set cellular data is not turned on.", device.findObject(
                        new UiSelector().textContains("ON").resourceId(
                                Res.ANDROID_DATA_SWITCH_RES).className(
                                "android.widget.Switch")).exists());
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
     * The test works on API 23 and greater.
     */
    @Test
    @TestInfo(id = "14581152")
    public void enableAirplaneMode() throws Exception {
        final Instrumentation instrumentation = testFramework.getInstrumentation();
        UiDevice device = UiDevice.getInstance(instrumentation);

        if (testFramework.getApi() >= 23) {
            String[] path = testFramework.getApi() >= 26 ? new String[]{"Settings", "Network & Internet"} :
                    new String[]{"Settings", "More"};
            AppLauncher.launchPath(instrumentation, path);

            // Test requires "Airplane mode" switch widget to start in the off state.
            if (NetworkUtil.isAirplaneModeEnabled(device)) {
                AppLauncher.launchPath(instrumentation, path);
                toggleAirplaneMode(device);
            }
            assertFalse("Airplane mode is not disabled.", NetworkUtil.isAirplaneModeEnabled(device));

            AppLauncher.launchPath(instrumentation, path);
            toggleAirplaneMode(device);
            assertTrue("Airplane mode is not enabled.", NetworkUtil.isAirplaneModeEnabled(device));

            // Disable airplane mode.
            AppLauncher.launchPath(instrumentation, path);
            toggleAirplaneMode(device);
        }
    }

    /**
     * Verifies disabling 3G Data mode
     *   <pre>
     *   Test Steps:
     *   1. Start the emulator.
     *   2. Open Settings
     *   3. Launch Preferred Network Type
     *   4. Enable 3G Data mode if not enabled.
     *   5. Toggle 2G Data mode on.
     *   Verify:
     *   2G Data mode icon is set as the Preferred Network Type
     *   6. Toggle 3G Data mode on to reset image.
     *   </pre>
     * <p>
     * The test works on API 19 and greater.
     */
    @Test
    @TestInfo(id = "14581152")
    public void disable3GData() throws Exception {
        final Instrumentation instrumentation = testFramework.getInstrumentation();
        UiDevice device = UiDevice.getInstance(instrumentation);

        if (testFramework.getApi() >= 19) {
            String[] path;
            if (testFramework.getApi() >= 27) {
                path = new String[]{"Settings", "Network & Internet", "Mobile network", "Advanced", "Preferred network type"};
            } else if (testFramework.getApi() == 26) {
                path = new String[]{"Settings", "Network & Internet", "Mobile network", "Preferred network type"};
            } else if (testFramework.getApi() >= 21){
                path = new String[]{"Settings", "More", "Cellular networks", "Preferred network type"};
            } else {
                path = new String[]{"Settings", "More", "Mobile networks", "Preferred network type"};
            }

            AppLauncher.launchPath(instrumentation, path);

            UiObject dataSwitch3G = device.findObject(new UiSelector().text("3G"));
            UiObject dataSwitch2G = device.findObject(new UiSelector().text("2G"));

            // Test requires image to start in 3G data mode.
            if (!dataSwitch3G.isChecked()) {
                dataSwitch3G.clickAndWaitForNewWindow();
                UiObject preferredNetwork = device.findObject(new UiSelector().text("Preferred network type"));
                if (preferredNetwork.exists()) {
                    preferredNetwork.clickAndWaitForNewWindow();
                }
            }
            // Enable 2G data mode option.
            dataSwitch2G.click();

            final UiObject data2GPreferred = device.findObject(new UiSelector().text("2G").
                    packageName(Res.ANDROID_PHONE_RES));

            // Wait for 2G data mode icon
            boolean data2GModeActive = new Wait().until(new Wait.ExpectedCondition() {
                @Override
                public boolean isTrue() throws Exception {
                    return data2GPreferred.exists();
                }
            });

            assertTrue("3G data mode is not disabled.", data2GModeActive);

            // Reset 3G mode.
            data2GPreferred.clickAndWaitForNewWindow();
            dataSwitch3G.click();
        }
    }

    /**
     * Verifies disabling data roaming mode
     *   <pre>
     *   Test Steps:
     *   1. Start the emulator.
     *   2. Open Settings
     *   3. Launch Mobile network
     *   4. Enable data Roaming if not enabled.
     *   5. Toggle data Roaming mode off.
     *   Verify:
     *   Data Roaming is not set in the Telephony manager
     *   6. Toggle data roaming on to reset image.
     *   </pre>
     * <p>
     * The test works on API 18-25.
     * Note: This test cannot be run on API's 26 and greater due to a security exception thrown
     * by Settings.Global in checkRoamingStatus();
     */
    @Test
    @TestInfo(id = "14581152")
    public void disableDataRoaming() throws Exception {
        final Instrumentation instrumentation = testFramework.getInstrumentation();
        UiDevice device = UiDevice.getInstance(instrumentation);
        Context context = testFramework.getInstrumentation().getContext();

        if (testFramework.getApi() >= 18 && testFramework.getApi() <= 25) {
            String[] path;
            if (testFramework.getApi() >= 21) {
                path = new String[]{"Settings", "More", "Cellular networks"};
            } else {
                path = new String[]{"Settings", "More", "Mobile networks"};
            }

            AppLauncher.launchPath(instrumentation, path);

            // Test requires image to start with data roaming active.
            if (!isDataRoamingEnabled(context)) {
                toggleRoaming(device);
            }

            assertTrue("Data roaming is not enabled.", isDataRoamingEnabled(context));

            // Disable data roaming option.
            toggleRoaming(device);

            assertFalse("Data roaming is not disabled.", isDataRoamingEnabled(context));

            toggleRoaming(device);

        }
    }

    /**
     * Helper class to toggle the active data roaming status
     */
    private void toggleAirplaneMode(UiDevice device) throws UiObjectNotFoundException {
        UiObject airplaneModeText = device.findObject(
                new UiSelector().text("Airplane mode"));
        boolean isFound = airplaneModeText.waitForExists(3L);
        if (isFound) {
            airplaneModeText.clickAndWaitForNewWindow();
        }
    }


    /**
     * Helper class to determine if data roaming is enabled
     * Note: this method is blocked on API's 26 and higher by a java.lang.SecurityException
     */
    private boolean isDataRoamingEnabled(Context context) throws Exception {
        try {
            String key = Settings.Global.DATA_ROAMING;
            ContentResolver cr = context.getContentResolver();
            return Settings.Global.getInt(cr, key, 0) == 1 ? true : false;
        } catch (Exception exception) {
            return false;
        }
    }

    /**
     * Helper class to toggle the active data roaming status
     */
    private void toggleRoaming(UiDevice device) throws UiObjectNotFoundException {
        UiObject dataRoamingSwitch = device.findObject(new UiSelector().text("Data roaming"));
        dataRoamingSwitch.clickAndWaitForNewWindow();
        UiObject allowRoaming = device.findObject(new UiSelector().text("OK"));
        if (allowRoaming.exists()) {
            allowRoaming.clickAndWaitForNewWindow();
        }
    }
}