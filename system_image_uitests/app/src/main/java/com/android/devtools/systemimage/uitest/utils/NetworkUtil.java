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

import android.support.test.uiautomator.By;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.Until;

import java.util.concurrent.TimeUnit;

/**
 * Static utility methods pertaining to network status.
 */
public class NetworkUtil {
    private static final String WIFI_ICONS_RES = "com.android.systemui:id/wifi_signal";
    private static final String MOBILE_TYPE_ICONS_RES = "com.android.systemui:id/mobile_type";

    private NetworkUtil() {
        throw new AssertionError();
    }

    /**
     * Checks network status.
     *
     * @param device see {@link UiDevice#getInstance(android.app.Instrumentation) getInstance}
     * @return True if the emulator is connected to the internet via WiFi or mobile data.
     */
    public static boolean verifyNetworkStatus(UiDevice device) {
        // Verify that a mobile data or WiFi icon is on the status bar.
        device.openNotification();
        boolean hasWifi = verifyWifi(device);
        if (hasWifi) {
            device.pressHome();
            return true;
        }
        boolean hasMobileData = verifyMobileData(device);
        if (hasMobileData) {
            device.pressHome();
            return true;
        }
        device.pressHome();
        return false;
    }

    private static boolean verifyWifi(UiDevice device) {
        // Wait to check the notification bar items. Opening notification is an animation.
        boolean isTrue =
                device.wait(
                        Until.hasObject(By.res(WIFI_ICONS_RES)),
                        TimeUnit.MILLISECONDS.convert(3L, TimeUnit.SECONDS)
                );
        return isTrue;
    }

    private static boolean verifyMobileData(UiDevice device) {
        // Wait to check the notification bar items. Opening notification is an animation.
        boolean isTrue =
                device.wait(
                        Until.hasObject(By.res(MOBILE_TYPE_ICONS_RES)),
                        TimeUnit.MILLISECONDS.convert(3L, TimeUnit.SECONDS)
                );
        return isTrue;
    }
}