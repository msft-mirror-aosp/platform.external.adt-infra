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

import static org.junit.Assert.assertTrue;

import android.app.Instrumentation;
import androidx.test.runner.AndroidJUnit4;
import androidx.test.uiautomator.UiDevice;
import androidx.test.uiautomator.UiObject;
import androidx.test.uiautomator.UiScrollable;
import androidx.test.uiautomator.UiSelector;

import com.android.devtools.systemimage.uitest.annotations.ScreenRecord;
import com.android.devtools.systemimage.uitest.annotations.TestInfo;
import com.android.devtools.systemimage.uitest.common.Res;
import com.android.devtools.systemimage.uitest.framework.SystemImageTestFramework;
import com.android.devtools.systemimage.uitest.utils.AppLauncher;
import com.android.devtools.systemimage.uitest.utils.AppManager;
import com.android.devtools.systemimage.uitest.utils.GoogleAppUtil;
import com.android.devtools.systemimage.uitest.watchers.watcher;

import org.junit.Rule;
import org.junit.Test;
import org.junit.runner.RunWith;

/**
 * Test to verify that Google services are available on Google API images
 */

@RunWith(AndroidJUnit4.class)
public class GoogleServicesTest {
    private static final String WIDGET_TEXT_VIEW_CLASS = "android.widget.TextView";

    @Rule
    public final SystemImageTestFramework testFramework = new SystemImageTestFramework();

    /**
     * Verifies that Google services are available on Google API images
     * <p>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p>
     * TR ID: C14578827
     * <p>
     *   <pre>
     *   Test Steps:
     *   1. Start an emulator AVD targeting Google Add On image.
     *   2. Open Settings > Apps.
     *   3. From the Overflow menu, select "Show system".
     *   4. Scroll through the list.
     *   Verify:
     *   Google Play Services, Google Services Framework and Maps
     *   applications are present.
     *   </pre>
     */
    @Test
    @TestInfo(id = "14578827")
    public void verifyGoogleApps() throws Exception{
        Instrumentation instrumentation = testFramework.getInstrumentation();

        if (!testFramework.isGoogleApiImage() || !testFramework.isGoogleApiAndPlayImage()) {
            return;
        }

        AppManager.openAppList_v3(instrumentation);
        AppManager.openSystemAppList_v2(instrumentation);

        UiScrollable appList=
                new UiScrollable(new UiSelector().resourceIdMatches(Res.SETTINGS_LIST_CONTAINER_RES));
        appList.setAsVerticalList();

        assertTrue("Cannot find Gmail", appList.getChildByText(
                new UiSelector().className(WIDGET_TEXT_VIEW_CLASS),
                "Gmail").exists());
        assertTrue("Cannot find Google", appList.getChildByText(
                new UiSelector().className(WIDGET_TEXT_VIEW_CLASS),
                "Google").exists());
        assertTrue("Cannot find Google Play services", appList.getChildByText(
                new UiSelector().className(WIDGET_TEXT_VIEW_CLASS),
                "Google Play services").exists());
        assertTrue("Cannot find Google Play Store", appList.getChildByText(
                new UiSelector().className(WIDGET_TEXT_VIEW_CLASS),
                "Google Play Store").exists());
        assertTrue("Cannot find Maps", appList.getChildByText(
                new UiSelector().className(WIDGET_TEXT_VIEW_CLASS),
                "Maps").exists());
    }

    /**
     * Verify the contents of the Location Settings page
     * <p>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p>
     * TR ID: C14578827
     * <p>
     *   <pre>
     *   Test Steps:
     *   1. Start an emulator AVD targeting Google Add On image
     *   2. Open Settings > Location
     *   Verify:
     *   Location enable toggle button.
     *   </pre>
     */
    @Test
    @TestInfo(id = "14578827")
    public void verifyLocationSettings() throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();
        UiDevice device = UiDevice.getInstance(instrumentation);

        // Open settings
        AppLauncher.launch(instrumentation, "Settings");
        new watcher(device, Res.ADD_GOOGLE_ACC_WATCHER_PATTERN).checkForCondition();

        //Dismiss Set Up Wizard.
        UiObject cancelWizard = device.findObject(
                new UiSelector().resourceIdMatches(Res.CANCEL_SETUP_WIZARD_RES));

        if (cancelWizard.waitForExists(5L)) {
            cancelWizard.clickAndWaitForNewWindow();
        }

        //Defer until later today.
        UiObject deferUntilLater = device.findObject(
                new UiSelector().resourceIdMatches(Res.DEFERRED_SNOOZE_ITEM_RES).index(0));

        if (deferUntilLater.waitForExists(5L)) {
            deferUntilLater.clickAndWaitForNewWindow();
        }

        // Find and click "Location" in Settings
        UiScrollable itemList =
                new UiScrollable(
                        new UiSelector().resourceIdMatches(Res.SETTINGS_LIST_CONTAINER_RES)
                );

        if (itemList.waitForExists(3L)) {
            itemList.setAsVerticalList();
        }

        String securityLabel = "Location";
        UiObject security = itemList.getChildByText(new UiSelector().className("android.widget.TextView"),
                securityLabel);

        if (security.waitForExists(3L)) {
            security.clickAndWaitForNewWindow();
        }

        assertTrue("Cannot find location toggle button",
                device.findObject(new UiSelector().resourceIdMatches(Res.ANDROID_SWITCH_TEXT_RES)
                        .text("Use location")).waitForExists(5L));
    }

    /**
     * Logs the user into Google Chrome app.
     * <p>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p>
     * TR ID: d7f5673a-a3d0-4f50-856a-dfa10ce5c21c
     * <p>
     *   <pre>
     *   Test Steps:
     *   1. Start an emulator with API 24+ Google APIs support.
     *   2. Launch Chrome.
     *   3. Log out of Chrome, if logged in already.
     *   4. Log into Chrome using the test account.
     *   5. Open the Chrome menu > Settings.
     *   6. Find logged user name.
     *   7. Log user out of Chrome.
     *   Verify:
     *   1. Logging into Chrome was successful.
     *   2. Logging out of Chrome was successful.
     *   </pre>
     */
    @Test
    @TestInfo(id = "d7f5673a-a3d0-4f50-856a-dfa10ce5c21c")
    @ScreenRecord
    public void loginGoogleChrome() throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();

        GoogleAppUtil.logoutGoogleChrome(instrumentation);

        boolean logInSuccess = GoogleAppUtil.loginGoogleApp(instrumentation, true);
        assertTrue("Google log in was unsuccessful", logInSuccess);

        boolean logOutSuccess = GoogleAppUtil.logoutGoogleChrome(instrumentation);
        assertTrue("Google log out was unsuccessful", logOutSuccess);
    }
}
