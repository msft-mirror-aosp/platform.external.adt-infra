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

package com.android.devtools.systemimage.uitest.smoke.api18;

import android.app.Instrumentation;
import android.support.test.runner.AndroidJUnit4;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiSelector;

import com.android.devtools.systemimage.uitest.annotations.TestInfo;
import com.android.devtools.systemimage.uitest.common.Res;
import com.android.devtools.systemimage.uitest.framework.SystemImageTestFramework;
import com.android.devtools.systemimage.uitest.utils.AppLauncher;
import com.android.devtools.systemimage.uitest.utils.NetworkUtil;
import com.android.devtools.systemimage.uitest.utils.Wait;

import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.Timeout;
import org.junit.runner.RunWith;

import static org.junit.Assert.assertTrue;

/**
 * Test class for network connection on emulator.
 */
@RunWith(AndroidJUnit4.class)
public class NetworkIOTest {
    @Rule
    public final SystemImageTestFramework testFramework = new SystemImageTestFramework();

    @Rule
    public Timeout globalTimeout = Timeout.seconds(240);

    /**
     * Verifies test browser successfully loads a web page.
     * <p>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p>
     * TR ID: C14578825
     * <p>
     *   <pre>
     *   Test Steps:
     *   1. Start the emulator.
     *   2. Launch browser app.
     *   3. Navigate to a website.
     *   Verify:
     *   Icons indicating working network connection displayed in status bar.
     *   Browser successfully loads the web page.
     *   </pre>
     */
    @Test
    @TestInfo(id = "14578825")
    public void testBrowserLoadsSite() throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();
        UiDevice device = testFramework.getDevice();

        // Check network connectivity.
        if (NetworkUtil.hasCellularNetworkConnection(instrumentation)) {
            AppLauncher.launch(instrumentation, "Browser");
            device.findObject(new UiSelector().resourceId(
                    Res.BROWSER_URL_TEXT_FIELD_RES)).click();
            device.findObject(new UiSelector().resourceId(Res.BROWSER_URL_TEXT_FIELD_RES))
                    .clearTextField();
            device.findObject(new UiSelector().resourceId(Res.BROWSER_URL_TEXT_FIELD_RES))
                    .setText("google.com");
            device.pressEnter();

            // Verify if the load bar is there at first,
            // then verify if the loading bar finishes in 3 seconds (default timeout on Wait()).
            final UiObject progress =
                    device.findObject(new UiSelector().resourceId(Res.BROWSER_SEARCH_ICON_RES));
            boolean isSuccess = new Wait().until(() -> !progress.exists());
            assertTrue("Failed to dismiss the loading bar.", isSuccess);
        }
    }
}