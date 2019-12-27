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

package com.android.devtools.systemimage.uitest.smoke.api21;

import android.app.Instrumentation;
import android.support.test.runner.AndroidJUnit4;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiObject2;
import android.support.test.uiautomator.UiScrollable;
import android.support.test.uiautomator.UiSelector;
import android.util.Log;

import com.android.devtools.systemimage.uitest.annotations.TestInfo;
import com.android.devtools.systemimage.uitest.common.Res;
import com.android.devtools.systemimage.uitest.framework.SystemImageTestFramework;
import com.android.devtools.systemimage.uitest.utils.ApiDemosInstaller;
import com.android.devtools.systemimage.uitest.utils.DeveloperOptionsManager;
import com.android.devtools.systemimage.uitest.utils.PackageInstallationUtil;
import com.android.devtools.systemimage.uitest.utils.SettingsUtil;
import com.android.devtools.systemimage.uitest.utils.Wait;

import org.junit.Assert;
import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.Timeout;
import org.junit.runner.RunWith;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

/**
 * Test class for Android Settings page on Google API images.
 */
@RunWith(AndroidJUnit4.class)
public class SettingsTest {
    @Rule
    public final SystemImageTestFramework testFramework = new SystemImageTestFramework();

    private Instrumentation instrumentation = testFramework.getInstrumentation();
    private UiDevice device = UiDevice.getInstance(instrumentation);

    private final static String TAG = "SettingsTest";

    // Tests under this class takes up to 240 seconds depending on the performance of the bot the
    // tests run on.
    @Rule
    public Timeout globalTimeout = Timeout.seconds(240);

    @Before
    public void activateDeviceAdmin() throws Exception {
        ApiDemosInstaller.installApp("Security", "Device administrators");
    }

