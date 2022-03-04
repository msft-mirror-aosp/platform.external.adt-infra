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

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import android.app.Instrumentation;
import android.support.test.runner.AndroidJUnit4;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiScrollable;
import android.support.test.uiautomator.UiSelector;
import android.util.Log;
import android.widget.TextView;

import com.android.devtools.systemimage.uitest.annotations.TestInfo;
import com.android.devtools.systemimage.uitest.common.Res;
import com.android.devtools.systemimage.uitest.framework.SystemImageTestFramework;
import com.android.devtools.systemimage.uitest.utils.ApiDemosInstaller;
import com.android.devtools.systemimage.uitest.utils.AppLauncher;
import com.android.devtools.systemimage.uitest.utils.AppManager;
import com.android.devtools.systemimage.uitest.utils.DeveloperOptionsManager;
import com.android.devtools.systemimage.uitest.utils.PackageInstallationUtil;
import com.android.devtools.systemimage.uitest.utils.SettingsUtil;
import com.android.devtools.systemimage.uitest.utils.Wait;

import org.junit.Assert;
import org.junit.Before;
import org.junit.Ignore;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.Timeout;
import org.junit.runner.RunWith;

/**
 * Test class for Android Settings page on Google API images.
 */
@RunWith(AndroidJUnit4.class)
public class SettingsTest {
    @Rule
    public final SystemImageTestFramework testFramework = new SystemImageTestFramework();

    private final Instrumentation instrumentation = testFramework.getInstrumentation();
    private final UiDevice device = UiDevice.getInstance(instrumentation);

    private final static String TAG = "SettingsTest";

    // Tests under this class takes up to 240 seconds depending on the performance of the bot the
    // tests run on.
    @Rule
    public Timeout globalTimeout = Timeout.seconds(360);

    @Before
    public void activateDeviceAdmin() throws Exception {
        ApiDemosInstaller.installApp("Security", "Device admin apps", false);
    }

    /**
     * Verifies Location page opens on Google API images.
     * <p>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p>
     * TT ID: 97d93bb7-63d2-4e89-9d18-0f232bbd51ab
     * <p>
     *   <pre>
     *   1. Start the emulator.
     *   2. Open Settings > Google > Location
     *   Verify:
     *   Location settings page opens.
     *   </pre>
     */
    @Test
    @TestInfo(id = "97d93bb7-63d2-4e89-9d18-0f232bbd51ab")
    public void testLocationSettingsPageOpen() throws Exception {
        if (!testFramework.isGoogleApiAndPlayImage() && !testFramework.isGoogleApiImage()) {
            return;
        }

        AppLauncher.launch(instrumentation, "Settings");
        UiScrollable itemList =
                new UiScrollable(
                        new UiSelector().resourceIdMatches(Res.SETTINGS_LIST_CONTAINER_RES)
                );
        itemList.setAsVerticalList();

        UiObject location =
                itemList.getChildByText(new UiSelector().className("android.widget.TextView"),
                        "Location");
        location.clickAndWaitForNewWindow();

        boolean recentAccessText = new Wait().until(
                () -> device.findObject(new UiSelector()
                        .text("Recent access")).exists());

        if (!recentAccessText) {
            device.findObject(new UiSelector().text("Use location")).clickAndWaitForNewWindow();
        }

        UiObject seeAll = device.findObject(new UiSelector()
                .text("See all"));

        if (new Wait().until(seeAll::exists)) {
            seeAll.clickAndWaitForNewWindow();
        }

        boolean recentAccessDesc = new Wait().until(
                () -> device.findObject(new UiSelector()
                        .description("Recent access")).exists());
        assertTrue("Failed to find Location title.", recentAccessDesc);
    }

