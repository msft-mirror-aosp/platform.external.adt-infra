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

package com.android.devtools.systemimage.uitest.smoke.api26;

import android.app.Instrumentation;
import android.support.test.runner.AndroidJUnit4;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiObject2;
import android.support.test.uiautomator.UiObjectNotFoundException;
import android.support.test.uiautomator.UiScrollable;
import android.support.test.uiautomator.UiSelector;
import android.util.Log;
import android.widget.LinearLayout;
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
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.Timeout;
import org.junit.runner.RunWith;

import static org.junit.Assert.assertEquals;
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

        AppLauncher.launchPath(instrumentation, true,
                "Settings", "Security & Location", "Location");

        boolean isLocationDisabled = new Wait().until(() ->
                device.findObject(new UiSelector().textMatches("(?i)yes")).exists());

        if (isLocationDisabled) {
            device.findObject(new UiSelector().textMatches("(?i)yes")).clickAndWaitForNewWindow();
            device.findObject(new UiSelector().textMatches("(?i)location")).clickAndWaitForNewWindow();
        }
        assertTrue("Failed to find Location title.",
                new Wait().until(() -> device.findObject(new UiSelector().text("Location")).exists() &&
                        device.findObject(new UiSelector().text("Recent location requests"))
                                .exists()));
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
     *
     */
    @Test
    @TestInfo(id = "4f09278e-d1e3-47bb-a22c-70f236ac9a48")
    public void testPhonePermissions() throws Exception {
        final String app = "Phone";

        SettingsUtil.setAppPermissions_v1(instrumentation, app, app,
                false, "DENY ANYWAY", "Apps & notifications");
        device.pressHome();

        AppLauncher.launch(instrumentation, app);

        UiObject dialer = device.findObject(
                new UiSelector().resourceIdMatches("com.google.android.dialer:id/digits"));
        if (dialer.waitForExists(5L)) {
            device.findObject(new UiSelector().resourceIdMatches("com.google.android.dialer:id/digits")).
                    clickAndWaitForNewWindow();
            device.findObject(new UiSelector().resourceIdMatches(Res.DIALER_DIGITS_RES)).setText("555");
            device.findObject(new UiSelector().resourceIdMatches(Res.DIALER_PAD_RES)).click();
        }
        assertTrue("Did not prompt for lack of Phone permission.",
                new Wait().until(() -> device.findObject(new UiSelector().text(
                        "This application cannot make outgoing calls without the Phone permission.")).
                        exists())
        );

        SettingsUtil.setAppPermissions_v1(instrumentation, app, app,
                true, "DENY ANYWAY", "Apps & notifications");
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

        SettingsUtil.setAppPermissions_v1(instrumentation, appType, appName, false, "DENY ANYWAY", "Apps");
        device.pressHome();
        UiObject mapsApp = device.findObject(new UiSelector().text(appName));
        assertTrue("Failed to find Maps application", new Wait(5L)
                .until(mapsApp::exists));
        mapsApp.clickAndWaitForNewWindow();
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
        device.findObject(new UiSelector().description("Move to your location"))
                .clickAndWaitForNewWindow();
        assertTrue("Did not prompt for lack of Maps permission.",
                new Wait().until(() -> device.findObject(new UiSelector()
                        .text("Allow Maps to access this device's location?")).exists())
        );

        SettingsUtil.setAppPermissions_v1(instrumentation, appType, appName, true, "DENY ANYWAY", "Apps");
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
        AppLauncher.launchPath(instrumentation, true, "Settings", "Apps & notifications");
        device.findObject(new UiSelector().textContains("App permissions")).clickAndWaitForNewWindow();
        assertTrue(SettingsUtil.getAppPermissions_v3("Calendar")
                && SettingsUtil.getAppPermissions_v3("Camera")
                && SettingsUtil.getAppPermissions_v3("Phone"));
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
            assertTrue("Failed to enable Developer options.",
                    DeveloperOptionsManager.isDeveloperOptionsEnabled_v1(testFramework));
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
        AppLauncher.launchPath(instrumentation, true, "Settings", "System", "Date & time");
        final UiObject2 widget = SettingsUtil.navigateToDateTimeSwitch("Automatic date & time", instrumentation, Res.NETWORK_SWITCHES_RECYCLER_VIEW_RES);

        // Test requires "Automatic date & time" widget to start in the enabled state.
        assert widget != null;
        if (!widget.isChecked()) {
            widget.click();
        }
        assertTrue("Failed to disable set date.",
                new Wait().until(() -> !device.findObject(new UiSelector().text("Set date")).isEnabled())
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
                new UiSelector().resourceId(Res.ANDROID_DATE_PICKER_HEADER_RES)).exists());
        device.findObject(new UiSelector().textContains("CANCEL")).click();
        device.findObject(new UiSelector().text("Set time")).click();
        assertTrue(device.findObject(
                new UiSelector().resourceId(Res.ANDROID_TIME_HEADER_RES)).exists());

        device.findObject(new UiSelector().textContains("CANCEL")).click();
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
        AppLauncher.launchPath(instrumentation, true, "Settings", "System", "Date & time");

        final UiObject2 widget = SettingsUtil.navigateToDateTimeSwitch("Automatic time zone", instrumentation, Res.NETWORK_SWITCHES_RECYCLER_VIEW_RES);

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
        AppLauncher.launchPath(instrumentation, true, "Settings", "System", "Date & time");
        final UiObject2 useTwentyFourSwitch = SettingsUtil.navigateToDateTimeSwitch("Use 24-hour format", instrumentation, Res.NETWORK_SWITCHES_RECYCLER_VIEW_RES);

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
            AppLauncher.launchPath(instrumentation, true, "Settings", "Security & Location", "Device admin apps");

            if (SettingsUtil.checkStatusOfPolicy(device, instrumentation, "android.widget.CheckBox", Res.ANDROID_LIST_RES)) {
                SettingsUtil.deactivate(instrumentation, "Sample Device Admin", "Security & Location", "Device admin apps");
            }
            assertFalse(SettingsUtil.checkStatusOfPolicy(device, instrumentation, "android.widget.CheckBox", Res.ANDROID_LIST_RES));

            // Activate "Sample Device Admin" policy
            SettingsUtil.activate(instrumentation, "Sample Device Admin", "Security & Location", "Device admin apps");
            assertTrue(SettingsUtil.checkStatusOfPolicy(device, instrumentation, "android.widget.CheckBox", Res.ANDROID_LIST_RES));

            // Deactivate "Sample Device Admin" policy
            SettingsUtil.deactivate(instrumentation, "Sample Device Admin", "Security & Location", "Device admin apps");
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
        SettingsUtil.enableSampleDeviceAdmin_v2(instrumentation, device);
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
    @Test
    @TestInfo(id = "d49facce-9be7-47e0-afde-2052d3c57a25")
    public void modifyAndResetAppPermissions() throws Exception {
        String appName = "Maps";
        String contactsText = "Contacts";
        String locationText = "Location";
        String phoneText = "Phone";
        String storageText = "Storage";

        // Variables to store the state of permissions.
        boolean contactsSwitchState;
        boolean locationSwitchState;
        boolean phoneSwitchState;
        boolean storageSwitchState;

        AppLauncher.launchPath(instrumentation, true,
                "Settings","Apps & notifications", "App info");
        AppManager.openSystemAppList_v2(instrumentation);

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

        UiScrollable permissionList = new UiScrollable(new UiSelector().resourceIdMatches(Res.ANDROID_LIST_RES));

        //Get switch widgets UiObjects.
        UiObject contactSwitch =
                SettingsUtil.findObjectByRelative(permissionList,contactsText,LinearLayout.class.getName());
        UiObject locationSwitch =
                SettingsUtil.findObjectByRelative(permissionList,locationText,LinearLayout.class.getName());
        UiObject phoneSwitch =
                SettingsUtil.findObjectByRelative(permissionList,phoneText,LinearLayout.class.getName());
        UiObject storageSwitch =
                SettingsUtil.findObjectByRelative(permissionList,storageText,LinearLayout.class.getName());

        //Store current permissions state of switch widgets.
        contactsSwitchState = contactSwitch.isChecked();
        locationSwitchState = locationSwitch.isChecked();
        phoneSwitchState = phoneSwitch.isChecked();
        storageSwitchState = storageSwitch.isChecked();

        //Modify application permission.
        contactSwitch.click();
        phoneSwitch.click();
        storageSwitch.click();
        locationSwitch.clickAndWaitForNewWindow();

        device.findObject(new UiSelector().textStartsWith("Deny")).clickAndWaitForNewWindow();

        //Go back two times to go to system apps page to reset permissions.
        device.pressBack();
        device.pressBack();

        //Reset app preferences from overflow menu.
        device.pressMenu();
        device.findObject(
                new UiSelector().textContains("Reset app preferences")).clickAndWaitForNewWindow();
        device.findObject(new UiSelector().textContains("RESET APPS")).clickAndWaitForNewWindow();

        //Open Maps info.
        itemList.scrollIntoView(new UiSelector().text(appName));
        itemList.getChildByText(new UiSelector().className(TextView.class.getName()), appName)
                .clickAndWaitForNewWindow();

        //Open permission and verify Contacts,Location,Phone and Storage.
        //Verify that all the permission for the app are reset.
        appInfoList.getChildByText(new UiSelector().
                className(TextView.class.getName()),"Permissions").clickAndWaitForNewWindow();

        assertEquals(contactsSwitchState,
                SettingsUtil.findObjectByRelative(
                        permissionList,"Contacts",LinearLayout.class.getName()).isChecked());
        assertEquals(locationSwitchState,
                SettingsUtil.findObjectByRelative(
                        permissionList,"Location",LinearLayout.class.getName()).isChecked());
        assertEquals(phoneSwitchState,
                SettingsUtil.findObjectByRelative(
                        permissionList,"Phone",LinearLayout.class.getName()).isChecked());
        assertEquals(storageSwitchState,
                SettingsUtil.findObjectByRelative(
                        permissionList,"Storage",LinearLayout.class.getName()).isChecked());
    }

    /**
     * To verify that revoking USB debugging can be invoked from Developer Options
     * <p>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p>
     *   <pre>
     *   Test Steps:
     *   1. Launch an emulator avd.
     *   2. If Developer Options are disabled, enable Developer Options.
     *   3. Launch Developers Options.
     *   4. Scroll to Revoke USB Debugging Authorizations and click.
     *   5. Detect that the Revoke USB Debugging message is presented.
     *   Verify:
     *   1. Developer Options have been enabled.
     *   2. 'Settings keeps stopping' error was not thrown.
     *   3. Revoke USB Debugging option is available.
     *   </pre>
     */
    @Test
    public void revokeDebugAuth() throws Exception {
        if (!DeveloperOptionsManager.isDeveloperOptionsEnabled_v1(testFramework)) {
            DeveloperOptionsManager.enableDeveloperOptions_v1(testFramework);
        }

        Assert.assertTrue("Could not enable developer options",
                DeveloperOptionsManager.isDeveloperOptionsEnabled_v1(testFramework));

        UiObject developerOptionsItem = UiDevice.getInstance(instrumentation).findObject(
                new UiSelector().text("Developer options"));
        if (developerOptionsItem.waitForExists(5L)) {
            developerOptionsItem.clickAndWaitForNewWindow();
        }
        UiScrollable itemList =
                new UiScrollable(
                        new UiSelector().resourceIdMatches(Res.SETTINGS_LIST_CONTAINER_RES)
                );
        itemList.setAsVerticalList();

        UiSelector revokeUSBOption = new UiSelector().text("Revoke USB debugging authorizations");
        itemList.scrollIntoView(revokeUSBOption);

        UiObject revokeUSBDebug = device.findObject(revokeUSBOption);

        if (revokeUSBDebug.waitForExists(5L)) {
            revokeUSBDebug.clickAndWaitForNewWindow();
        }

        UiObject androidErrorClose = device.findObject(
                new UiSelector().resourceId(Res.ANDROID_ERROR_CLOSE_RES));
        Assert.assertTrue("Settings Keeps Stopping error when revoking usb debugging",
                !androidErrorClose.waitForExists(5L));

        UiObject revokeText = device.findObject(
                new UiSelector().text("Revoke access to USB debugging from all computers you’ve previously authorized?"));
        UiObject cancelRevoke = device.findObject(
                new UiSelector().text("CANCEL").className("android.widget.Button"));
        Assert.assertTrue("Unable to revoke USB debugging authorizations",
                revokeText.waitForExists(5L) && cancelRevoke.waitForExists(5L));
        cancelRevoke.click();
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
        AppLauncher.launchPath(instrumentation, true, "Settings", "Connected devices");

        UiObject androidErrorClose = device.findObject(
                new UiSelector().resourceId(Res.ANDROID_ERROR_CLOSE_RES));
        Assert.assertTrue("Settings Keeps Stopping error when revoking usb debugging",
                !androidErrorClose.waitForExists(5L));

        UiObject actionBar = device.findObject(
                new UiSelector().resourceId(Res.SETTINGS_ACTION_BAR_RES).className("android.view.ViewGroup"));
        UiObject connectedDevices = device.findObject(
                new UiSelector().text("Connected devices").className("android.widget.TextView"));
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
    @Test
    public void filesDeleted() throws Exception {
        String[] testFileNames = {"test_text_01.txt", "test_text_02.txt", "test_text_03.txt"};

        for (String name : testFileNames) {
            AppLauncher.launchPath(instrumentation, true, "Settings", "Storage", "Internal shared storage", "Files");

            if (SettingsUtil.hasTestFile(instrumentation, name)) {
                SettingsUtil.deleteTestFile_v1(instrumentation, name);
            }
            Assert.assertFalse("Test file " + name + " already exists",
                    SettingsUtil.hasTestFile(instrumentation, name));

            SettingsUtil.copyTestFile(instrumentation, name);
            Assert.assertTrue("Test file " + name + " could not be copied",
                    SettingsUtil.hasTestFile(instrumentation, name));

            SettingsUtil.deleteTestFile_v1(instrumentation, name);
            Assert.assertFalse("Test file " + name + " could not be deleted",
                    SettingsUtil.hasTestFile(instrumentation, name));
        }
    }
}