    /**
     * Verifies Developer options is displayed under the System section on the Systems page.
     * <p>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p>
     * TT ID: 4578f63f-7d2e-4e5e-a4e0-0ce2ae67982e
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
    @TestInfo(id = "4578f63f-7d2e-4e5e-a4e0-0ce2ae67982e")
    public void developerOptionsEnabled() throws Exception {
        if (!DeveloperOptionsManager.isDeveloperOptionsEnabled_v1(testFramework)) {
            DeveloperOptionsManager.enableDeveloperOptions_v1(testFramework);
        } else {
            return;
        }
        assertTrue("Failed to enable Developer options.",
                DeveloperOptionsManager.isDeveloperOptionsEnabled_v1(testFramework));
    }

    /**
     * Verifies set date and set time fields are editable.
     * <p>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p>
     * TT ID: f83bf063-2a8c-4d1b-808b-20fd76933135
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
    @TestInfo(id = "f83bf063-2a8c-4d1b-808b-20fd76933135")
    public void enableSetDateAndSetTime() throws Exception {
        try {
            SettingsUtil.openItem(instrumentation, "Date & time");
        } catch (Exception e) {
            Log.e(TAG, e.getMessage());
        }

        final UiObject2 widget = SettingsUtil.navigateToDateTimeSwitch("Automatic date & time", instrumentation, Res.ANDROID_LIST_RES);

        // Test requires "Automatic date & time" widget to start in the enabled state.
        assert widget != null;
        if (!widget.isChecked()) {
            widget.click();
        }
        assertTrue("Failed to disable set date.",
                new Wait().until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() throws Exception {
                        return !device.findObject(new UiSelector().text("Set date")).isEnabled();
                    }
                })
        );
        assertTrue("Failed to disable set time.",
                new Wait().until(() -> !device.findObject(new UiSelector().text("Set time")).isEnabled())
        );
        widget.click();
        assertTrue("Failed to enable set date.",
                new Wait().until(() -> device.findObject(new UiSelector().text("Set date")).isEnabled())
        );
        assertTrue("Failed to enable set time.",
                new Wait().until(() -> device.findObject(new UiSelector().text("Set time")).isEnabled())
        );
        device.findObject(new UiSelector().text("Set date")).clickAndWaitForNewWindow();

        assertTrue(device.findObject(
                new UiSelector().resourceId(Res.ANDROID_DATE_PICKER_HEADER_RES_19)).exists());
        device.findObject(new UiSelector().textContains("OK")).click();
        device.findObject(new UiSelector().text("Set time")).click();
        assertTrue(device.findObject(
                new UiSelector().resourceId(Res.ANDROID_TIME_HEADER_RES_19)).exists());

        device.findObject(new UiSelector().textContains("OK")).click();
    }

    /**
     * Verifies Time Zone option can be enabled.
     * <p>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p>
     * TT ID: f83bf063-2a8c-4d1b-808b-20fd76933135
     * <p>
     *   <pre>
     *   1. Start the emulator.
     *   2. Open Settings > Date & Time
     *   3. Verify automatic time zone option is enabled.
     *   4. Disable automatic time zone.
     *   5. Verify Select time zone is enabled.
     *   6. Enable time zone.
     *   Verify:
     *   Select time zone text and timezone offset text can be seen.
     *   </pre>
     */
    @Test
    @TestInfo(id = "f83bf063-2a8c-4d1b-808b-20fd76933135")
    public void enableTimeZone() throws Exception {
        try {
            SettingsUtil.openItem(instrumentation, "Date & time");
        } catch (Exception e) {
            Log.e(TAG, e.getMessage());
        }

        final UiObject2 widget = SettingsUtil.navigateToDateTimeSwitch("Automatic time zone", instrumentation, Res.ANDROID_LIST_RES);

        // Initialize automatic time zone option to enabled state.
        assert widget != null;
        if (!widget.isChecked()) {
            widget.click();
        }
        assertTrue("Failed to disable select time zone",
                new Wait().until(() -> !device.findObject(new UiSelector().text("Select time zone")).isEnabled())
        );
        // Disable automatic time zone option.
        widget.click();
        final UiObject selectTimeZone = device.findObject(
                new UiSelector().text("Select time zone"));
        assertTrue("Failed to enable select time zone",
                new Wait().until(selectTimeZone::isEnabled)
        );
        selectTimeZone.clickAndWaitForNewWindow();

        assertTrue("Failed to load Select time zone screen.",
                new Wait().until(() -> device.findObject(
                        new UiSelector().text("Select time zone")).exists())
        );

        UiObject timeZoneLabel = device.findObject(new UiSelector().text("Time zone").
                resourceId(Res.ANDROID_TITLE_RES).packageName("com.android.settings"));
        if (timeZoneLabel.waitForExists(3L)) {
            timeZoneLabel.clickAndWaitForNewWindow();
        }
        UiScrollable timeZoneList =
                new UiScrollable(new UiSelector().className("android.widget.ListView"));

        String timezoneOffset = "GMT-08:00";

        assertTrue("Target time zone label not found",
                timeZoneList.getChildByText(
                        new UiSelector().className("android.widget.TextView"), timezoneOffset).exists());
    }

