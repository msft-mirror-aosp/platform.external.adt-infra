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
import com.android.devtools.systemimage.uitest.utils.DeveloperOptionsManager;
import com.android.devtools.systemimage.uitest.utils.SettingsUtil;
import com.android.devtools.systemimage.uitest.utils.UiAutomatorPlus;
import com.android.devtools.systemimage.uitest.utils.Wait;

import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.Timeout;
import org.junit.runner.RunWith;
import static org.junit.Assert.*;

import android.app.Instrumentation;
import android.support.test.runner.AndroidJUnit4;
import android.support.test.uiautomator.By;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject2;
import android.support.test.uiautomator.UiObjectNotFoundException;
import android.support.test.uiautomator.UiScrollable;
import android.support.test.uiautomator.UiSelector;


/**
 * Test class for Android Settings page on Google API images.
 */
@RunWith(AndroidJUnit4.class)
public class SettingsTest {
    @Rule
    public final SystemImageTestFramework testFramework = new SystemImageTestFramework();

    // Tests under this class may take more than 60 seconds depending on buildbot infrastructure.
    // 90 seconds is a more reliable setup here.
    @Rule
    public Timeout globalTimeout = Timeout.seconds(90);


    /**
     * Verifies Location page opens on Google API images.
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
    @TestInfo(id = "14581163")
    public void testLocationSettingsPageOpen() throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();
        final UiDevice device = testFramework.getDevice();

        if (!testFramework.isGoogleApiImage() || testFramework.getApi() < 23) {
            return;
        }

        SettingsUtil.openItem(instrumentation, "Google");
        device.findObject(new UiSelector().textContains("Location")).clickAndWaitForNewWindow();
        assertTrue("Failed to find Location title.",
                new Wait().until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() throws Exception {
                        return device.findObject(new UiSelector().textContains("Location")).exists();
                    }
                }));
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
     * <p>
     * The test works on API 23 and greater. No gear menu and app permissions for APIs under 23.
     */
    @Test
    @TestInfo(id = "14581153")
    public void displayConfigureAppPermissions() throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();
        UiDevice device = UiDevice.getInstance(instrumentation);

