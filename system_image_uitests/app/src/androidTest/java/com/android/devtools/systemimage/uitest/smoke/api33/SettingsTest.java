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

package com.android.devtools.systemimage.uitest.smoke.api33;

import android.app.Instrumentation;
import androidx.test.runner.AndroidJUnit4;
import androidx.test.uiautomator.UiDevice;
import androidx.test.uiautomator.UiObject;
import androidx.test.uiautomator.UiScrollable;
import androidx.test.uiautomator.UiSelector;
import android.util.Log;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;
import android.widget.FrameLayout;
import com.android.devtools.systemimage.uitest.annotations.TestInfo;
import com.android.devtools.systemimage.uitest.common.Res;
import com.android.devtools.systemimage.uitest.framework.SystemImageTestFramework;
import com.android.devtools.systemimage.uitest.utils.ApiDemosInstaller;
import com.android.devtools.systemimage.uitest.utils.AppLauncher;
import com.android.devtools.systemimage.uitest.utils.AppManager;
import com.android.devtools.systemimage.uitest.utils.DeveloperOptionsManager;
import com.android.devtools.systemimage.uitest.utils.GoogleAppUtil;
import com.android.devtools.systemimage.uitest.utils.SettingsUtil;
import com.android.devtools.systemimage.uitest.utils.Wait;

import org.junit.Assert;
import org.junit.Ignore;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.Timeout;
import org.junit.runner.RunWith;

