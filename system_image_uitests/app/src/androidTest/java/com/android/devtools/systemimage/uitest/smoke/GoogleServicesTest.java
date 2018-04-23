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

import android.app.Instrumentation;
import android.support.test.runner.AndroidJUnit4;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiObjectNotFoundException;
import android.support.test.uiautomator.UiScrollable;
import android.support.test.uiautomator.UiSelector;

import com.android.devtools.systemimage.uitest.annotations.TestInfo;
import com.android.devtools.systemimage.uitest.common.Res;
import com.android.devtools.systemimage.uitest.framework.SystemImageTestFramework;
import com.android.devtools.systemimage.uitest.utils.AppLauncher;
import com.android.devtools.systemimage.uitest.utils.AppManager;
import com.android.devtools.systemimage.uitest.utils.SystemUtil;
import com.android.devtools.systemimage.uitest.utils.Wait;
import com.android.devtools.systemimage.uitest.watchers.AddGoogleAccountWatcher;
import com.android.devtools.systemimage.uitest.watchers.GoogleChromeConfirmationWatcher;

import org.junit.Rule;
import org.junit.Test;
import org.junit.runner.RunWith;

import static org.junit.Assert.assertTrue;

/**
 * Test to verify that Google services are available on Google API images
 */

@RunWith(AndroidJUnit4.class)
public class GoogleServicesTest {
    private static final String WIDGET_TEXT_VIEW_CLASS = "android.widget.TextView";

    @Rule
    public final SystemImageTestFramework testFramework = new SystemImageTestFramework();

    private int api = testFramework.getApi();

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

        AppManager.openSystemAppList(instrumentation);

        UiScrollable appList=
                new UiScrollable(new UiSelector().resourceIdMatches(Res.APPS_LIST_CONTAINER_RES));
        appList.setAsVerticalList();

        assertTrue("Cannot find Google Play services", appList.getChildByText(
                new UiSelector().className(WIDGET_TEXT_VIEW_CLASS),
                "Google Play services").exists());
        assertTrue("Cannot find Google Services Framework", appList.getChildByText(
                new UiSelector().className(WIDGET_TEXT_VIEW_CLASS),
                "Google Services Framework").exists());
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
     *   Location enable toggle button
     *   Verify location Mode
     *   Verify recent location requests
     *   </pre>
     */
    @Test
    @TestInfo(id = "14578827")
    public void verifyLocationSettings() throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();
        UiDevice device = UiDevice.getInstance(instrumentation);

        // Open settings
        AppLauncher.launch(instrumentation, "Settings");

