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

import android.content.ContentResolver;
import android.content.Context;
import android.provider.Settings;
import androidx.test.uiautomator.UiDevice;
import androidx.test.uiautomator.UiObject;
import androidx.test.uiautomator.UiObjectNotFoundException;
import androidx.test.uiautomator.UiSelector;

public class NetworkIOTestUtil {

    private NetworkIOTestUtil() {
        throw new AssertionError();
    }

    /**
     * Helper class to toggle the active data roaming status
     */
    public static void toggleAirplaneMode(UiDevice device) throws UiObjectNotFoundException {
        UiObject airplaneModeText = device.findObject(
                new UiSelector().text("Airplane mode"));
        boolean isFound = airplaneModeText.waitForExists(10L);
        if (isFound) {
            airplaneModeText.clickAndWaitForNewWindow();
        }
    }

    /**
     * Helper class to determine if data roaming is enabled
     * Note: this method is blocked on API's 26 and higher by a java.lang.SecurityException
     */
    public static boolean isDataRoamingEnabled(Context context) {
        try {
            String key = Settings.Global.DATA_ROAMING;
            ContentResolver cr = context.getContentResolver();
            return Settings.Global.getInt(cr, key, 0) == 1;
        } catch (Exception exception) {
            return false;
        }
    }

    /**
     * Helper class to toggle the active data roaming status
     */
    public static void toggleRoaming(UiDevice device) throws UiObjectNotFoundException {
        UiObject dataRoamingSwitch = device.findObject(new UiSelector().text("Data roaming"));
        dataRoamingSwitch.clickAndWaitForNewWindow();
        UiObject allowRoaming = device.findObject(new UiSelector().text("OK"));
        if (allowRoaming.exists()) {
            allowRoaming.clickAndWaitForNewWindow();
        }
    }
}
