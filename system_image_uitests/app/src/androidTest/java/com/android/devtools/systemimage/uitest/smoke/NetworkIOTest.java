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

import com.android.devtools.systemimage.uitest.common.Res;
import com.android.devtools.systemimage.uitest.framework.SystemImageTestFramework;
import com.android.devtools.systemimage.uitest.utils.AppLauncher;
import com.android.devtools.systemimage.uitest.utils.NetworkUtil;
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
import android.support.test.uiautomator.UiScrollable;
import android.support.test.uiautomator.UiSelector;
import android.telephony.TelephonyManager;

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
    public void testBrowserLoadsSite() throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();
        UiDevice device = testFramework.getDevice();

        // Check network connectivity.
        if (NetworkUtil.verifyNetworkStatus(device)) {
            AppLauncher.launch(instrumentation, "Browser");
            device.findObject(new UiSelector().resourceId(Res.BROWSER_URL_TEXT_FIELD_RES)).click();
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
     */
    @Test
    public void toggleCellularDataOff() throws Exception {
        final Instrumentation instrumentation = testFramework.getInstrumentation();
        UiDevice device = UiDevice.getInstance(instrumentation);
        // TODO: Add a fixture method in AppLauncher class to launch a specified path.
        AppLauncher.launch(instrumentation, "Settings");
        UiScrollable itemList = new UiScrollable(
                new UiSelector().resourceIdMatches(Res.SETTINGS_LIST_CONTAINER_RES));
        itemList.setAsVerticalList();
        itemList.scrollToBeginning(100);
        device.findObject(new UiSelector().textContains("Data usage")).click();

        UiObject2 dataSwitch = UiAutomatorPlus.findObjectByRelative(
                instrumentation,
                By.clazz("android.widget.Switch"),
                By.text("Cellular data"),
                By.res(Res.NETWORK_SWITCHES_CONTAINER_RES));
        // Test requires "Cellular data" switch widget to start in the on state.
        if (!dataSwitch.isChecked()) {
            dataSwitch.click();
        }
        // Disable "Cellular data" option.
        dataSwitch.click();
        device.findObject(new UiSelector().text("OK")).click();
        // Wait for data connection to turn off.
        new Wait().until(new Wait.ExpectedCondition() {
            @Override
            public boolean isTrue() throws Exception {

                return !NetworkUtil.hasCellularNetworkConnection(instrumentation);
            }
        });

        assertFalse("Cellular data is enabled.",
                NetworkUtil.hasCellularNetworkConnection(instrumentation));
        if (device.findObject(
                new UiSelector().textContains("Set cellular data limit")).exists()) {
            assertTrue("Set cellular data limit text not visible.", false);
        }
        // Enable Cellular data.
        dataSwitch.click();
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
     */
    @Test
    public void toggleCellularDataOn() throws Exception {
        final Instrumentation instrumentation = testFramework.getInstrumentation();
        UiDevice device = UiDevice.getInstance(instrumentation);
        // TODO: Add a fixture method in AppLauncher class to launch a specified path.
        AppLauncher.launch(instrumentation, "Settings");
        UiScrollable itemList = new UiScrollable(
                new UiSelector().resourceIdMatches(Res.SETTINGS_LIST_CONTAINER_RES));
        itemList.setAsVerticalList();
        itemList.scrollToBeginning(100);
        device.findObject(new UiSelector().textContains("Data usage")).click();

        UiObject2 dataSwitch = UiAutomatorPlus.findObjectByRelative(
                instrumentation,
                By.clazz("android.widget.Switch"),
                By.text("Cellular data"),
                By.res(Res.NETWORK_SWITCHES_CONTAINER_RES));
        // Test requires "Cellular data" switch widget to start in the off state.
        if (dataSwitch.isChecked()) {
            dataSwitch.click();
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

        if (!device.findObject(
                new UiSelector().textContains("Set cellular data limit")).exists()) {
            assertTrue("Set cellular data limit text is visible.", false);
        }
        // Disable Cellular data.
        dataSwitch.click();
        device.findObject(new UiSelector().text("OK")).click();
    }
}