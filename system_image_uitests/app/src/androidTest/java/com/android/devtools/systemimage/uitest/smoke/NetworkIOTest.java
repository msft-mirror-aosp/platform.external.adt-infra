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
import com.android.devtools.systemimage.uitest.utils.SettingsUtil;
import com.android.devtools.systemimage.uitest.utils.UiAutomatorPlus;
import com.android.devtools.systemimage.uitest.utils.Wait;

import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.Timeout;
import org.junit.runner.RunWith;
import static org.junit.Assert.*;

import android.app.Instrumentation;
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

import java.util.concurrent.TimeUnit;

/**
 * Test class for network connection on emulator.
 */
@RunWith(AndroidJUnit4.class)
public class NetworkIOTest {
    @Rule
    public final SystemImageTestFramework testFramework = new SystemImageTestFramework();

    @Rule
    public Timeout globalTimeout = Timeout.seconds(60);

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
        if (NetworkUtil.verifyNetworkStatus(device) && testFramework.getApi() < 24) {
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
            String iconDesc = (testFramework.getApi() >= 26) ?
                    "Mobile data" : "Mobile Cellular Data";
            device.openNotification();
            boolean hasCellularData =
                    device.wait(
                            Until.hasObject(By.descContains(iconDesc)),
                                    TimeUnit.MILLISECONDS.convert(3L, TimeUnit.SECONDS)
                    );
            assertTrue("Could not connect to the network.", hasCellularData);
            device.pressHome();

            if (testFramework.getApi() >= 26) {
                device.wait(
                        Until.hasObject(By.desc("Chrome").text("Chrome")),
                        TimeUnit.MILLISECONDS.convert(3L, TimeUnit.SECONDS)
                );
                device.findObject(new UiSelector().description("Chrome").text("Chrome")).
                        clickAndWaitForNewWindow();
            } else {
                AppLauncher.launch(instrumentation, "Chrome");
            }
            // If this is the first launch, dismiss the "Welcome to Chrome" screen.
            boolean hasAcceptButton =
                device.wait(
                        Until.hasObject(By.res(Res.CHROME_TERMS_ACCEPT_BUTTON_RES)),
                        TimeUnit.MILLISECONDS.convert(3L, TimeUnit.SECONDS)
                );
            if (hasAcceptButton) {
                device.findObject(new UiSelector().resourceId(
                        Res.CHROME_TERMS_ACCEPT_BUTTON_RES)).clickAndWaitForNewWindow();
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
        final UiDevice device = UiDevice.getInstance(instrumentation);
        String containerRes = (testFramework.getApi() >= 24) ?
                Res.NETWORK_SWITCHES_RECYCLER_VIEW_RES : Res.NETWORK_SWITCHES_CONTAINER_RES;
        String[] path = testFramework.getApi() >= 26 ? new String[] {"Settings", "Network & Internet", "Data Uuage"} :
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
            }
            // Disable "Cellular data" option.
            dataSwitch.click();
            if (api == 23) {
                device.findObject(new UiSelector().text("OK")).click();
            }
            // Wait for data connection to turn off.
            new Wait().until(new Wait.ExpectedCondition() {
                @Override
                public boolean isTrue() throws Exception {

                    return !NetworkUtil.hasCellularNetworkConnection(instrumentation);
                }
            });

            assertFalse("Cellular data is enabled.",
                    NetworkUtil.hasCellularNetworkConnection(instrumentation));
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
                if (api == 23) {
                    device.findObject(new UiSelector().text("OK")).click();
                }
            }
            // Enable Cellular data.
            dataSwitch.click();
            // Wait for data connection to turn off.
            new Wait().until(new Wait.ExpectedCondition() {
                @Override
                public boolean isTrue() throws Exception {

                    return NetworkUtil.hasCellularNetworkConnection(instrumentation);
                }
            });
            assertTrue("Cellular data is disabled.",
                    NetworkUtil.hasCellularNetworkConnection(instrumentation));

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
     * Verifies toggling airplane mode on.
     * <p>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p>
     * TR ID: C14581152
     * <p>
     *   <pre>
     *   Test Steps:
     *   1. Start the emulator.
     *   2. Open Settings.
     *   3. Locate Airplane mode toggle switch.
     *   4. Toggle Airplane mode on (verify).
     *   5. Toggle Airplane mode off (cleanup).
     *   Verify:
     *   Airplane mode icon is present and enabled in notification tray.
     *   </pre>
     * <p>
     * The test works on API 17 and greater.
     */
    @Test
    @TestInfo(id = "14581152")
    public void toggleAirplaneMode() throws Exception {
        final Instrumentation instrumentation = testFramework.getInstrumentation();
        UiDevice device = UiDevice.getInstance(instrumentation);

        if (testFramework.getApi() >= 17) {
            String[] path = testFramework.getApi() >= 26 ? new String[]{"Settings", "Network & Internet"} :
                    new String[]{"Settings", "More"};
            String airplaneToggle;

            if (testFramework.getApi() >= 24) {
                airplaneToggle = "android:id/switch_widget";
            } else if (testFramework.getApi() >= 21) {
                airplaneToggle = "android:id/switchWidget";
            } else {
                airplaneToggle = "android:id/checkbox";
            }

            AppLauncher.launchPath(instrumentation, path);

            UiObject airplaneModeSwitch = device.findObject(
                    new UiSelector().resourceId(airplaneToggle));

            // Test requires "Airplane mode" switch widget to start in the off state.
            if (airplaneModeSwitch.isChecked()) {
                airplaneModeSwitch.click();
            }
            // Disable "Airplane mode" option.
            airplaneModeSwitch.click();

            final UiObject airplaneModeIcon = testFramework.getApi() >= 24 ?
                    device.findObject(new UiSelector().description("Airplane mode")) :
                    device.findObject(new UiSelector().resourceId("com.android.systemui:id/airplane"));

            device.openNotification();

            // Wait for airplane mode icon.
            boolean airplaneModeActive = new Wait().until(new Wait.ExpectedCondition() {
                @Override
                public boolean isTrue() throws Exception {
                    return airplaneModeIcon.exists() && airplaneModeIcon.isEnabled();
                }
            });

            assertTrue("Airplane mode is not enabled.", airplaneModeActive);

            // Disable airplane mode.
            AppLauncher.launchPath(instrumentation, path);
            device.findObject(new UiSelector().resourceId(airplaneToggle)).click();

        }
    }
}