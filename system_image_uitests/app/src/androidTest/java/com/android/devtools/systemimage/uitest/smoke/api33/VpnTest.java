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
import android.support.test.runner.AndroidJUnit4;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiSelector;

import com.android.devtools.systemimage.uitest.annotations.TestInfo;
import com.android.devtools.systemimage.uitest.common.Res;
import com.android.devtools.systemimage.uitest.framework.SystemImageTestFramework;
import com.android.devtools.systemimage.uitest.utils.AppLauncher;
import com.android.devtools.systemimage.uitest.utils.PackageInstallationUtil;
import com.android.devtools.systemimage.uitest.utils.VpnTestUtil;
import com.android.devtools.systemimage.uitest.watchers.VpnPopupWatcher;

import org.junit.Assert;
import org.junit.Ignore;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.Timeout;
import org.junit.runner.RunWith;

import static org.junit.Assert.assertTrue;

/**
 * Test on VPN app.
 */
@RunWith(AndroidJUnit4.class)
public class VpnTest {
    @Rule
    public final SystemImageTestFramework testFramework = new SystemImageTestFramework();

    @Rule
    public Timeout globalTimeout = Timeout.seconds(360);

    /**
     * Tests if VPN works as expected.
     * <p>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p>
     * TR ID: C14578822
     * <p>
     *   <pre>
     *   Test Steps:
     *   1. Start the emulator.
     *   2. Install FredVPN app.
     *   3. Open the app.
     *   4. Tap on Connect.
     *   Verify:
     *   The VPN app runs on the emulator. A VPN lock icon displays on the status bar.
     *   </pre>
     * <p/>
     */
    @Test
    @Ignore("Bug: 317918808 - No 'Install anyway' button element listed in the XML hierarchy")
    public void testVpn() throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();
        UiDevice device = testFramework.getDevice();
        String apk = "FredVPN.apk";
        String result = PackageInstallationUtil.installApk(instrumentation, apk, true);

        assertTrue("Application " + apk + " is not installed. Result: " + result,
                result.isEmpty());

        // Check if VPN is on. If true, skip.
        if (!VpnTestUtil.verifyVpnStatus_v2(device)) {
            AppLauncher.launch(instrumentation, "TestVPN");
            UiObject olderVersionWarning = device.findObject(
                    new UiSelector().textMatches("(?i)ok(?-i)"));
            if (olderVersionWarning.waitForExists(5000)) {
                olderVersionWarning.clickAndWaitForNewWindow();
            }
            device.findObject(new UiSelector().resourceId(Res.START_VPN_BUTTON_RES))
                    .clickAndWaitForNewWindow();
            new VpnPopupWatcher(device).checkForCondition();
            Assert.assertTrue("Failed to find the VPN lock icon after starting VPN!",
                    VpnTestUtil.verifyVpnStatus_v2(device));
        }
    }
}