        if (testFramework.getApi() >= 23) {
            SettingsUtil.openItem(instrumentation, "Apps");
            device.findObject(new UiSelector().resourceId(Res.SETTINGS_ADVANCED_OPTION_RES))
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

    /**
     * Common code for finding a checkbox/switch in the Date & time settings.
     */
    private  UiObject2 navigateToDateTimeSwitch(String text) throws UiObjectNotFoundException {
        final Instrumentation instrumentation = testFramework.getInstrumentation();
        SettingsUtil.openItem(instrumentation, "Date & time");

        UiObject2 widget;
        try {
            final String listViewClass = (
                    testFramework.getApi() >= 24) ? "android.support.v7.widget.RecyclerView" :
                    "android.widget.ListView";
            widget = UiAutomatorPlus.findObjectByRelative(
                    instrumentation,
                    By.clazz("android.widget.Switch"),
                    By.text(text),
                    By.clazz(listViewClass));
        } catch (UiObjectNotFoundException e) {
            widget = UiAutomatorPlus.findObjectByRelative(
                    instrumentation,
                    By.clazz("android.widget.CheckBox"),
                    By.text(text),
                    By.clazz("android.widget.ListView"));
        }
        return widget;
    }

    /**
     * Verifies set date and set time fields are editable.
     * <p>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p>
     * TR ID: C14581295
     * <p>
     *   <pre>
     *   1. Start the emulator.
     *   2. Open Settings > Date and time
     *   3. Automatic date & time option is enabled.
     *   4. Disable Automatic date & time option.
     *   5. Set date and Set time options are enabled.
     *   6. Click on Set date option and Set time option.
     *   Verify:
     *   Calendar frame and Clock frame appears respectively.
     *   </pre>
     */
    @Test
    @TestInfo(id = "14581295")
    public void enableSetDateAndSetTime() throws Exception {
        int api = testFramework.getApi();
        final UiDevice device = testFramework.getDevice();
        final UiObject2 widget = navigateToDateTimeSwitch("Automatic date & time");

        // Test requires "Automatic date & time" widget to start in the enabled state.
        if (!widget.isChecked()) {
            widget.click();
        }
        assertTrue("Failed to disable set date.",
                new Wait().until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() throws Exception {
                        return !device.findObject(new UiSelector().text("Set date")).isEnabled();
                    }
                }));
        assertTrue("Failed to disable set time.",
                new Wait().until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() throws Exception {
                        return !device.findObject(new UiSelector().text("Set time")).isEnabled();
                    }
                }));
        widget.click();
        assertTrue("Failed to enable set date.",
                new Wait().until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() throws Exception {
                        return device.findObject(new UiSelector().text("Set date")).isEnabled();
                    }
                }));
        assertTrue("Failed to enable set time.",
                new Wait().until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() throws Exception {
                        return device.findObject(new UiSelector().text("Set time")).isEnabled();
                    }
                }));
        device.findObject(new UiSelector().text("Set date")).clickAndWaitForNewWindow();
        if (api < 20) {
            assertTrue(device.findObject(
                    new UiSelector().resourceId(Res.ANDROID_DATE_PICKER_HEADER_RES_19)).exists());
            device.findObject(new UiSelector().textContains("Done")).click();
            device.findObject(new UiSelector().text("Set time")).click();
            assertTrue(device.findObject(
                    new UiSelector().resourceId(Res.ANDROID_TIME_HEADER_RES_19)).exists());

            device.findObject(new UiSelector().textContains("Done")).click();
        } else {
            assertTrue(device.findObject(
                    new UiSelector().resourceId(Res.ANDROID_DATE_PICKER_HEADER_RES)).exists());
            device.findObject(new UiSelector().textContains("CANCEL")).click();
            device.findObject(new UiSelector().text("Set time")).click();
            assertTrue(device.findObject(
                    new UiSelector().resourceId(Res.ANDROID_TIME_HEADER_RES)).exists());

            device.findObject(new UiSelector().textContains("CANCEL")).click();
        }
    }

    /**
     * Verifies Developer options is displayed under the System section on the Systems page.
     * <p>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p>
     * TR ID: C14581154
     * <p>
     *   <pre>
     *   1. Start the emulator.
     *   2. Open Settings > About emulated device
     *   3. Click on the Build number option 7 times.
     *   4. Toast message indicating developer options is enabled. (Can't confirm due to b/26511336)
     *   5. Navigate to Settings page.
     *   Verify:
     *   Developer options displayed under Systems section on the Settings page.
     *   </pre>
     */
    @Test
    @TestInfo(id = "14581154")
    public void developerOptionsEnabled() throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();
        if (!DeveloperOptionsManager.isDeveloperOptionsEnabled(instrumentation)) {
            DeveloperOptionsManager.enableDeveloperOptions(instrumentation);
        }
        assertTrue("Developer options not enabled.",
                DeveloperOptionsManager.isDeveloperOptionsEnabled(instrumentation));
    }

    /**
     * Verifies show cards confirmation page opens on Google API images.
     * <p>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p>
     * TR ID: C14581322
     * <p>
     *   <pre>
     *   1. Start the emulator.
     *   2. Open Settings > Google > Search and Now > Now Cards
     *   3. Enable Show cards.
     *   Verify:
     *   The show cards confirmation page opens.
     *   </pre>
     */
    @Test
    @TestInfo(id = "14581322")
    public void confirmNowCardsPageOpen() throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();
        final UiDevice device = testFramework.getDevice();

        if (!testFramework.isGoogleApiImage() || testFramework.getApi() < 23) {
            return;
        }

        SettingsUtil.openItem(instrumentation, "Google");
        device.findObject(new UiSelector().text("Search & Now")).click();
        device.findObject(new UiSelector().text("Now cards")).click();

        UiObject2 switchWidget = UiAutomatorPlus.findObjectByRelative(
                instrumentation,
                By.clazz("android.widget.Switch"),
                By.text("Show cards"),
                By.clazz("android.widget.ListView"));
        if (!switchWidget.isChecked()) {
            switchWidget.click();
            assertTrue("Failed to find Now sign-in title and buttons.", new Wait().until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() throws Exception {
                        return device.findObject(new UiSelector().resourceIdMatches(Res.NOW_SIGNIN_SCREEN_RES)).exists()
                                && device.findObject(new UiSelector().resourceIdMatches(Res.NOW_SIGNIN_DECLINE_BUTTON_RES)).exists()
                                && device.findObject(new UiSelector().resourceIdMatches(Res.NOW_SIGNIN_ACCEPT_BUTTON_RES)).exists();
                    }
            }));
        }
    }

    /**
     * Verifies Time Zone option can be enabled.
     * <p>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p>
     * TR ID: C14581409
     * <p>
     *   <pre>
     *   1. Start the emulator.
     *   2. Open Settings > Date & Time
     *   3. Verify automatic time zone option is enabled.
     *   4. Disable automatic time zone.
     *   5. Verify Select time zone is enabled.
     *   6. Enable time zone.
     *   Verify:
     *   Select time zone text and Pacific Daylight Time text can be seen.
     *   </pre>
     */
    @Test
    @TestInfo(id = "14581409")
    public void enableTimeZone() throws Exception {
        final UiDevice device = testFramework.getDevice();
        final UiObject2 widget = navigateToDateTimeSwitch("Automatic time zone");

        // Initialize automatic time zone option to enabled state.
        if (!widget.isChecked()) {
            widget.click();
        }
        assertTrue("Failed to disable select time zone",
            new Wait().until(new Wait.ExpectedCondition() {
                @Override
                public boolean isTrue() throws Exception {
                    return !device.findObject(new UiSelector().text("Select time zone")).isEnabled();
                }
            }));
        // Disable automatic time zone option.
        widget.click();
        assertTrue("Failed to enable select time zone",
            new Wait().until(new Wait.ExpectedCondition() {
                @Override
                public boolean isTrue() throws Exception {
                    return device.findObject(new UiSelector().text("Select time zone")).isEnabled();
                }
            }));
        device.findObject(new UiSelector().text("Select time zone")).clickAndWaitForNewWindow();
        assertTrue("Failed to find Select time zone title.",
                device.findObject(new UiSelector().text("Select time zone")).exists());
        UiScrollable timeZoneList =
                new UiScrollable(
                        new UiSelector().className("android.widget.ListView"));
        try {
            timeZoneList.getChildByText(
                    new UiSelector().className("android.widget.TextView"), "Pacific Daylight Time");
        } catch (UiObjectNotFoundException e) {
            timeZoneList.getChildByText(
                    new UiSelector().className("android.widget.TextView"), "Pacific Time");
        }
    }

    /**
     * Verifies 24-hour format is enabled.
     * <p>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p>
     * TR ID: C14581410
     * <p>
     *   <pre>
     *   1. Start the emulator.
     *   2. Open Settings > Date & Time
     *   3. Verify 24-hour format option is disabled.
     *   4. Verify example time on screen shows 1:00 PM.
     *   5. Enable 24-hour format.
     *   Verify:
     *   Example time on screen shows 13:00.
     *   </pre>
     */
    @Test
    @TestInfo(id = "14581410")
    public void enableTwentyFourHourFormat() throws Exception {
        final UiDevice device = testFramework.getDevice();
        final UiObject2 widget = navigateToDateTimeSwitch("Use 24-hour format");

        // Initialize 24-hour format option to disabled state.
        if (widget.isChecked()) {
            widget.click();
        }
        assertTrue("Failed to find Use 24-hour format.",
                new Wait().until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() throws Exception {
                        return device.findObject(
                                new UiSelector().text("Use 24-hour format")).exists();
                    }
                }));
        assertTrue("Failed to find 1:00 PM.",
                new Wait().until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() throws Exception {
                        return device.findObject(new UiSelector().text("1:00 PM")).exists();
                    }
                }));
        // Enable 24-hour format.
        widget.click();
        assertTrue("Failed to find 13:00.",
                new Wait().until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() throws Exception {
                        return device.findObject(new UiSelector().text("13:00")).exists();
                    }
                }));
        // Clean up by disabling 24-hour format option.
        widget.click();
    }
}
