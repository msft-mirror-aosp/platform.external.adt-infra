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
import com.android.devtools.systemimage.uitest.watchers.VpnPopupWatcher;

import org.junit.Assert;
import org.junit.Rule;
import org.junit.Test;
import org.junit.runner.RunWith;

import android.app.Instrumentation;
import android.support.test.runner.AndroidJUnit4;
import android.support.test.uiautomator.By;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiSelector;
import android.support.test.uiautomator.Until;

import java.util.concurrent.TimeUnit;

/**
 * Test on VPN app.
 */
@RunWith(AndroidJUnit4.class)
public class VpnTest {
    private static final String START_VPN_BUTTON_RES = "com.test.vpn:id/start_vpn";
    private static final String VPN_LOCK_ICON_RES = "com.android.systemui:id/vpn";
    @Rule
    public final SystemImageTestFramework testFramework = new SystemImageTestFramework();

    private static boolean verifyVpnStatus(UiDevice device) {
        // Verify that a VPN lock icon is on the status bar.
        device.openNotification();
        // Need to wait for a while to check the notification bar items
        // because opening notification is an animation.
        boolean isTrue =
                device.wait(
                        Until.hasObject(By.res(VPN_LOCK_ICON_RES)),
                        TimeUnit.MILLISECONDS.convert(3L, TimeUnit.SECONDS)
                );
        device.pressHome();
        return isTrue;
    }

    /**
     * Tests if VPN works as expected.
     */
    @Test
    public void testVpn() throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();
        UiDevice device = testFramework.getDevice();

        // Check if VPN is on. If true, skip.
        if (!verifyVpnStatus(device)) {
            AppManager.installApp(instrumentation, "FredVPN.apk");
            AppLauncher.launch(instrumentation, "TestVPN");

            // Register a watcher to dismiss the popup dialog when starting VPN.
            device.registerWatcher(VpnPopupWatcher.class.getName(), new VpnPopupWatcher(device));
            device
                    .findObject(new UiSelector().resourceId(START_VPN_BUTTON_RES))
                    .clickAndWaitForNewWindow();
            Assert.assertTrue("Failed to find the VPN lock icon after starting VPN!",
                    verifyVpnStatus(device));
            device.removeWatcher(VpnPopupWatcher.class.getName());
        }
        AppManager.uninstallApp(instrumentation, "TestVPN", null);
    }
}