    /**
     * Verifies that the phone cannot dial out if phone privileges have been disabled.
     * <p>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p>
     * TT ID: 4f09278e-d1e3-47bb-a22c-70f236ac9a48
     * <p>
     *   <pre>
     *  1. Start the emulator.
     *  2. Open Settings > Apps
     *  3. Click on the gear icon and select App permissions.
     *  4. Click on "Phone"
     *  5. Disable Phone permissions.
     *  6. Click on DENY button.
     *  7. Return to the main screen.
     *  8. Launch the phone app.
     *  9. Click on the dialer icon.
     *  10. Type in a number.
     *  11. Click on Call icon.
     *   Verify:
     *   Dialog stating "This application cannot make outgoing calls without the Phone permission."
     *   </pre>
     * <p>
     *
     */
    @Test
    @TestInfo(id = "4f09278e-d1e3-47bb-a22c-70f236ac9a48")
    @Ignore("Phone access cannot be revoked on API 30")
    public void testPhonePermissions() throws Exception {
        final String app = "Phone";

        SettingsUtil.setAppPermissions_v3(instrumentation, app, app, false,
                "Deny anyway", "Apps & notifications", "Permission manager");
        device.pressHome();

        AppLauncher.launch(instrumentation, app);

        device.findObject(new UiSelector().resourceIdMatches(Res.DIALER_PHONE_RES)).
                clickAndWaitForNewWindow();
        device.findObject(new UiSelector().resourceIdMatches(Res.DIALER_DIGITS_RES)).setText("555");
        device.findObject(new UiSelector().resourceIdMatches(Res.DIALER_PAD_RES)).click();

        assertTrue("Did not prompt for lack of Phone permission.",
                new Wait().until(() -> !(device.findObject(
                        new UiSelector().resourceIdMatches("com.google.android.dialer:id/incall_end_call")).
                        exists()))
        );

        SettingsUtil.setAppPermissions_v3(instrumentation, app, app, true,
                "Deny anyway", "Apps & notifications", "Permission manager");
        device.pressHome();
    }

    /**
     * Verifies that access must be confirmed if Maps location permissions are disabled.
     * <p>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p>
     * TT ID: 4f09278e-d1e3-47bb-a22c-70f236ac9a48
     * <p>
     *   <pre>
     *  1. Start the Emulator.
     *  2. Open Settings > Apps
     *  3. Click on the gear icon and select App permissions.
     *  4. Click on Location from App permissions screen.
     *  5. Disable Maps.
     *  6. Launch Maps app.
     *  7. Click on the locator icon.
     *   Verify:
     *   Dialog asking "Allow Maps to access this device's location?"
     *   </pre>
     * <p>
     */
    @Test
    @TestInfo(id = "4f09278e-d1e3-47bb-a22c-70f236ac9a48")
    public void testMapPermissions() throws Exception {
        final String appType = "Location";
        final String appName = "Maps";

        if (!testFramework.isGoogleApiAndPlayImage() && !testFramework.isGoogleApiImage()) {
            return;
        }

        SettingsUtil.setAppPermissions_v3(instrumentation, appType, appName, false,
                "Deny anyway", "Apps", "Permission manager");
        device.pressHome();

        AppLauncher.launch(instrumentation, appName);
        final UiObject acceptAndContinueButton;
        acceptAndContinueButton = device.findObject(new UiSelector().
                textMatches("(?i)accept\\s&\\scontinue"));
        if (acceptAndContinueButton.exists())
            acceptAndContinueButton.clickAndWaitForNewWindow();
        final UiObject skipButton;
        skipButton = device.findObject(new UiSelector().textMatches("(?i)skip"));
        if (skipButton.exists())
            skipButton.clickAndWaitForNewWindow();
        final UiObject gotItButton;
        gotItButton = device.findObject(new UiSelector().textMatches("(?i)got\\sit"));
        if (gotItButton.exists())
            gotItButton.clickAndWaitForNewWindow();
        device.findObject(new UiSelector().resourceId(Res.ANDROID_MY_LOCATION))
                .clickAndWaitForNewWindow();
        assertTrue("Did not prompt for lack of Maps permission.",
                new Wait().until(() -> device.findObject(new UiSelector()
                        .resourceId(Res.ANDROID_PERMISSIONS_MESSAGE)).exists())
        );

        SettingsUtil.setAppPermissions_v3(instrumentation, appName, appName, true,
                "Deny anyway", "Apps", "Permission manager");
        device.pressHome();
    }

