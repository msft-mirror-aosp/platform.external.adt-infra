/*
 * Copyright (c) 2018 The Android Open Source Project
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

package com.android.devtools.systemimage.uitest.tv.api27;

import android.app.Instrumentation;
import androidx.test.runner.AndroidJUnit4;
import androidx.test.uiautomator.UiDevice;
import androidx.test.uiautomator.UiObject;
import androidx.test.uiautomator.UiObjectNotFoundException;
import androidx.test.uiautomator.UiScrollable;
import androidx.test.uiautomator.UiSelector;

import com.android.devtools.systemimage.uitest.annotations.TestInfo;
import com.android.devtools.systemimage.uitest.common.Res;
import com.android.devtools.systemimage.uitest.framework.SystemImageTestFramework;
import com.android.devtools.systemimage.uitest.utils.Wait;

import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.Timeout;
import org.junit.runner.RunWith;

import static org.junit.Assert.assertTrue;

/**
 * Test class for Settings page on Android TV API images.
 */
@RunWith(AndroidJUnit4.class)
public class SettingsTest {
    @Rule
    public final SystemImageTestFramework testFramework = new SystemImageTestFramework();

    private Instrumentation instrumentation = testFramework.getInstrumentation();
    private UiDevice device = UiDevice.getInstance(instrumentation);

    private final static String TAG = "SettingsTest";

    @Rule
    public Timeout globalTimeout = Timeout.seconds(120);

