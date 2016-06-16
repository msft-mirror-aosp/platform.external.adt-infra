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

import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.Timeout;
import org.junit.runner.RunWith;
import static org.junit.Assert.*;

import android.app.Instrumentation;
import android.support.test.runner.AndroidJUnit4;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiScrollable;
import android.support.test.uiautomator.UiSelector;


/**
 * Test class for Android Settings page on Google API images.
 */
@RunWith(AndroidJUnit4.class)
public class SettingsTest {
    private static final String APP_IMAGE_SETTINGS_ID = "com.android.settings:id/advanced";

    @Rule
    public final SystemImageTestFramework testFramework = new SystemImageTestFramework();

    @Rule
    public Timeout globalTimeout = Timeout.seconds(60);

    /**
     * Verifies Location page opens.
     * <p>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p>
     * TR ID: C14581163
     * <p>
     *   <pre>
     *   1. Start the emulator.
     *   2. Open Settings > Google > Location
     *   Verify:
     *   Location settings page opens.
     *   </pre>
     */
    @Test
    public void testLocationSettingsPageOpen() throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();
        UiDevice device = testFramework.getDevice();
        AppLauncher.launch(instrumentation, "Settings");
        UiScrollable itemList = new UiScrollable(
                new UiSelector().resourceIdMatches(Res.SETTINGS_LIST_CONTAINER_RES));
        itemList.setAsVerticalList();
        itemList.scrollIntoView(new UiSelector().textContains("Google"));
        device.findObject(new UiSelector().textContains("Google")).clickAndWaitForNewWindow();
        device.findObject(new UiSelector().textContains("Location")).clickAndWaitForNewWindow();
        assertTrue(device.findObject(new UiSelector().textContains("Location")).exists());
    }

    /**
     * Verifies the App permissions screen loads.
     * <p>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p>
     * TR ID: C14581153
     * <p>
     *   <pre>
     *   1. Start the emulator.
     *   2. Open Settings > Apps
     *   3. Click on the gear icon.
     *   4. Click on App permissions.
     *   Verify:
     *   App permissions page loads. Able to identify various apps on the page.
     *   </pre>
     */
    @Test
    public void displayConfigureAppPermissions() throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();
        UiDevice device = UiDevice.getInstance(instrumentation);

        AppLauncher.launch(instrumentation, "Settings");
        device.findObject(new UiSelector().textContains("Apps")).clickAndWaitForNewWindow();
        device.findObject(new UiSelector().resourceId(APP_IMAGE_SETTINGS_ID))
                .clickAndWaitForNewWindow();
        device.findObject(new UiSelector().textContains("App permissions"))
                .clickAndWaitForNewWindow();

        assertTrue(device.findObject(new UiSelector().textContains("App permissions")).exists()
                && device.findObject(new UiSelector().textContains("Calendar")).exists()
                && device.findObject(new UiSelector().textContains("Camera")).exists()
                && device.findObject(new UiSelector().textContains("Contacts")).exists()
                && device.findObject(new UiSelector().textContains("Phone")).exists()
                && device.findObject(new UiSelector().description("Navigate up")).exists());
    }
}
