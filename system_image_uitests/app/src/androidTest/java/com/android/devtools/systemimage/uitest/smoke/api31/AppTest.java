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
import android.support.test.runner.AndroidJUnit4;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiSelector;
import android.util.Log;

import com.android.devtools.systemimage.uitest.annotations.TestInfo;
import com.android.devtools.systemimage.uitest.common.Res;
import com.android.devtools.systemimage.uitest.framework.SystemImageTestFramework;
import com.android.devtools.systemimage.uitest.utils.AppLauncher;
import com.android.devtools.systemimage.uitest.utils.GoogleAppUtil;
import com.android.devtools.systemimage.uitest.utils.PackageInstallationUtil;
import com.android.devtools.systemimage.uitest.utils.Wait;
import com.android.devtools.systemimage.uitest.watchers.AppWatcher;
import com.android.devtools.systemimage.uitest.watchers.watcher;

import org.junit.Ignore;
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
    public Timeout globalTimeout = Timeout.seconds(360);

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
     *   2. Install BasicRenderScript app.
     *   3. Open the app.
     *   Verify:
     *   App runs on the emulator. Image of a leaf is displayed on the emulator.
     *   </pre>
     * <p/>
     */
    @Test
    @TestInfo(id = "14578823")
    @Ignore("Covered by CTS. Move to FAT")
    public void installAppAndLaunch() throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();
        UiDevice device = UiDevice.getInstance(instrumentation);
        String apk = "Appication-debug.apk";
        String appName = "BasicRenderScript";
        String result = PackageInstallationUtil.installApk(instrumentation, apk, true);

        new AppWatcher(device).checkForCondition();

        assertTrue("Application " + apk + " is not installed. Result: " + result,
                result.isEmpty());

        AppLauncher.launch(instrumentation, appName);
        new AppWatcher(device).checkForCondition();
        boolean hasApplication = testFramework.getDevice().findObject(new UiSelector().text(
                "BasicRenderScript")).waitForExists(5L);

        assertTrue("Application " + appName + " did not launch", hasApplication);
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
     *   2. Open Chrome.
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
    @Ignore("Covered by FAT")
    public void bookmarkWebSiteInBrowser() throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();
        final UiDevice device = UiDevice.getInstance(instrumentation);

        if (testFramework.isGoogleApiImage() || testFramework.isGoogleApiAndPlayImage()) {
            GoogleAppUtil.loginGoogleApp(instrumentation, true);
            AppLauncher.launch(instrumentation, "Chrome");

            // Click the search box if it's there.
            UiObject searchBox = device.findObject(new UiSelector().resourceId(
                    Res.CHROME_SEARCH_BOX_RES));
            if (searchBox.waitForExists(TimeUnit.SECONDS.toMillis(3))) {
                searchBox.clickAndWaitForNewWindow();
            }

            new watcher(device, Res.APP_WATCHER_PATTERN).checkForCondition();

            UiObject textField = device.findObject(
                    new UiSelector().resourceId(Res.CHROME_URL_BAR_RES));
            if (textField.waitForExists(TimeUnit.SECONDS.toMillis(15))) {
                textField.click();
                textField.clearTextField();
                // Include a timestamp in the URL so it's not already bookmarked. (On Chrome, the UI
                // changes in that case.)
                textField.setText("http://espn.com");
                device.pressEnter();
                device.pressMenu();
            }

            UiObject editBookmarkImage = device.findObject(new UiSelector()
                    .description("Edit bookmark").className("android.widget.ImageButton"));
            boolean isBookmarked = new Wait().until(editBookmarkImage::exists);
            if (!isBookmarked) {
                UiObject setBookmarkImage = device.findObject(new UiSelector()
                        .description("Bookmark").className("android.widget.ImageButton"));
                setBookmarkImage.click();
                new watcher(device, Res.APP_WATCHER_PATTERN).checkForCondition();
                device.pressMenu();
            }
            // After bookmarking, the button description changes.
            isBookmarked = editBookmarkImage.waitForExists(TimeUnit.SECONDS.toMillis(15));
            assertTrue("Bookmark was not set", isBookmarked);

            UiObject bookmarks = device.findObject(new UiSelector().text("Bookmarks"));
            bookmarks.waitForExists(TimeUnit.SECONDS.toMillis(15));
            if (bookmarks.exists()) {
                bookmarks.clickAndWaitForNewWindow();
            }

            String TAG = "AppTest";
            Log.d(TAG, "The bookmark is set");

            UiObject mobileBookmarks = device.findObject(new UiSelector().text("Mobile bookmarks")
                    .resourceId(Res.CHROME_TITLE_RES));
            mobileBookmarks.waitForExists(TimeUnit.SECONDS.toMillis(15));
            if (mobileBookmarks.exists()) {
                mobileBookmarks.clickAndWaitForNewWindow();
            }

            Log.d(TAG, "Searching for bookmark...");
            final UiObject bookmarkedSite = device.findObject(new UiSelector().textContains("ESPN"));

            assertTrue("Cannot find bookmark",
                    new Wait().until(() -> device.findObject(
                            new UiSelector().textContains(("kmarks"))).exists() &&
                            bookmarkedSite.exists())
            );

            bookmarkedSite.dragTo(bookmarkedSite,20);

            final UiObject trashCan = device.findObject(new UiSelector().
                    description("Delete bookmarks"));
            // Delete the bookmark.
            assertTrue("Cannot find trash",
                    new Wait().until(trashCan::exists)
            );

            trashCan.click();
        }
    }
}
