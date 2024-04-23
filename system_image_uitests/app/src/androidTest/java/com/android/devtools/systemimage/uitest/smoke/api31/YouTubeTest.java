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
package com.android.devtools.systemimage.uitest.smoke.api31;

import android.app.Instrumentation;
import.androidx.test.runner.AndroidJUnit4;
import.androidx.test.uiautomator.UiDevice;
import.androidx.test.uiautomator.UiObject;
import.androidx.test.uiautomator.UiSelector;

import com.android.devtools.systemimage.uitest.annotations.TestInfo;
import com.android.devtools.systemimage.uitest.common.Res;
import com.android.devtools.systemimage.uitest.framework.SystemImageTestFramework;
import com.android.devtools.systemimage.uitest.utils.AppLauncher;
import com.android.devtools.systemimage.uitest.utils.GoogleAppUtil;
import com.android.devtools.systemimage.uitest.utils.YouTubeUtil;

import org.junit.FixMethodOrder;
import org.junit.Ignore;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.Timeout;
import org.junit.runner.RunWith;
import org.junit.runners.MethodSorters;

import static junit.framework.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

/**
 * Test to verify that YouTube is installed and working correctly on Google API images
 */

@RunWith(AndroidJUnit4.class)
/*
 *Added this annotation so that YouTube version is checked first before login happens.
 *This is done  because if login happens first, it will update the app and version check
 *test will always pass.
 */
@FixMethodOrder(MethodSorters.NAME_ASCENDING)
public class YouTubeTest {

    @Rule
    public final SystemImageTestFramework testFramework = new SystemImageTestFramework();

    @Rule
    public Timeout globalTimeout = Timeout.seconds(7200);

    /**
     * Verify YouTube has the latest version or not.
     *   <pre>
     *   Test Steps:
     *   1. Start an emulator and launch home screen.
     *   2. Open Apps.
     *   3. Launch YouTube app.
     *   Verify:
     *      1. Verify that there is no YouTube update screen.
     *   </pre>
     */
    @Test
    @Ignore("Covered by media test suite")
    public void checkYouTubeVersion() throws Exception{
        Instrumentation instrumentation = testFramework.getInstrumentation();
        UiDevice device = UiDevice.getInstance(instrumentation);

        YouTubeUtil.launchYouTube(instrumentation);
        UiObject updateLaterButton = device.findObject(new UiSelector().resourceId(Res.YOUTUBE_UPDATE_LATER_BUTTON_RES));
        assertFalse("Device has older version of YouTube installed", updateLaterButton.waitForExists(5L));
    }

    /**
     * Verify YouTube login and logout are working correctly.
     *   <pre>
     *   Test Steps:
     *   1. Start an emulator and launch home screen
     *   2. Sign out of YouTube if already logged in
     *   3. Launch Chrome app and sign in to Chrome
     *   4. Launch YouTube and check for user account
     *   5. Sign out of You Tube
     *   Verify:
     *      1. Verify that Chrome login synced with YouTube login
     *      2. Verify that Google Account Services logout removed YouTube user
     *   </pre>
     */
    @Test
    @Ignore("Covered by media test suite")
    public void loginYouTube() throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();
        UiDevice device = UiDevice.getInstance(instrumentation);

        if (YouTubeUtil.isTestUserLoggedIn(instrumentation)) {
            YouTubeUtil.logoutYouTubeAccount(instrumentation);

            assertFalse("YouTube log out was unsuccessful",
                    YouTubeUtil.isTestUserLoggedIn(instrumentation));
        }

        UiObject doneButton = device.findObject(
                new UiSelector().packageName("com.google.android.youtube")
                        .className("android.widget.ImageButton")
                        .description("Close"));

        if (doneButton.waitForExists(5000L)) {
            doneButton.clickAndWaitForNewWindow();
        }

        assertTrue("Google log in was unsuccessful",
                GoogleAppUtil.loginGoogleApp(instrumentation, true));

        assertTrue("YouTube log in was unsuccessful",
                YouTubeUtil.isTestUserLoggedIn(instrumentation));

        YouTubeUtil.logoutYouTubeAccount(instrumentation);
        assertFalse("YouTube log out was unsuccessful",
                YouTubeUtil.isTestUserLoggedIn(instrumentation));
    }
}