import java.util.Objects;

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

    private final Instrumentation instrumentation = testFramework.getInstrumentation();
    private final UiDevice device = UiDevice.getInstance(instrumentation);

    private final static String TAG = "SettingsTest";

    // Tests under this class takes up to 1000 seconds depending on the performance of the bot the
    // tests run on.
    @Rule
    public Timeout globalTimeout = Timeout.seconds(1000);

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
        UiSelector region = new UiSelector().resourceIdMatches(Res.SETTINGS_LIST_CONTAINER_RES);
        UiSelector target = new UiSelector()
                .className("android.widget.TextView")
                .text("Location");

        assertTrue("Location not found in Settings List",
                SettingsUtil.scrollToObject(device, region, target));
        device.findObject(target).clickAndWaitForNewWindow();

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
                        new UiSelector().resourceIdMatches(Res.DIALER_IN_CALL_RES)).
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

        device.executeShellCommand("am start -a android.intent.action.VIEW -d geo:0,0");
        device.waitForIdle();
        final UiObject acceptAndContinueButton;
        acceptAndContinueButton = device.findObject(new UiSelector().
                textMatches("(?i)accept\\s&\\scontinue"));
        if (acceptAndContinueButton.waitForExists(5000L))
            acceptAndContinueButton.clickAndWaitForNewWindow();

        final UiObject skipButton;
        skipButton = device.findObject(new UiSelector().textMatches("(?i)skip"));
        if (skipButton.waitForExists(5000L))
            skipButton.clickAndWaitForNewWindow();

        final UiObject gotItButton;
        gotItButton = device.findObject(new UiSelector().textMatches("(?i)got\\sit"));
        if (gotItButton.waitForExists(5000L))
            gotItButton.clickAndWaitForNewWindow();

        final UiObject myLocation;
        myLocation = device.findObject(new UiSelector().resourceId(Res.ANDROID_MY_LOCATION));
        if (myLocation.waitForExists(5000L))
            myLocation.clickAndWaitForNewWindow();

        final UiObject allowForegroundButton = device.findObject(
                new UiSelector().resourceId(Res.PERMISSION_ALLOW_FOREGROUND_BUTTON));
        assertTrue("Did not prompt for lack of Maps permission.",
                new Wait(20000L).until(allowForegroundButton::exists));

        device.pressHome();

        SettingsUtil.setAppPermissions_v3(instrumentation, appName, appName, true,
                "Deny anyway", "Apps", "Permission manager");
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
        DeveloperOptionsManager.enableDeveloperOptions_v3(testFramework);
        assertTrue("Failed to enable Developer options.",
                AppLauncher.launchPath(
                        instrumentation, true, "Settings", "System", "Developer options"));
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
            AppLauncher.launchPath(
                    instrumentation, true, "Settings", "System", "Date & time");

        } catch (Exception e) {
            Log.e(TAG, Objects.requireNonNull(e.getMessage()));
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
            AppLauncher.launchPath(
                    instrumentation, true, "Settings", "System", "Date & time");
        } catch (Exception e) {
            Log.e(TAG, Objects.requireNonNull(e.getMessage()));
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

        UiObject timeZoneLabel = device.findObject(new UiSelector().textMatches("Time zone").
                resourceId(Res.ANDROID_TITLE_RES).packageName("com.android.settings"));
        if (timeZoneLabel.waitForExists(3L)) {
            timeZoneLabel.clickAndWaitForNewWindow();
        }

        String timezoneOffset = "GMT-08:00";
        assertTrue("Target time zone label not found",
                device.findObject(new UiSelector().textContains(timezoneOffset)).waitForExists(3L));
    }

    /**
     * Verifies that the user can register the device from Google Settings.
     * <p>
     * <p>
     *   <pre>
     *   1. Start the emulator.
     *   2. Open Settings > Google
     *   3. Check if user account is registered to the device.
     *   4. Remove Google account if logged in.
     *   5. Log in user account from Settings > Google.
     *   Verify:
     *   User Google account has been successfully logged in.
     *   </pre>
     */
    @Test
    @ScreenRecord
    public void testGoogleLoginSettings() throws Exception {
        String userEmail = GoogleAppUtil.getUserEmail();
        String userPassword = GoogleAppUtil.getUserPassword();

        final UiObject userLoginInfo = device.findObject(
                new UiSelector().
                        className(TextView.class).
                        text(userEmail));

        boolean wasUserLoggedIn = SettingsUtil.verifyGoogleAccountStatus(
                instrumentation, userLoginInfo);
        if (wasUserLoggedIn) {
            userLoginInfo.clickAndWaitForNewWindow();
            assertTrue("Google account could not be removed.",
                    SettingsUtil.removeGoogleAccount(device, userEmail));

            final UiObject passwordsLabel = device.findObject(
                    new UiSelector().
                            resourceId(Res.SETTINGS_COLLAPSING_TOOLBAR_RES).
                            description("Passwords & accounts").
                            className(FrameLayout.class));

            assertTrue("Passwords & accounts label not found.",
                    new Wait(1000L).until(passwordsLabel::exists));

            device.pressBack();

            if (passwordsLabel.waitForExists(5000L)) {
                passwordsLabel.waitUntilGone(5000L);
            }
        }

        final UiObject manageAccountButton = device.findObject(
                new UiSelector()
                        .text(wasUserLoggedIn ? "Manage your Google Account" : "Sign in to your Google Account")
                        .className(Button.class));

        assertTrue("Manage Google account button not found.",
                new Wait(20000L).until(manageAccountButton::exists));

        manageAccountButton.click();

        if (wasUserLoggedIn) {
            final UiObject addAccountButton = device.findObject(
                    new UiSelector().
                            resourceId(Res.GOOGLE_ACCOUNT_POSITIVE_BUTTON_RES).
                            text("Add account").
                            className(Button.class));
            if (addAccountButton.waitForExists(5000L)) {
                addAccountButton.click();
                assertTrue("Add Google account button not dismissed.",
                        addAccountButton.waitUntilGone(10000L));
            }
        } else {
            assertTrue("Manage Google account button not dismissed.",
                    manageAccountButton.waitUntilGone(10000L));
        }
        final UiObject checkingInfoLabel = device.findObject(
                new UiSelector().resourceId(Res.GOOGLE_LAYOUT_ICON_RES));

        assertTrue("Checking info label before email input not found.",
                new Wait(10000L).until(checkingInfoLabel::exists));

        assertTrue("Checking info label before email input not dismissed.",
                checkingInfoLabel.waitUntilGone(90000L));

        final UiObject signInLabel = device.findObject(
                new UiSelector().
                        text("Sign in").
                        resourceId("headingText").
                        className(TextView.class));
        assertTrue("Sign in label not found.",
                new Wait(90000L).until(signInLabel::exists));

        final UiObject googleEmailInput = device.findObject(
                new UiSelector().
                        resourceId("identifierId").
                        className(EditText.class));

        assertTrue(wasUserLoggedIn ? "After logout: " : "First attempt: " + "Google account email input not found.",
                new Wait(20000L).until(googleEmailInput::exists));

        googleEmailInput.clearTextField();
        googleEmailInput.setText(userEmail);
        googleEmailInput.clickAndWaitForNewWindow(3000L);
        device.pressEnter();

        assertTrue(wasUserLoggedIn ? "After logout: " : "First attempt: " + "Email input entry page not dismissed.",
                googleEmailInput.waitUntilGone(90000L));

        final UiObject googlePasswordInput = device.findObject(
                new UiSelector().
                        className(EditText.class));

        assertTrue(wasUserLoggedIn ? "After logout: " : "First attempt: " + "Google account password input not found.",
                new Wait(20000L).until(googlePasswordInput::exists));

        googlePasswordInput.clearTextField();
        googlePasswordInput.setText(userPassword);
        googlePasswordInput.clickAndWaitForNewWindow(3000L);
        device.pressEnter();

        assertTrue(wasUserLoggedIn ? "After logout: " : "First attempt: " + "Password input entry page not dismissed.",
                googlePasswordInput.waitUntilGone(90000L));

        final UiObject iAgreeButton = device.findObject(
                new UiSelector().
                        text("I agree").
                        className(Button.class));

        assertTrue("Agree button not found.",
                new Wait(30000L).until(iAgreeButton::exists));

        iAgreeButton.click();

        assertTrue("Agree button not dismissed.",
                iAgreeButton.waitUntilGone(90000L));

        final UiObject googleServicesLabel = device.findObject(
                new UiSelector().
                        text("Google services").
                        resourceId(Res.GOOGLE_SERVICES_LABEL_RES).
                        className(TextView.class));

        assertTrue("Logged in Google Services not found.",
                new Wait(60000L).until(googleServicesLabel::exists)
        );

        AppLauncher.launchPath(
                instrumentation, true, "Settings", "Google");

        boolean isUserLoggedIn = SettingsUtil.verifyGoogleAccountStatus(instrumentation, userLoginInfo);

        assertTrue("User login not confirmed", isUserLoggedIn);
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
            AppLauncher.launchPath(
                    instrumentation, true, "Settings", "System", "Date & time");
        } catch (Exception e) {
            Log.e(TAG, Objects.requireNonNull(e.getMessage()));
        }

        boolean autoTwentyFourWasEnabled = false;
        boolean useTwentyFourWasEnabled = false;
        
        final UiSelector twentyFourHourSelector = new UiSelector().text("Use 24-hour format");
        UiObject useTwentyFourLabel = device.findObject(twentyFourHourSelector);
        UiObject autoTwentyFourLabel = device.findObject(new UiSelector().text("Use locale default"));
        final UiObject thirteenHundredLabel = device.findObject(new UiSelector().text("13:00"));
        
        UiSelector dateTimeRegion = new UiSelector().resourceIdMatches(Res.SETTINGS_LIST_CONTAINER_RES);
        SettingsUtil.scrollToObject(device, dateTimeRegion, twentyFourHourSelector);

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
    @Ignore("Device admin apps are not supported on API 33")
    public void activateDeactivatePolicy() throws Exception {
        ApiDemosInstaller.installApp("Security", "Device admin apps", false);

        try {
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
        } catch(Exception e) {
            Log.e(TAG,"activateDeactivatePolicy: required APK is missing");
            Log.e(TAG,"error: " + e.getMessage());
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
        String storageText = "Photos and videos";

        // Variables to store the state of permissions.
        boolean contactsSwitchState;
        boolean locationSwitchState;
        boolean microphoneSwitchState;
        boolean storageSwitchState;

        AppManager.openAppList_v3(instrumentation);

        final UiObject allAppsTextLabel = device.findObject(new UiSelector()
                .resourceId(Res.ANDROID_TITLE_RES).text("All apps"));

        new Wait().until(allAppsTextLabel::exists);
        allAppsTextLabel.clickAndWaitForNewWindow();

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
        assertTrue("Contact switch not found", contactSwitch.waitForExists(5000L));
        contactSwitch.click();
        UiObject contactsAllowSwitch = device.findObject(new UiSelector().resourceIdMatches(Res.ALLOW_PERMISSION_BUTTON));

        contactsSwitchState = contactsAllowSwitch.isChecked();
        if (contactsSwitchState) {
            UiObject contactsDenySwitch = device.findObject(new UiSelector().resourceIdMatches(Res.DENY_PERMISSION_BUTTON));
            contactsDenySwitch.clickAndWaitForNewWindow(1000);
        }

        assertFalse("Contacts permission already allowed", contactsAllowSwitch.isChecked());
        contactsAllowSwitch.clickAndWaitForNewWindow(1000);
        assertTrue("Contacts permission not allowed", contactsAllowSwitch.isChecked());
        device.pressBack();

        UiObject locationSwitch =
                permissionList.getChildByText(new UiSelector().className("android.widget.TextView"), locationText);
        locationSwitch.click();
        UiObject locationAllowSwitch = device.findObject(new UiSelector().resourceIdMatches(Res.ALLOW_PERMISSION_BUTTON));

        locationSwitchState = locationAllowSwitch.isChecked();
        if (locationSwitchState) {
            UiObject locationDenySwitch = device.findObject(new UiSelector().resourceIdMatches(Res.DENY_PERMISSION_BUTTON));
            locationDenySwitch.clickAndWaitForNewWindow(1000);
        }

        assertFalse("Location permission already allowed", locationAllowSwitch.isChecked());
        locationAllowSwitch.clickAndWaitForNewWindow(1000);
        assertTrue("Location permission not allowed", locationAllowSwitch.isChecked());
        device.pressBack();

        UiObject microphoneSwitch =
                permissionList.getChildByText(new UiSelector().className("android.widget.TextView"), microphoneText);
        microphoneSwitch.clickAndWaitForNewWindow(1000);
        UiObject microphoneAllowSwitch = device.findObject(new UiSelector().resourceId(Res.ALLOW_FOREGROUND_ONLY_PERMISSION_BUTTON));

        microphoneSwitchState = microphoneAllowSwitch.isChecked();
        if (microphoneSwitchState) {
            UiObject microphoneDenySwitch = device.findObject(new UiSelector().resourceIdMatches(Res.DENY_PERMISSION_BUTTON));
            microphoneDenySwitch.clickAndWaitForNewWindow(1000);
        }

        assertFalse("Microphone permission already allowed", microphoneAllowSwitch.isChecked());
        microphoneAllowSwitch.clickAndWaitForNewWindow(1000);
        assertTrue("Microphone permission not allowed", microphoneAllowSwitch.isChecked());

        device.pressBack();

        UiObject storageSwitch =
                permissionList.getChildByText(new UiSelector().className("android.widget.TextView"), storageText);
        storageSwitch.click();
        UiObject storageAllowSwitch = device.findObject(new UiSelector().resourceIdMatches(Res.ALLOW_PERMISSION_BUTTON));

        storageSwitchState = storageAllowSwitch.isChecked();
        if (storageSwitchState) {
            UiObject storageDenySwitch = device.findObject(new UiSelector().resourceIdMatches(Res.DENY_PERMISSION_BUTTON));
            storageDenySwitch.clickAndWaitForNewWindow(1000);
        }

        assertFalse("Storage permission already allowed", storageAllowSwitch.isChecked());
        storageAllowSwitch.clickAndWaitForNewWindow(1000);
        assertTrue("Storage permission not allowed", storageAllowSwitch.isChecked());

        device.pressBack();


        //Go back two times to go to system apps page to reset permissions.
        device.pressBack();
        device.pressBack();

        //Reset app preferences from overflow menu.
        device.pressMenu();
        device.findObject(
                new UiSelector().textContains("Reset app preferences")).clickAndWaitForNewWindow();

        try {
            device.findObject(new UiSelector().textContains("Reset Apps")).clickAndWaitForNewWindow();
        } catch (Exception e) {
            Log.e(TAG, Objects.requireNonNull(e.getMessage()));
        }

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
        assertTrue("Contacts permissions ", contactsAllowSwitch.isChecked());
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
        if (!AppLauncher.launchPath(
                instrumentation, true, "Settings", "System", "Developer options")) {
            DeveloperOptionsManager.enableDeveloperOptions_v3(testFramework);
            Assert.assertTrue("Could not enable developer options",
                    AppLauncher.launchPath(
                            instrumentation, true, "Settings", "System", "Developer options"));
        }
        
        UiSelector region = new UiSelector().resourceIdMatches(Res.SETTINGS_LIST_CONTAINER_RES);
        UiSelector target = new UiSelector().text("USB debugging");

        assertTrue("USB debugging controls not found", SettingsUtil.scrollToObject(device, region, target));
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
            AppLauncher.launchPath(
                    instrumentation, true, "Settings", "Connected devices");
        } catch (Exception e) {
            Log.e(TAG, Objects.requireNonNull(e.getMessage()));
        }

        UiObject seeAll = device.findObject(new UiSelector()
                .text("See all"));

        if (new Wait().until(seeAll::exists)) {
            seeAll.clickAndWaitForNewWindow();
        }

        UiObject savedDevices = device.findObject(new UiSelector()
                .description("Saved devices")
                .resourceId(Res.SETTINGS_COLLAPSING_TOOLBAR_RES));

        boolean hasSavedDevices = new Wait().until(savedDevices::exists);

        UiObject androidErrorClose = device.findObject(
                new UiSelector().resourceId(Res.ANDROID_ERROR_CLOSE_RES));
        assertFalse("Settings Keeps Stopping error when revoking usb debugging", androidErrorClose.waitForExists(5L));

        UiObject actionBar = device.findObject(
                new UiSelector().resourceId(Res.SETTINGS_ACTION_BAR_RES).className("android.view.ViewGroup"));
        UiObject connectedDevices = device.findObject(
                new UiSelector().text("Previously connected devices").className("android.widget.TextView"));
        Assert.assertTrue("Connected devices were not listed",
                hasSavedDevices ||
                        (actionBar.waitForExists(5L) && connectedDevices.waitForExists(5L)));
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

