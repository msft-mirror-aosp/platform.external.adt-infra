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
import com.android.devtools.systemimage.uitest.watchers.watcher;

import android.app.Instrumentation;
import android.content.Context;
import android.graphics.Point;
import android.graphics.Rect;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiObjectNotFoundException;
import android.support.test.uiautomator.UiSelector;
import android.telephony.TelephonyManager;
import android.util.DisplayMetrics;
import android.util.Log;
import android.view.Display;
import android.view.WindowManager;

import com.android.devtools.systemimage.uitest.framework.SystemImageTestFramework;

import org.junit.Rule;

import java.util.concurrent.TimeUnit;

/**
 * Static utility methods pertaining to network status.
 */
public class NetworkUtil {
    private NetworkUtil() {
        throw new AssertionError();
    }

    private static final String TAG = "NetworkUtil";

    @Rule
    private final static SystemImageTestFramework testFramework = new SystemImageTestFramework();

    public static boolean hasCellularNetworkConnection(Instrumentation instrumentation) {
        TelephonyManager tm = (TelephonyManager) instrumentation.getContext().
                getSystemService(Context.TELEPHONY_SERVICE);
        Log.i("NetworkUtil", "Cellular network state is: " + tm.getDataState());

        return tm.getDataState() != TelephonyManager.DATA_DISCONNECTED;
    }

    /**
     * Version 1 for api <= 23
     *
     * @param device
     * @return
     */
    public static UiObject getAirplaneModeIcon_v1(UiDevice device) {
        return device.findObject(new UiSelector().resourceId("com.android.systemui:id/airplane"));
    }

    /**
     * Version 2 for api >= 24 && <= 27.
     *
     * @param device
     * @return
     */
    public static UiObject getAirplaneModeIcon_v2(UiDevice device) {
        return device.findObject(new UiSelector().description("Airplane mode"));
    }

    /**
     * Version 3 for api >= 28.
     *
     * @param device
     * @return
     */
    public static UiObject getAirplaneModeIcon_v3(UiDevice device) {
        return device.findObject(new UiSelector().description("Airplane mode").
                className("android.widget.Switch"));
    }

    public static boolean isAirplaneModeEnabled(UiDevice device, UiObject airplaneModeIcon) throws Exception {
        openExtendedNotificationsPanel(device);

        boolean status;
        if (airplaneModeIcon.waitForExists(5L) && airplaneModeIcon.getText().toLowerCase().contains("on")) {
            status = true;
        } else {
            UiObject airplaneModeView = device.findObject(new UiSelector().descriptionStartsWith(("Airplane mode")));
            status = airplaneModeView.waitForExists(5L) && airplaneModeView.getContentDescription().toLowerCase().contains("on");
        }

        device.pressHome();

        return status;
    }

    static void openExtendedNotificationsPanel(UiDevice device) throws UiObjectNotFoundException, InterruptedException {
        device.pressHome();

        UiObject pan = device.findObject(new UiSelector().resourceIdMatches(Res.ANDROID_NOTIFICATION_DRAWER));
        Rect panRect = pan.getBounds();

        device.openNotification();
        TimeUnit.SECONDS.sleep(2);
        device.drag(panRect.left, panRect.top, panRect.left, panRect.centerY(), 10);
    }
}
