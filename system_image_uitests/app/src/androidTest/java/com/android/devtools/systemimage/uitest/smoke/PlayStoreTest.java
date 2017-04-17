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
import com.android.devtools.systemimage.uitest.utils.PlayStoreUtil;
import com.android.devtools.systemimage.uitest.utils.Wait;

import org.junit.Ignore;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.Timeout;
import org.junit.runner.RunWith;

import static org.junit.Assert.assertTrue;

/**
 * Test to verify that Play Store services are available on Google API with Play Store images.
 */

@RunWith(AndroidJUnit4.class)
public class PlayStoreTest {
    private static final String WIDGET_TEXT_VIEW_CLASS = "android.widget.TextView";

    @Rule
    public final SystemImageTestFramework testFramework = new SystemImageTestFramework();

    @Rule
    public Timeout globalTimeout = Timeout.seconds(120);

    /**
     * Verify that Google Play can install an app on the device.
     * <p>
     * TR ID: C14578827
     * <p>
     *   <pre>
     *   Test Steps:
     *   1. Start an emulator and launch home screen.
     *   2. Open Apps.
     *   3. Confirm that Play Store is present, then launch.
     *   5. Search for test app in store.
     *   6. If app is available for install, begin installation.
     *   Verify:
     *      a. If Install button is displayed, allow installation to complete then
     *      confirm that the Open button to launch the app is present.
     *      b. If Install button is not displayed, confirm that the Open button to
     *      launch the app is present.
     *   </pre>
     */
    @Ignore("Testing play store requires google login that may trigger 2-auth factor. Test to be initiated manually by tester.")
    @Test
    @TestInfo(id = "14578827")
    public void testAppInstallation() throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();
        final UiDevice device = UiDevice.getInstance(instrumentation);
        final UiScrollable scrollable = new UiScrollable(new UiSelector().scrollable(true));
        final String playStore = "Play Store";
        final String appName = "Google Translate";

        if (testFramework.getApi() >= 24 && testFramework.isGoogleApiAndPlayImage()) {
            device.pressHome();
            device.findObject(new UiSelector().description("Apps")).clickAndWaitForNewWindow();

            boolean playStoreInstalled = PlayStoreUtil.isPlayStoreInstalled(instrumentation);

            if (playStoreInstalled) {
                device.findObject(new UiSelector().text(playStore)).clickAndWaitForNewWindow();

                boolean backButtonExists = new Wait().until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() throws UiObjectNotFoundException {
                        return device.findObject(
                                new UiSelector().resourceId(Res.GOOGLE_PLAY_NAV_RES)
                                        .description("Back")).exists();
                    }
                });

                if (backButtonExists) {
                    device.findObject(
                            new UiSelector().resourceId(Res.GOOGLE_PLAY_NAV_RES)
                                    .description("Back")).click();
                }

                boolean idleTextFieldExists = new Wait().until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() throws UiObjectNotFoundException {
                        return device.findObject(
                                new UiSelector().resourceId(Res.GOOGLE_PLAY_IDLE_RES)).exists();
                    }
                });

                if (idleTextFieldExists) {
                    device.findObject(
                            new UiSelector().resourceId(Res.GOOGLE_PLAY_IDLE_RES)).click();
                }

                boolean inputTextFieldExists = new Wait().until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() throws UiObjectNotFoundException {
                        return device.findObject(
                                new UiSelector().resourceId(Res.GOOGLE_PLAY_INPUT_RES)).exists();
                    }
                });

                if (inputTextFieldExists) {
                    UiObject inputTextField = device.findObject(
                            new UiSelector().resourceId(Res.GOOGLE_PLAY_INPUT_RES));
                    inputTextField.clearTextField();
                    inputTextField.setText(appName);
                    device.pressEnter();
                }

                boolean isListed = new Wait().until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() throws UiObjectNotFoundException {
                        return device.findObject(new UiSelector()
                                .description("App: Google Translate")).exists();
                    }
                });

                if (isListed) {
                    device.findObject(new UiSelector()
                            .description("App: Google Translate")).clickAndWaitForNewWindow();
                }

                boolean needsConfirmation = new Wait().until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() throws UiObjectNotFoundException {
                        return device.findObject(new UiSelector()
                                .resourceId(Res.GOOGLE_PLAY_POSITIVE_BUTTON_RES)).exists();
                    }
                });

                if (needsConfirmation) {
                    device.findObject(new UiSelector()
                            .resourceId(Res.GOOGLE_PLAY_POSITIVE_BUTTON_RES))
                            .clickAndWaitForNewWindow();
                }

                assertTrue("Unable to install the application from Google Play",
                        PlayStoreUtil.installApplication(instrumentation));
            }
        }
    }
}