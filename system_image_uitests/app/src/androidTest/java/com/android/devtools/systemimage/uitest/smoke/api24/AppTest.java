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

package com.android.devtools.systemimage.uitest.smoke.api24;

import android.app.Instrumentation;
import android.support.test.runner.AndroidJUnit4;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiObjectNotFoundException;
import android.support.test.uiautomator.UiSelector;
import android.util.Log;

import com.android.devtools.systemimage.uitest.annotations.TestInfo;
import com.android.devtools.systemimage.uitest.common.Res;
import com.android.devtools.systemimage.uitest.framework.SystemImageTestFramework;
import com.android.devtools.systemimage.uitest.utils.AppLauncher;
import com.android.devtools.systemimage.uitest.utils.PackageInstallationUtil;
import com.android.devtools.systemimage.uitest.utils.Wait;
import com.android.devtools.systemimage.uitest.watchers.AppWatcher;

import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.Timeout;
import org.junit.runner.RunWith;

import java.util.concurrent.TimeUnit;

import static org.junit.Assert.assertTrue;

/**
 * Test for app interactions.
 */
@RunWith(AndroidJUnit4.class)
public class AppTest {
    @Rule
    public final SystemImageTestFramework testFramework = new SystemImageTestFramework();

    @Rule
    public Timeout globalTimeout = Timeout.seconds(240);

    private final String TAG = "AppTest";

    /**
     * Verifies an app runs on the emulator.
     * <p/>
     * The test installs, launches, and uninstalls the app.
     * <p/>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p/>
     * TR ID: C14578823
     * <p/>
     *   <pre>
     *   Test Steps:
     *   1. Start the emulator.
     *   2. Install HelloComputer app.
     *   3. Open the app.
     *   Verify:
     *   App runs on the emulator. Image of a leaf is displayed on the emulator.
     *   </pre>
     * <p/>
     */
    @Test
    @TestInfo(id = "14578823")
    public void installAppAndLaunch() throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();
        String testPackageName = "com.example.android.rs.hellocompute";
        String apk = "HelloCompute.apk";
        String result = "";

        // Install RsHelloCompute, if not already present.
        boolean isHelloComputeInstalled = PackageInstallationUtil.
                isPackageInstalled(instrumentation, testPackageName);

        if (!isHelloComputeInstalled) {
            result = PackageInstallationUtil.installApk(instrumentation, apk);
            isHelloComputeInstalled = PackageInstallationUtil.
                    isPackageInstalled(instrumentation, testPackageName);
        }

        assertTrue("Application " + apk + " is not installed. Result: " + result,
                isHelloComputeInstalled);


        AppLauncher.launch(instrumentation, "RsHelloCompute");
        assertTrue(testFramework.getDevice().findObject(new UiSelector().resourceId(
                Res.APP_IMAGE_VIEW_ID)).exists());
    }

    /**
     * Verify website is bookmarked.
     * <p/>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p/>
     * TR ID: C14578831
     * <p/>
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
     *   Website is bookmarked.
     *   </pre>
     */
    @Test
    @TestInfo(id = "14578831")
    public void bookmarkWebSiteInBrowser() throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();
        final UiDevice device = UiDevice.getInstance(instrumentation);

        if (testFramework.isGoogleApiImage() || testFramework.isGoogleApiAndPlayImage()) {
            AppLauncher.launch(instrumentation, "Chrome");

            // If this is the first launch, dismiss the "Welcome to Chrome" screen.
            UiObject welcomeScreen = device.findObject(
                    new UiSelector().text("Welcome to Chrome"));
            if (welcomeScreen.waitForExists(TimeUnit.SECONDS.toMillis(3))) {
                device.findObject(
                        new UiSelector().resourceId(Res.CHROME_TERMS_ACCEPT_BUTTON_RES))
                        .clickAndWaitForNewWindow();
            }

            // Dismiss the "Sign in to Chrome" screen if it's there.
            UiObject noThanksButton = device.findObject(
                    new UiSelector().resourceIdMatches(Res.CHROME_NO_THANKS_BUTTON_RES));
            if (noThanksButton.waitForExists(TimeUnit.SECONDS.toMillis(3))) {
                noThanksButton.clickAndWaitForNewWindow();
            }

            // Click the search box if it's there.
            UiObject searchBox = device.findObject(new UiSelector().resourceId(
                    Res.CHROME_SEARCH_BOX_RES));
            if (searchBox.waitForExists(TimeUnit.SECONDS.toMillis(3))) {
                searchBox.clickAndWaitForNewWindow();
            }

            new AppWatcher(device).checkForCondition();

            UiObject textField = device.findObject(
                    new UiSelector().resourceId(Res.CHROME_URL_BAR_RES));

            textField.click();
            textField.clearTextField();
            // Include a timestamp in the URL so it's not already bookmarked. (On Chrome, the UI
            // changes in that case.)
            textField.setText("http://espn.com");
            device.pressEnter();
            device.pressMenu();

            boolean notBookmarked = new Wait().until(new Wait.ExpectedCondition() {
                @Override
                public boolean isTrue() throws UiObjectNotFoundException {
                    return device.findObject(new UiSelector().description("Bookmark this page")).exists();
                }
            });
            if (notBookmarked) {
                device.findObject(new UiSelector().description("Bookmark this page")).click();
                new AppWatcher(device).checkForCondition();
                device.pressMenu();
            }
            // After bookmarking, the button description changes.
            assertTrue("Bookmark was not set",
                    device.findObject(new UiSelector().description("Edit bookmark")).exists());
            // Verify the new bookmark is in the list.
            UiObject bookmarks = device.findObject(new UiSelector().text("Bookmarks"));
            bookmarks.waitForExists(TimeUnit.SECONDS.toMillis(5));
            if (bookmarks.exists()) {
                bookmarks.clickAndWaitForNewWindow();
            }

            Log.d(TAG, "The bookmark is set");
            new AppWatcher(device).checkForCondition();

            UiObject mobileBookmarks = device.findObject(new UiSelector().text("Mobile bookmarks")
                    .resourceId(Res.CHROME_TITLE_RES));
            mobileBookmarks.waitForExists(TimeUnit.SECONDS.toMillis(5));
            if (mobileBookmarks.exists()) {
                mobileBookmarks.clickAndWaitForNewWindow();
            }

            Log.d(TAG, "Searching for bookmark...");
            new AppWatcher(device).checkForCondition();

            assertTrue("Cannot find bookmark",
                    new Wait().until(new Wait.ExpectedCondition() {
                        @Override
                        public boolean isTrue() {
                            return device.findObject(
                                    new UiSelector().textContains(("kmarks"))).exists() &&
                                    device.findObject(new UiSelector().textContains("ESPN").resourceId(
                                            Res.CHROME_TITLE_RES)).exists();
                        }
                    })
            );

            device.findObject(new UiSelector().resourceId(
                    Res.CHROME_CLOSE_MENU_BUTTON_RES)).clickAndWaitForNewWindow();

            Log.d(TAG, "Closing the menu");

            // Delete the bookmark.
            device.pressMenu();
            device.findObject(
                    new UiSelector().description("Edit bookmark")).clickAndWaitForNewWindow();
            device.findObject(new UiSelector().description("Delete bookmarks")).click();

        }
    }
}