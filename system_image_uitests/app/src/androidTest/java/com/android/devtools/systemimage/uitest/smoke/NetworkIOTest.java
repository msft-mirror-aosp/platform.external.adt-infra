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

import com.android.devtools.systemimage.uitest.framework.SystemImageTestFramework;
import com.android.devtools.systemimage.uitest.utils.AppLauncher;
import com.android.devtools.systemimage.uitest.utils.NetworkUtil;
import com.android.devtools.systemimage.uitest.utils.Wait;

import org.junit.Assert;
import org.junit.Rule;
import org.junit.Test;
import org.junit.runner.RunWith;

import android.app.Instrumentation;
import android.support.test.runner.AndroidJUnit4;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiSelector;

/**
 * Test class for network connection on emulator.
 */
@RunWith(AndroidJUnit4.class)
public class NetworkIOTest {
    private static final String BROWSER_URL_TEXT_FIELD = "com.android.browser:id/url";
    private static final String BROWSER_SEARCH_ICON_RES = "com.android.browser:/id/progress";
    @Rule
    public final SystemImageTestFramework testFramework = new SystemImageTestFramework();

    /**
     * Verifies test browser successfully loads a web page.
     * <p>
     * Test Rail ID: T136017709
     */
    @Test
    public void testBrowserLoadsSite() throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();
        UiDevice device = testFramework.getDevice();

        // Check network connectivity.
        if (NetworkUtil.verifyNetworkStatus(device)) {
            AppLauncher.launch(instrumentation, "Browser");
            device.findObject(new UiSelector().resourceId(BROWSER_URL_TEXT_FIELD)).click();
            device.findObject(new UiSelector().resourceId(BROWSER_URL_TEXT_FIELD))
                    .clearTextField();
            device.findObject(new UiSelector().resourceId(BROWSER_URL_TEXT_FIELD))
                    .setText("google.com");
            device.pressEnter();

            // Verify if the load bar is there at first,
            // then verify if the loading bar finishes in 3 seconds (default timeout on Wait()).
            final UiObject progress =
                    device.findObject(new UiSelector().resourceId(BROWSER_SEARCH_ICON_RES));
            Assert.assertTrue("Failed to find the loading bar.", progress.exists());
            boolean isSuccess =
                    new Wait().until(new Wait.ExpectedCondition() {
                        @Override
                        public boolean isTrue() throws Exception {
                            return !progress.exists();
                        }
                    });
            Assert.assertTrue("Failed to dismiss the loading bar.", isSuccess);
        }
    }
}