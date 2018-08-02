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

package com.android.devtools.systemimage.uitest.utils;

import com.android.devtools.systemimage.uitest.common.Res;

import android.support.test.uiautomator.By;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiSelector;

import java.util.concurrent.TimeUnit;

public class VpnTestUtil {
    private static final String VPN_ACTIVATED_TEXT = "VPN is activated by TestVPN";
    private static final String NETWORK_MONITORED_TEXT = "Network may be monitored";
    private static final String DEVICE_CONNECTED_TEXT = "Device connected to TestVPN";

    private VpnTestUtil() {
        throw new AssertionError();
    }

    /**
     * Version 1 for api <=23
     *
     * @param device
     * @return
     * @throws Exception
     */
    public static boolean verifyVpnStatus_v1(final UiDevice device) throws Exception {
        // Verify that a VPN lock icon is on the status bar.
        // Need to wait for a while to check the notification bar items
        // because opening notification is an animation.
        boolean isTrue = new Wait().until(new Wait.ExpectedCondition() {
            @Override
            public boolean isTrue() {
                device.openNotification();
                return device.hasObject(By.res(Res.VPN_LOCK_ICON_RES)) ||
                        device.hasObject(By.text(VPN_ACTIVATED_TEXT));
            }
        });
        device.pressHome();
        return isTrue;
    }

    /**
     * Version 2 for api >= 24
     *
     * @param device
     * @return
     * @throws Exception
     */
    public static boolean verifyVpnStatus_v2(final UiDevice device) throws Exception {
        // Verify that a VPN lock icon is on the status bar.
        // Need to wait for a while to check the notification bar items
        // because opening notification is an animation.
        // API 25 requires extra retry time to indentify VPN indicator.
        boolean isTrue = new Wait(TimeUnit.MILLISECONDS.convert(10L, TimeUnit.SECONDS)).until(new Wait.ExpectedCondition() {
            @Override
            public boolean isTrue() throws Exception {
                device.openNotification();
                device.findObject(new UiSelector().resourceId(Res.NOTIFICATION_BAR_EXPAND_RES)
                        .className("android.widget.ImageView")).click();
                return device.hasObject(By.text(NETWORK_MONITORED_TEXT)) ||
                        device.hasObject(By.text(DEVICE_CONNECTED_TEXT));
            }
        });
        device.pressHome();
        return isTrue;
    }
}