        // Find and click "Location" in Settings
        UiScrollable itemList =
                new UiScrollable(
                        new UiSelector().resourceIdMatches(Res.SETTINGS_LIST_CONTAINER_RES)
                );
        itemList.setAsVerticalList();
        if(api > 18) {
            if(api >= 26) {
                String securityLabel = api == 26 ? "Security & Location" : "Security & location";
                UiObject security = itemList.getChildByText(new UiSelector().className("android.widget.TextView"),
                        securityLabel);
                security.clickAndWaitForNewWindow();
            }
            UiObject location = itemList.getChildByText(new UiSelector().className(WIDGET_TEXT_VIEW_CLASS),
                            "Location");
            location.clickAndWaitForNewWindow();

            assertTrue("Cannot find location toggle button", device.findObject(
                    new UiSelector().className("android.widget.Switch")).exists());
            assertTrue("Cannot find mode", device.findObject(new UiSelector().text(
                    "Mode")).exists());
            assertTrue("Cannot find recent location", device.findObject(new UiSelector().text(
                    "Recent location requests")).exists());
        } else {
            UiObject item =
                    itemList.getChildByText(
                            new UiSelector().className(WIDGET_TEXT_VIEW_CLASS),
                            "Location access");
            item.clickAndWaitForNewWindow();

            // API specific assertion, since mode and recent location requests are absent in API 18
            assertTrue("Cannot find location toggle button", device.findObject(new
                    UiSelector().className("android.widget.Switch")).exists());
        }
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
     *   3. Log into Chrome using the test account.
     *   4. Logout to reset.
     *   Verify:
     *   1) Chrome login success page was reached.
     *   2) Chrome logout page was reached.
     *   </pre>
     */
    @Test
    @TestInfo(id = "d7f5673a-a3d0-4f50-856a-dfa10ce5c21c")
    public void loginGoogleChrome() throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();
        final UiDevice device = UiDevice.getInstance(instrumentation);

        if (api < 24 || !testFramework.isGoogleApiImage()) {
            return;
        }

        UiObject inputPasswordField = device.findObject(new UiSelector().resourceId("password"));
        final String email = "pstester1980@gmail.com";
        final String password = "pst4lif3";

        AppLauncher.launch(instrumentation, "Chrome");
        new AddGoogleAccountWatcher(device).checkForCondition();

        final UiObject signInButton = device.findObject(new UiSelector().text("SIGN IN"));
        boolean hasSignInButton = new Wait(5L).
                until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() throws UiObjectNotFoundException {
                        return signInButton.exists();
                    }
                });
        if (!hasSignInButton) {
            return;
        }
        signInButton.clickAndWaitForNewWindow();

        boolean needsEmail = new Wait().
                until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() throws UiObjectNotFoundException {
                        if (api == 24) {
                            return device.findObject(
                                    new UiSelector().description("Email or phone")).exists();
                        } else {
                            return device.findObject(
                                    new UiSelector().text("Email or phone")).exists();
                        }
                    }
                });

        if (!needsEmail) {
            boolean needsPassword = new Wait().
                    until(new Wait.ExpectedCondition() {
                        @Override
                        public boolean isTrue() throws UiObjectNotFoundException {
                            if (api == 24) {
                                return device.findObject(
                                        new UiSelector().description("Sign in " + email)).exists();
                            } else {
                                return device.findObject(
                                        new UiSelector().text("Sign in " + email)).exists();
                            }
                        }
                    });
            if (!needsPassword) {
                device.pressHome();
                return;
            }

            new GoogleChromeConfirmationWatcher(device).checkForCondition();
            if (api == 24) {
                inputPasswordField = device.findObject(new UiSelector().text("password"));
            } else {
                inputPasswordField = device.findObject(new UiSelector().className("android.widget.EditText"));
            }
            inputPasswordField.clearTextField();
            inputPasswordField.setText(password);
        } else {
            UiObject inputEmailField;
            if (api == 24) {
                inputEmailField = device.findObject(new UiSelector().description("Email or phone"));
            } else {
                inputEmailField = device.findObject(new UiSelector().text("Email or phone"));
            }
            inputEmailField.clearTextField();
            inputEmailField.setText(email);
            new GoogleChromeConfirmationWatcher(device).checkForCondition();
            if (api == 24) {
                inputPasswordField = device.findObject(new UiSelector().text("password"));
            } else {
                inputPasswordField = device.findObject(new UiSelector().className("android.widget.EditText"));
            }
            inputPasswordField.clearTextField();
            inputPasswordField.setText(password);
        }

        new GoogleChromeConfirmationWatcher(device).checkForCondition();
        device.pressHome();
        AppLauncher.launch(instrumentation, "Chrome");

        final UiObject gotItButton = device.findObject(new UiSelector().text("OK, GOT IT"));
        final UiObject undoButton = device.findObject(new UiSelector().text("UNDO"));

        assertTrue("Google log in was unsuccessful", new Wait().
                until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() throws UiObjectNotFoundException {
                        return gotItButton.exists() && undoButton.exists();
                    }
                }));

        undoButton.clickAndWaitForNewWindow();

        final UiObject noThanksButton = device.findObject(new UiSelector().text("NO THANKS"));

        assertTrue("Google log out was unsuccessful", new Wait().
                until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() throws UiObjectNotFoundException {
                        return noThanksButton.exists();
                    }
                }));

        noThanksButton.clickAndWaitForNewWindow();
    }
}
