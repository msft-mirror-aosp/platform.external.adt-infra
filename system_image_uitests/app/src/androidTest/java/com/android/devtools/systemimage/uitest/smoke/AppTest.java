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
import com.android.devtools.systemimage.uitest.utils.AppLauncher;
import com.android.devtools.systemimage.uitest.utils.AppManager;

import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.Timeout;
import org.junit.runner.RunWith;
import static org.junit.Assert.*;

import android.app.Instrumentation;
import android.support.test.runner.AndroidJUnit4;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiSelector;

/**
 * Test for app interactions.
 */
@RunWith(AndroidJUnit4.class)
public class AppTest {
    @Rule
    public final SystemImageTestFramework testFramework = new SystemImageTestFramework();

    @Rule
    public Timeout globalTimeout = Timeout.seconds(90);

    /**
     * Verifies an app runs on the emulator.
     * <p>
     * The test installs, launches, and uninstalls the app.
     * <p>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p>
     * TR ID: C14578823
     * <p>
     *   <pre>
     *   Test Steps:
     *   1. Start the emulator.
     *   2. Install HelloComputer app.
     *   3. Open the app.
     *   Verify:
     *   App runs on the emulator. Image of a leaf is displayed on the emulator.
     *   </pre>
     */
    @Test
    @TestInfo(id = "14578823")
    public void installAppAndLaunch() throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();

        AppLauncher.launch(instrumentation, "RsHelloCompute");
        assertTrue(testFramework.getDevice().findObject(new UiSelector().resourceId(
                Res.APP_IMAGE_VIEW_ID)).exists());
    }

    /**
     * Verify website is bookmarked.
     * <p>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p>
     * TR ID: C14578831
     * <p>
     *   <pre>
     *   1. Launch emulator.
     *   2. Open Browser app.
     *   3. Tap on the address bar and enter espn.com
     *   4. Open menu (3 vertical dots).
     *   5. Tap on "Save to bookmarks" and tap OK.
     *   6. Assert message that bookmark is added.
     *   7. Open menu (3 vertical dots).
     *   8. Tap on "Bookmarks"
     *   Verify:
     *   ESPN website is bookmarked.
     *   </pre>
     */
    @Test
    @TestInfo(id = "14578831")
    public void bookmarkWebSiteInBrowser() throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();
        UiDevice device = UiDevice.getInstance(instrumentation);
        AppLauncher.launch(instrumentation, "Browser");
        UiObject textField = device.findObject(
                new UiSelector().resourceId(Res.BROWSER_URL_TEXT_FIELD_RES));
        textField.click();
        textField.clearTextField();
        textField.setText("espn.com");
        device.pressEnter();
        device.pressMenu();
        device.findObject(new UiSelector().text("Save to bookmarks")).click();
        device.findObject(new UiSelector().text("OK")).click();
        device.pressMenu();
        device.findObject(new UiSelector().text("Bookmarks")).click();
        assertTrue("Cannot find ESPN bookmark",
                device.findObject(new UiSelector().text("Bookmarks")).exists() &&
                device.findObject(new UiSelector().textContains(
                        "ESPN").resourceId(Res.BROWSER_BOOKMARKS_LABEL_RES)).exists());
    }
}