    /**
     * Verifies the App permissions screen loads.
     * <p>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p>
     * TT ID: 4f09278e-d1e3-47bb-a22c-70f236ac9a48
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
     */
    @Test
    @TestInfo(id = "4f09278e-d1e3-47bb-a22c-70f236ac9a48")
    public void displayConfigureAppPermissions() throws Exception {

        assertTrue(SettingsUtil.getAppPermissions_v2(instrumentation, "Calendar", "Apps", "Permission manager").exists()
                && SettingsUtil.getAppPermissions_v2(instrumentation, "Camera", "Apps", "Permission manager").exists()
                && SettingsUtil.getAppPermissions_v2(instrumentation, "Phone", "Apps", "Permission manager").exists());
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
        if (!DeveloperOptionsManager.isDeveloperOptionsEnabled_v2(testFramework)) {
            DeveloperOptionsManager.enableDeveloperOptions_v3(testFramework);
            assertTrue("Failed to enable Developer options.",
                    DeveloperOptionsManager.isDeveloperOptionsEnabled_v2(testFramework));
        }
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
            SettingsUtil.openItem(instrumentation, "System");
            device.findObject(new UiSelector().text("Date & time"))
                    .clickAndWaitForNewWindow();
        } catch (Exception e) {
            Log.e(TAG, e.getMessage());
        }

        final UiObject timeButton = device.findObject(new UiSelector().text("Set time automatically"));

        // Test requires "Automatic date & time" widget to start in the enabled state.
        if (device.findObject(new UiSelector().text("Date")).isEnabled()) {
            timeButton.click();
        }
        assertTrue("Failed to disable set date.",
                new Wait().until(() -> !device.findObject(new UiSelector().text("Date")).isEnabled())
        );
        assertTrue("Failed to disable set time.",
                new Wait().until(() -> !device.findObject(new UiSelector().text("Time")).isEnabled())
        );
        timeButton.click();
        assertTrue("Failed to enable set date.",
                new Wait().until(() -> device.findObject(new UiSelector().text("Date")).isEnabled())
        );
        assertTrue("Failed to enable set time.",
                new Wait().until(() -> device.findObject(new UiSelector().text("Time")).isEnabled())
        );
        device.findObject(new UiSelector().text("Date")).clickAndWaitForNewWindow();

        assertTrue(device.findObject(
                new UiSelector().resourceId(Res.ANDROID_DATE_PICKER_HEADER_RES)).exists());
        device.findObject(new UiSelector().textContains("Cancel")).click();
        device.findObject(new UiSelector().text("Time")).click();
        assertTrue(device.findObject(
                new UiSelector().resourceId(Res.ANDROID_TIME_HEADER_RES)).exists());