    /**
     * Verifies 24-hour format is enabled.
     * <p>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p>
     * TT ID: f83bf063-2a8c-4d1b-808b-20fd76933135
     * <p>
     *   <pre>
     *   1. Start the Android TV emulator.
     *   2. Open Settings > Device Preferences > Date & time.
     *   3. Disable 24-hour format.
     *   4. Verify example time on screen shows 1:00 PM.
     *   5. Enable 24-hour format.
     *   Verify:
     *   Example time on screen shows 13:00.
     *   </pre>
     */
    @Test
    @TestInfo(id = "f83bf063-2a8c-4d1b-808b-20fd76933135")
    public void enableTwentyFourHourFormat() throws Exception {

        this.openDateTimeSettings();

        UiObject use24 = device.findObject(new UiSelector().text("Use 24-hour format"));
        assertTrue("Failed to find Use 24-hour format switch.", use24.waitForExists(5L));

        boolean useTwentyFourWasEnabled = false;
        final UiObject thirteenHundredLabel = device.findObject(new UiSelector().text("13:00"));

        // Initialize 24-hour format option to disabled state.
        if (thirteenHundredLabel.exists()) {
            useTwentyFourWasEnabled = true;
            use24.click();
        }
        assertTrue("Failed to find Use 24-hour format label.",
                new Wait().until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() {
                        return device.findObject(
                                new UiSelector().text("Use 24-hour format")).exists();
                    }
                })
        );
        assertTrue("Failed to find 1:00 PM label.",
                new Wait().until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() {
                        return device.findObject(new UiSelector().text("1:00 PM")).exists();
                    }
                })
        );
        // Enable 24-hour format.
        use24.click();
        assertTrue("Failed to find 13:00 label.",
                new Wait().until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() {
                        return thirteenHundredLabel.waitForExists(5L);
                    }
                })
        );

        // Clean up by disabling 24-hour format option.
        if (!useTwentyFourWasEnabled) {
            use24.click();
        }
    }

    /**
     * Verifies Time Zone can be set correctly.
     * <p>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p>
     * TT ID: f83bf063-2a8c-4d1b-808b-20fd76933135
     * <p>
     *   <pre>
     *   1. Start the Android TV emulator.
     *   2. Open Settings > Device Preferences > Date & time.
     *   3. Store original time zone offset.
     *   4. Open Set time zone
     *   4. Set the time zone to GMT-5:00.
     *   5. Set the time zone back to the original offset.
     *   Verify:
     *   1. Time zone was set to new value successfully.
     *   2. Time zone was reset successfully.
     *   </pre>
     */
    @Test
    @TestInfo(id = "f83bf063-2a8c-4d1b-808b-20fd76933135")
    public void setTimeZone() throws Exception {

        this.openDateTimeSettings();

        UiObject originalTimeZone = device.findObject(new UiSelector().textContains("GMT"));
        String originalLabel = originalTimeZone.getText();
        int index = originalLabel.indexOf(" ");
        if ( index == -1 ) index = originalLabel.length();
        String originalOffset = originalLabel.substring(0, index);
        
        UiObject setTimeZone = device.findObject(new UiSelector().text("Set time zone"));
        if (setTimeZone.waitForExists(5L)) {
            setTimeZone.clickAndWaitForNewWindow();
        }

        UiScrollable itemList = new UiScrollable(new UiSelector().resourceId(Res.TV_MAIN_FRAME));
        itemList.setAsVerticalList();

        String targetOffset = "GMT-05:00";
        UiSelector targetSelector = new UiSelector().textContains(targetOffset);
        boolean targetFound = itemList.scrollIntoView(targetSelector);
        assertTrue("Target time zone label not found", targetFound);

        UiObject targetTimeZone = device.findObject(targetSelector);
        targetTimeZone.click();
        assertTrue("Target time zone not set", targetTimeZone.waitForExists(5L));

        if (setTimeZone.waitForExists(5L)) {
            setTimeZone.clickAndWaitForNewWindow();
        }

        UiSelector originalSelector = new UiSelector().textContains(originalOffset);
        boolean originalFound = itemList.scrollIntoView(originalSelector);
        assertTrue("Original time zone label not found", originalFound);

        originalTimeZone = device.findObject(originalSelector);
        originalTimeZone.click();
        assertTrue("Original time zone not set", originalTimeZone.waitForExists(5L));
    }

    /**
     * Verifies set date and set time fields are editable.
     * <p>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p>
     * TT ID: f83bf063-2a8c-4d1b-808b-20fd76933135
     * <p>
     *   <pre>
     *   1. Start the Android TV emulator.
     *   2. Open Settings > Device Preferences > Date & time.
     *   3. Ensure that Automatic date & time option is enabled.
     *   4. Disable Automatic date & time option.
     *   5. Set date and Set time options are enabled.
     *   6. Click on Set date option and Set time option.
     *   Verify:
     *   1. Automatic date & time is enabled.
     *   2. Automatic date & time is disabled, Set date and Set time are enabled.
     *   3. Calendar date picker is found.
     *   4. Clock time picker is found.
     *   5. Automatic date & time is re-enabled, Set date and Set time are disabled.
     *   </pre>
     */
    @Test
    @TestInfo(id = "f83bf063-2a8c-4d1b-808b-20fd76933135")
    public void enableSetDateAndSetTime() throws Exception {

        this.openDateTimeSettings();

        // Test requires "Automatic date & time" widget to start in the enabled state.

        final UiObject automaticDateTime = device.findObject(new UiSelector().text("Automatic date & time"));
        final UiObject networkProvidedLabel = device.findObject(new UiSelector().text("Use network-provided time"));
        final UiObject setDate = device.findObject(new UiSelector().text("Set date"));
        final UiObject setTime = device.findObject(new UiSelector().text("Set time"));

        if (automaticDateTime.waitForExists(5L)) {
            automaticDateTime.clickAndWaitForNewWindow();
        }

        if (networkProvidedLabel.waitForExists(5L)) {
            networkProvidedLabel.clickAndWaitForNewWindow();
        }

        assertTrue("Failed to enable automatic date & time.",
                new Wait().until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() {
                        return automaticDateTime.waitForExists(5L) &&
                                networkProvidedLabel.waitForExists(5L);
                    }
                })
        );

        automaticDateTime.clickAndWaitForNewWindow();
        final UiObject offLabel = device.findObject(new UiSelector().text("Off"));
        if (offLabel.waitForExists(5L)) {
            offLabel.clickAndWaitForNewWindow();
        }

        assertTrue("Failed to disable automatic date & time.",
                new Wait().until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() throws Exception {
                        return automaticDateTime.waitForExists(5L) &&
                                offLabel.waitForExists(5L) &&
                                setDate.isEnabled() && setTime.isEnabled();
                    }
                })
        );

        setDate.clickAndWaitForNewWindow();
        final UiObject datePicker = device.findObject(
                new UiSelector().resourceId(Res.TV_DATE_PICKER));
        assertTrue("Date picker not found",
                new Wait().until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() {
                        return datePicker.waitForExists(5L);
                    }
                })
        );

        this.openDateTimeSettings();

        setTime.clickAndWaitForNewWindow();
        final UiObject timePicker = device.findObject(
                new UiSelector().resourceId(Res.TV_TIME_PICKER));
        assertTrue("Time picker not found",
                new Wait().until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() {
                        return timePicker.waitForExists(5L);
                    }
                })
        );

        this.openDateTimeSettings();

        if (automaticDateTime.waitForExists(5L) && !networkProvidedLabel.waitForExists(5L)) {
            automaticDateTime.clickAndWaitForNewWindow();
        }

        if (networkProvidedLabel.waitForExists(5L)) {
            networkProvidedLabel.clickAndWaitForNewWindow();
        }

        assertTrue("Failed to re-enable automatic date & time.",
                new Wait().until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() throws Exception {
                        return automaticDateTime.waitForExists(5L) &&
                                networkProvidedLabel.waitForExists(5L) &&
                                !setDate.isEnabled() && !setTime.isEnabled();
                    }
                })
        );
    }

    // Opens the Date & time Settings on Android TV.
    private void openDateTimeSettings() throws UiObjectNotFoundException {
        device.pressBack();

        UiObject tvLauncher = device.findObject(new UiSelector().resourceId(Res.TV_LAUNCHER));
        if (tvLauncher.waitForExists(10L)) {
            tvLauncher.clickAndWaitForNewWindow();
        }

        UiObject devicePreferences = device.findObject(new UiSelector().text("Device Preferences"));
        if (devicePreferences.waitForExists(5L)) {
            devicePreferences.clickAndWaitForNewWindow();
        }

        UiObject dateTime = device.findObject(new UiSelector().text("Date & time"));
        if (dateTime.waitForExists(5L)) {
            dateTime.clickAndWaitForNewWindow();
        }
    }
}