    /**
     * Verifies 24-hour format is enabled.
     * <p>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p>
     * TT ID: f83bf063-2a8c-4d1b-808b-20fd76933135
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
    @TestInfo(id = "f83bf063-2a8c-4d1b-808b-20fd76933135")
    public void enableTwentyFourHourFormat() throws Exception {
        try {
            SettingsUtil.openItem(instrumentation, "Date & time");
        } catch (Exception e) {
            Log.e(TAG, e.getMessage());
        }

        final UiObject2 useTwentyFourSwitch = SettingsUtil.navigateToDateTimeSwitch("Use 24-hour format", instrumentation, Res.ANDROID_LIST_RES);

        assertTrue("Failed to find Use 24-hour format switch.",
                new Wait().until(() -> useTwentyFourSwitch != null)
        );

        boolean useTwentyFourWasEnabled = false;
        final UiObject thirteenHundredLabel = device.findObject(new UiSelector().text("13:00"));

        // Initialize 24-hour format option to disabled state.
        if (thirteenHundredLabel.exists()) {
            useTwentyFourWasEnabled = true;
            assert useTwentyFourSwitch != null;
            useTwentyFourSwitch.click();
        }
        assertTrue("Failed to find Use 24-hour format label.",
                new Wait().until(() -> device.findObject(
                        new UiSelector().text("Use 24-hour format")).exists())
        );
        assertTrue("Failed to find 1:00 PM label.",
                new Wait().until(() -> device.findObject(new UiSelector().text("1:00 PM")).exists())
        );
        // Enable 24-hour format.
        assert useTwentyFourSwitch != null;
        useTwentyFourSwitch.click();
        assertTrue("Failed to find 13:00 label.",
                new Wait().until(thirteenHundredLabel::exists)
        );

        // Clean up by disabling 24-hour format option.
        if (!useTwentyFourWasEnabled) {
            useTwentyFourSwitch.click();
        }
    }

    /**
     * Verify that activating and deactivating Device Administrators setting works.
     * <p>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p>
     * TR ID: C144630613
     * <p>
     *   <pre>
     *   Test Steps:
     *   1. Start an emulator AVD.
     *   2. Goto Settings —> Security —> Device Administration.
     *   3. Select Sample Device Admin.
     *   4. Goto to setting and deactivate policy.
     *   Verify:
     *   1. (Verify #1) that the "Sample Device Admin" policy is deactivated.
     *   2. (Verify #2) that the "Sample Device Admin" policy is activated.
     *   3. (Verify #3) that the "Sample Device Admin" policy is deactivated.
     *   </pre>
     */
    @Test
    @TestInfo(id = "T144630613")
    public void activateDeactivatePolicy() throws Exception {
        boolean isAPIDemoInstalled = PackageInstallationUtil.isPackageInstalled(instrumentation,
                "com.example.android.apis");

        if (isAPIDemoInstalled) {
            SettingsUtil.launchDeviceAdminApps(instrumentation, "Security", "Device administrators");

            if (SettingsUtil.checkStatusOfPolicy(device, instrumentation, "android.widget.CheckBox", Res.ANDROID_LIST_RES)) {
                SettingsUtil.deactivate(instrumentation, "Sample Device Admin", "Security", "Device administrators");
            }
            assertFalse(SettingsUtil.checkStatusOfPolicy(device, instrumentation, "android.widget.CheckBox", Res.ANDROID_LIST_RES));

            // Activate "Sample Device Admin" policy
            SettingsUtil.activate(instrumentation, "Sample Device Admin", "Security", "Device administrators");
            assertTrue(SettingsUtil.checkStatusOfPolicy(device, instrumentation, "android.widget.CheckBox", Res.ANDROID_LIST_RES));

            // Deactivate "Sample Device Admin" policy
            SettingsUtil.deactivate(instrumentation, "Sample Device Admin", "Security", "Device administrators");
            assertFalse(SettingsUtil.checkStatusOfPolicy(device, instrumentation, "android.widget.CheckBox", Res.ANDROID_LIST_RES));
        } else {
            Log.w(TAG,"activateDeactivatePolicy: required APK is missing");
        }
    }

    /**
     * Verify test Camera App is disabled in emulator when disabled in Device Admin.
     * <p>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p>
     * TT ID: 4db4a825-b584-4c68-a04d-c6a933b14e24
     * <p>
     *   <pre>
     *   Test Steps:
     *   1. Start an emulator AVD.
     *   2. Goto Settings —> Security —> Device Administration
     *   3. Select Sample Device Admin.
     *   4. Goto app API Demos —> App —> Device Admin —> General
     *   5. Select Enable All Device Cameras.
     *   6. Repeat steps 2-4.
     *   7. Select Disable All Device Cameras.
     *   8. Goto Home screen —> Click on Camera Application
     *   9. Repeat steps 2-4.
     *   10. Select Enable All Device Cameras.
     *   Verify:
     *   1. (Verify #1) camera app is enabled
     *   2. (Verify #2) camera app is disabled
     *   2. (Verify #2) camera app is enabled
     *   </pre>
     */
    @Test
    @TestInfo(id = "4db4a825-b584-4c68-a04d-c6a933b14e24")
    public void testCameraAppDisabled() throws Exception {
        SettingsUtil.enableSampleDeviceAdmin_v1(instrumentation, device);
        if (SettingsUtil.verifyCameraAppDisabled(instrumentation)) {
            SettingsUtil.setCameraEnabled(true, instrumentation, device);
        }
        Assert.assertFalse(SettingsUtil.verifyCameraAppDisabled(instrumentation));

        SettingsUtil.setCameraEnabled(false, instrumentation, device);
        Assert.assertTrue(SettingsUtil.verifyCameraAppDisabled(instrumentation));
        SettingsUtil.setCameraEnabled(true, instrumentation, device);
        Assert.assertFalse(SettingsUtil.verifyCameraAppDisabled(instrumentation));
    }
}