        device.findObject(new UiSelector().textContains("Cancel")).click();
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
            SettingsUtil.openItem(instrumentation, "System");
            device.findObject(new UiSelector().text("Date & time"))
                    .clickAndWaitForNewWindow();
        } catch (Exception e) {
            Log.e(TAG, e.getMessage());
        }

        final UiObject autoTimeZoneButton = device.findObject(new UiSelector().text("Set time zone automatically"));
        final UiObject timeZoneButton = device.findObject(new UiSelector().textContains("GMT"));

        // Test requires "Automatic date & time" widget to start in the enabled state.
        if (timeZoneButton.isEnabled()) {
            autoTimeZoneButton.click();
        }
        assertTrue("Failed to disable select time zone",
                new Wait().until(() -> !timeZoneButton.isEnabled())
        );
        // Disable automatic time zone option.
        autoTimeZoneButton.click();
        assertTrue("Failed to enable select time zone",
                new Wait().until(timeZoneButton::isEnabled)
        );
        timeZoneButton.clickAndWaitForNewWindow();

        assertTrue("Failed to load Select time zone screen.",
                new Wait().until(() -> device.findObject(
                        new UiSelector().description("Select time zone")).exists())
        );

        UiObject timeZoneLabel = device.findObject(new UiSelector().textMatches("(Time zone|Select UTC offset)").
                resourceId(Res.ANDROID_TITLE_RES).packageName("com.android.settings"));
        if (timeZoneLabel.waitForExists(3L)) {
            timeZoneLabel.clickAndWaitForNewWindow();
        }

        String timezoneOffset = "GMT-08:00";
        assertTrue("Target time zone label not found",
                device.findObject(new UiSelector().textContains(timezoneOffset)).waitForExists(3L));
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
    @Ignore("24 hour format option has been removed from Settings.")
    @Test
    @TestInfo(id = "f83bf063-2a8c-4d1b-808b-20fd76933135")
    public void enableTwentyFourHourFormat() throws Exception {
        try {
            SettingsUtil.openItem(instrumentation, "System");
            device.findObject(new UiSelector().text("Date & time"))
                    .clickAndWaitForNewWindow();
        } catch (Exception e) {
            Log.e(TAG, e.getMessage());
        }

        boolean autoTwentyFourWasEnabled = false;
        boolean useTwentyFourWasEnabled = false;
        UiObject useTwentyFourLabel = device.findObject(new UiSelector().text("Use 24-hour format"));
        UiObject autoTwentyFourLabel = device.findObject(new UiSelector().text("Use locale default"));
        final UiObject thirteenHundredLabel = device.findObject(new UiSelector().text("13:00"));

        // Initialize automatic format option to disabled state.
        if (autoTwentyFourLabel.waitForExists(3L) && !useTwentyFourLabel.isEnabled()) {
            autoTwentyFourWasEnabled = true;
            autoTwentyFourLabel.click();
        }

        // Initialize 24-hour format option to disabled state.
        if (thirteenHundredLabel.exists()) {
            useTwentyFourWasEnabled = true;
            useTwentyFourLabel.click();
        }
        assertTrue("Failed to find Use 24-hour format label.",
                new Wait().until(() -> device.findObject(
                        new UiSelector().text("Use 24-hour format")).exists())
        );
        assertTrue("Failed to find 1:00 PM label.",
                new Wait().until(() -> device.findObject(new UiSelector().text("1:00 PM")).exists())
        );
        // Enable 24-hour format.
        useTwentyFourLabel.click();
        assertTrue("Failed to find 13:00 label.",
                new Wait().until(thirteenHundredLabel::exists)
        );

        if (autoTwentyFourWasEnabled && useTwentyFourLabel.isEnabled()) {
            autoTwentyFourLabel.click();
        }

        // Clean up by disabling 24-hour format option.
        if (!useTwentyFourWasEnabled) {
            useTwentyFourLabel.click();
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
            SettingsUtil.launchDeviceAdminApps(instrumentation, "Security", "Device admin apps");

            if (SettingsUtil.checkStatusOfPolicy(device, instrumentation, "android.widget.Switch", Res.ANDROID_SETTING_LIST_RES)) {
                SettingsUtil.deactivate(instrumentation, "Sample Device Admin", "Security", "Device admin apps");
            }
            assertFalse(SettingsUtil.checkStatusOfPolicy(device, instrumentation, "android.widget.Switch", Res.ANDROID_SETTING_LIST_RES));

            // Activate "Sample Device Admin" policy
            SettingsUtil.activate(instrumentation, "Sample Device Admin", "Security", "Device admin apps");
            assertTrue(SettingsUtil.checkStatusOfPolicy(device, instrumentation, "android.widget.Switch", Res.ANDROID_SETTING_LIST_RES));

            // Deactivate "Sample Device Admin" policy
            SettingsUtil.deactivate(instrumentation, "Sample Device Admin", "Security", "Device admin apps");
            assertFalse(SettingsUtil.checkStatusOfPolicy(device, instrumentation, "android.widget.Switch", Res.ANDROID_SETTING_LIST_RES));
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
     *   3. (Verify #3) camera app is enabled
     *   </pre>
     */
    @Test
    @TestInfo(id = "4db4a825-b584-4c68-a04d-c6a933b14e24")
    @Ignore("Disabling camera permissions does not deactivate camera app on API 30")
    public void testCameraAppDisabled() throws Exception {
        SettingsUtil.enableSampleDeviceAdmin_v2(instrumentation, device, "Security");

        if (SettingsUtil.verifyCameraAppDisabled(instrumentation)) {
            SettingsUtil.setCameraEnabled(true, instrumentation, device);
        }

        Assert.assertFalse(SettingsUtil.verifyCameraAppDisabled(instrumentation));

        SettingsUtil.setCameraEnabled(false, instrumentation, device);
        Assert.assertTrue(SettingsUtil.verifyCameraAppDisabled(instrumentation));

        SettingsUtil.setCameraEnabled(true, instrumentation, device);
        Assert.assertFalse(SettingsUtil.verifyCameraAppDisabled(instrumentation));
    }

    /**
     * To verify that "Reset app preferences" restores permission restrictions.
     * <p>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p>
     * TT ID: d49facce-9be7-47e0-afde-2052d3c57a25
     * <p>
     *   <pre>
     *   Test Steps:
     *   1. Launch an emulator avd with wipe data.
     *   2. Open Settings > Apps.
     *   3. Open the menu (3 vertical dots) and tap on "Show System".
     *   4. Tap on any app, say Maps and select "Permissions".
     *   5. Enable all available permissions for the app.
     *   6. Press back button.
     *   7. Open the menu > Reset app preferences > Reset apps.
     *   Verify:
     *   1. App settings for Maps are reset to default (Verify that Permissions and notification
     *   settings for Maps are cleared).
     *   </pre>
     */
    @Ignore("Test is canceled on crash during app permission reset.")
    @Test
    @TestInfo(id = "d49facce-9be7-47e0-afde-2052d3c57a25")
    public void modifyAndResetAppPermissions() throws Exception {
        String appName = "Maps";
        String contactsText = "Contacts";
        String locationText = "Location";
        String microphoneText = "Microphone";
        String storageText = "Files and media";

        // Variables to store the state of permissions.
        boolean contactsSwitchState;
        boolean locationSwitchState;
        boolean microphoneSwitchState;
        boolean storageSwitchState;

        AppManager.openAppList_v3(instrumentation);

        // Find and click "Maps" in apps list.
        UiScrollable itemList =
                new UiScrollable(
                        new UiSelector().resourceIdMatches(Res.SETTINGS_LIST_CONTAINER_RES)
                );
        itemList.setAsVerticalList();

        itemList.scrollIntoView(new UiSelector().text(appName));
        itemList.getChildByText(new UiSelector().className(TextView.class.getName()), appName)
                .clickAndWaitForNewWindow();

        //Get application info list.
        UiScrollable appInfoList =
                new UiScrollable(
                        new UiSelector().resourceIdMatches(Res.SETTINGS_LIST_CONTAINER_RES)
                );

        //Choose permissions to edit them.
        appInfoList.getChildByText(new UiSelector().
                className(TextView.class.getName()),"Permissions").clickAndWaitForNewWindow();

        UiScrollable permissionList = new UiScrollable(new UiSelector().resourceId(Res.PERMISSION_RECYCLER_VIEW));

        //Get switch widgets UiObjects and
        //Store current permissions state of switch widgets.
        UiObject contactSwitch =
                permissionList.getChildByText(new UiSelector().className("android.widget.TextView"), contactsText);
        contactSwitch.click();
        UiObject contactsAllowSwitch = device.findObject(new UiSelector().resourceIdMatches(Res.ALLOW_PERMISSION_BUTTON));
        contactsSwitchState = contactsAllowSwitch.isChecked();
        contactsAllowSwitch.clickAndWaitForNewWindow(1000);
        assertEquals(contactsSwitchState, !contactsAllowSwitch.isChecked());
        device.pressBack();

        UiObject locationSwitch =
                permissionList.getChildByText(new UiSelector().className("android.widget.TextView"), locationText);
        locationSwitch.click();
        UiObject locationAllowSwitch = device.findObject(new UiSelector().resourceIdMatches(Res.ALLOW_PERMISSION_BUTTON));
        locationSwitchState = locationAllowSwitch.isChecked();
        locationAllowSwitch.clickAndWaitForNewWindow(1000);
        assertEquals(locationSwitchState, !locationAllowSwitch.isChecked());
        device.pressBack();

        UiObject microphoneSwitch =
                permissionList.getChildByText(new UiSelector().className("android.widget.TextView"), microphoneText);
        microphoneSwitch.clickAndWaitForNewWindow(1000);
        UiObject microphoneAllowSwitch = device.findObject(new UiSelector().resourceId(Res.ALLOW_FOREGROUND_ONLY_PERMISSION_BUTTON));
        microphoneSwitchState = microphoneAllowSwitch.isChecked();
        microphoneAllowSwitch.clickAndWaitForNewWindow(1000);
        assertEquals(microphoneSwitchState, !microphoneAllowSwitch.isChecked());
        device.pressBack();

        UiObject storageSwitch =
                permissionList.getChildByText(new UiSelector().className("android.widget.TextView"), storageText);
        storageSwitch.click();
        UiObject storageAllowSwitch = device.findObject(new UiSelector().resourceId(Res.ALLOW_FOREGROUND_ONLY_PERMISSION_BUTTON));
        storageSwitchState = storageAllowSwitch.isChecked();
        storageAllowSwitch.clickAndWaitForNewWindow(1000);
        assertEquals(storageSwitchState, !storageAllowSwitch.isChecked());
        device.pressBack();


        //Go back two times to go to system apps page to reset permissions.
        device.pressBack();
        device.pressBack();

        //Reset app preferences from overflow menu.
        device.pressMenu();
        device.findObject(
                new UiSelector().textContains("Reset app preferences")).clickAndWaitForNewWindow();
        device.findObject(new UiSelector().textContains("Reset Apps")).clickAndWaitForNewWindow();

        //Open Maps info.
        itemList.scrollIntoView(new UiSelector().text(appName));
        itemList.getChildByText(new UiSelector().className(TextView.class.getName()), appName)
                .clickAndWaitForNewWindow();

        //Open permission and verify Contacts,Location,Phone and Storage.
        //Verify that all the permission for the app are reset.
        appInfoList.getChildByText(new UiSelector().
                className(TextView.class.getName()),"Permissions").clickAndWaitForNewWindow();

        permissionList = new UiScrollable(new UiSelector().resourceId(Res.PERMISSION_RECYCLER_VIEW));

        contactSwitch = permissionList.getChildByText(new UiSelector().className("android.widget.TextView"), contactsText);
        contactSwitch.clickAndWaitForNewWindow(1000);
        contactsAllowSwitch = device.findObject(new UiSelector().resourceIdMatches(Res.ALLOW_PERMISSION_BUTTON));
        assertEquals(contactsSwitchState, contactsAllowSwitch.isChecked());
        device.pressBack();

        locationSwitch = permissionList.getChildByText(new UiSelector().className("android.widget.TextView"), locationText);
        locationSwitch.clickAndWaitForNewWindow(1000);
        locationAllowSwitch = device.findObject(new UiSelector().resourceIdMatches(Res.ALLOW_PERMISSION_BUTTON));
        assertEquals(locationSwitchState, locationAllowSwitch.isChecked());
        device.pressBack();

        microphoneSwitch = permissionList.getChildByText(new UiSelector().className("android.widget.TextView"), microphoneText);
        microphoneSwitch.clickAndWaitForNewWindow(1000);
        microphoneAllowSwitch = device.findObject(new UiSelector().resourceId(Res.ALLOW_FOREGROUND_ONLY_PERMISSION_BUTTON));
        assertEquals(microphoneSwitchState, microphoneAllowSwitch.isChecked());
        device.pressBack();

        storageSwitch = permissionList.getChildByText(new UiSelector().className("android.widget.TextView"), storageText);
        storageSwitch.clickAndWaitForNewWindow(1000);
        storageAllowSwitch = device.findObject(new UiSelector().resourceId(Res.ALLOW_FOREGROUND_ONLY_PERMISSION_BUTTON));
        assertEquals(storageSwitchState, storageAllowSwitch.isChecked());
        device.pressBack();
    }

    /**
     * To verify that revoking USB debugging can be invoked from Developer Options.
     * <p>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p>
     *   <pre>
     *   Test Steps:
     *   1. Launch an emulator avd.
     *   2. If Developer Options are disabled, enable Developer Options.
     *   3. Launch Developers Options.
     *   4. Scroll to USB Debugging switch.
     *   Verify:
     *   1. Developer Options have been enabled.
     *   2. USB Debugging option is available.
     *   </pre>
     */
    @Test
    public void revokeDebugAuth() throws Exception {
        if (!DeveloperOptionsManager.isDeveloperOptionsEnabled_v2(testFramework)) {
            DeveloperOptionsManager.enableDeveloperOptions_v3(testFramework);
        }

        Assert.assertTrue("Could not enable developer options",
                DeveloperOptionsManager.isDeveloperOptionsEnabled_v2(testFramework));

        AppLauncher.launchPath(instrumentation, true, "Settings", "System", "Developer options");

        UiScrollable itemList =
                new UiScrollable(
                        new UiSelector().resourceIdMatches(Res.SETTINGS_LIST_CONTAINER_RES)
                );
        itemList.setAsVerticalList();

        UiSelector usbDebuggingSelector = new UiSelector().text("USB debugging");
        itemList.scrollIntoView(usbDebuggingSelector);

        UiObject usbDebugging = device.findObject(usbDebuggingSelector);

        assertTrue("USB debugging controls not found", usbDebugging.waitForExists(5L));
    }

    /**
     * To verify that a list of connected devices can be viewed.
     * <p>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p>
     *   <pre>
     *   Test Steps:
     *   1. Launch an emulator avd.
     *   2. Click on Settings.
     *   3. Click on Connected Devices.
     *   Verify:
     *   1. 'Settings keeps stopping' error was not thrown.
     *   2. List of connected devices is displayed.
     *   </pre>
     */
    @Test
    public void listConnectedDevices() throws Exception {
        try {
            SettingsUtil.openItem(instrumentation, "Connected devices");
        } catch (Exception e) {
            Log.e(TAG, e.getMessage());
        }

        UiObject androidErrorClose = device.findObject(
                new UiSelector().resourceId(Res.ANDROID_ERROR_CLOSE_RES));
        assertFalse("Settings Keeps Stopping error when revoking usb debugging", androidErrorClose.waitForExists(5L));

        UiObject actionBar = device.findObject(
                new UiSelector().resourceId(Res.SETTINGS_ACTION_BAR_RES).className("android.view.ViewGroup"));
        UiObject connectedDevices = device.findObject(
                new UiSelector().text("Previously connected devices").className("android.widget.TextView"));
        Assert.assertTrue("Connected devices were not listed",
                actionBar.waitForExists(5L) && connectedDevices.waitForExists(5L));
    }

    /**
     * To verify that files can be copied to and deleted from the device.
     * <p>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p>
     *   <pre>
     *   Test Steps:
     *   1. Launch an emulator avd.
     *   2. Click on Settings.
     *   3. Click on Storage > Internal shared storage > Files.
     *   4. Remove test file from internal storage folder if it already exists.
     *   5. Copy test file into internal storage folder.
     *   6. Delete copied test file from internal storage folder.
     *   7. Repeat for additional test files.
     *   Verify:
     *   1. Test file does not already exist in the Download folder.
     *   2. Test file is copied into the Download folder.
     *   3. Test file is deleted from the Download folder.
     *   </pre>
     */
    @Ignore("Cannot access external storage without a runtime permissions implementation")
    @Test
    public void filesDeleted() throws Exception {
        String[] testFileNames = {"test_text_01.txt", "test_text_02.txt", "test_text_03.txt"};

        for (String name : testFileNames) {
            AppLauncher.launchPath(instrumentation, true, "Settings", "Storage", "Internal shared storage", "Files");

            if (SettingsUtil.hasTestFile(instrumentation, name)) {
                SettingsUtil.deleteTestFile_v2(instrumentation, name, Res.OPTION_MENU_SEARCH_RES);
            }
            Assert.assertFalse("Test file " + name + " already exists",
                    SettingsUtil.hasTestFile(instrumentation, name));

            SettingsUtil.copyTestFile(instrumentation, name);
            Assert.assertTrue("Test file " + name + " could not be copied",
                    SettingsUtil.hasTestFile(instrumentation, name));

            SettingsUtil.deleteTestFile_v2(instrumentation, name, Res.OPTION_MENU_SEARCH_RES);
            Assert.assertFalse("Test file " + name + " could not be deleted",
                    SettingsUtil.hasTestFile(instrumentation, name));
        }
    }
}