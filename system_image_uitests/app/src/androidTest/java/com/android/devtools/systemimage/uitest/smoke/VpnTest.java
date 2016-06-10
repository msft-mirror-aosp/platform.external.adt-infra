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
import com.android.devtools.systemimage.uitest.utils.AppManager;
import com.android.devtools.systemimage.uitest.utils.Wait;
import com.android.devtools.systemimage.uitest.watchers.VpnPopupWatcher;

import org.junit.Assert;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.Timeout;
import org.junit.runner.RunWith;

import android.app.Instrumentation;
import android.support.test.runner.AndroidJUnit4;
import android.support.test.uiautomator.By;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiSelector;

/**
 * Test on VPN app.
 */
@RunWith(AndroidJUnit4.class)
public class VpnTest {
    private static final String START_VPN_BUTTON_RES = "com.test.vpn:id/start_vpn";
    private static final String VPN_LOCK_ICON_RES = "com.android.systemui:id/vpn";
    private static final String VPN_ACTIVATED_TEXT = "VPN is activated by TestVPN";

    @Rule
    public final SystemImageTestFramework testFramework = new SystemImageTestFramework();

    @Rule
    public Timeout globalTimeout = Timeout.seconds(60);

    private static boolean verifyVpnStatus(final UiDevice device) throws Exception {
        // Verify that a VPN lock icon is on the status bar.
        device.openNotification();
        // Need to wait for a while to check the notification bar items
        // because opening notification is an animation.
        boolean isTrue = new Wait().until(new Wait.ExpectedCondition() {
            @Override
            public boolean isTrue() throws Exception {
                return device.hasObject(By.res(VPN_LOCK_ICON_RES)) ||
                        device.hasObject(By.text(VPN_ACTIVATED_TEXT));
            }
        });
        device.pressHome();
        return isTrue;
    }

    /**
     * Tests if VPN works as expected.
     * <p>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p>
     * TR ID: C1457882
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
     */
    @Test
    public void testVpn() throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();
        UiDevice device = testFramework.getDevice();

        // Check if VPN is on. If true, skip.
        if (!verifyVpnStatus(device)) {
            AppManager.installApp(instrumentation, "FredVPN.apk");
            AppLauncher.launch(instrumentation, "TestVPN");

            device.findObject(new UiSelector().resourceId(START_VPN_BUTTON_RES))
                    .clickAndWaitForNewWindow();
            new VpnPopupWatcher(device).checkForCondition();
            Assert.assertTrue("Failed to find the VPN lock icon after starting VPN!",
                    verifyVpnStatus(device));
        }
        AppManager.uninstallApp(instrumentation, "TestVPN", null);
    }
}
