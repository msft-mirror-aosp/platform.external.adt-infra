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
import com.android.devtools.systemimage.uitest.watchers.NetworkUtilPopupWatcher;

import android.app.Instrumentation;
import android.content.Context;
import android.graphics.Point;
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
        UiObject airplaneModeIcon = device.findObject(new UiSelector().resourceId("com.android.systemui:id/airplane"));

        return airplaneModeIcon;
    }

    /**
     * Version 2 for api >= 24 && <= 27.
     *
     * @param device
     * @return
     */
    public static UiObject getAirplaneModeIcon_v2(UiDevice device) {
        UiObject airplaneModeIcon = device.findObject(new UiSelector().description("Airplane mode"));

        return airplaneModeIcon;
    }

    /**
     * Version 3 for api >= 28.
     *
     * @param device
     * @return
     */
    public static UiObject getAirplaneModeIcon_v3(UiDevice device) {
        UiObject airplaneModeIcon = device.findObject(new UiSelector().description("Airplane mode").
                className("android.widget.Switch"));

        return airplaneModeIcon;
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

        UiObject expandIndicator = device.findObject(
                new UiSelector().resourceId("com.android.systemui:id/qs_navbar_scrim"));
        expandIndicator.click();
        return status;
    }

    public static void openExtendedNotificationsPanel(UiDevice device)
            throws UiObjectNotFoundException {
        new NetworkUtilPopupWatcher(device).checkForCondition();
        device.openNotification();
        new NetworkUtilPopupWatcher(device).checkForCondition();

        UiObject expandIndicator = device.findObject(
                new UiSelector().resourceId(Res.NOTIFICATION_BAR_EXPAND_RES));
        if (expandIndicator.waitForExists(5L)) {
            expandIndicator.clickAndWaitForNewWindow();
        }

        UiObject quickPanel = device.findObject(new UiSelector().
                resourceId(Res.NOTIFICATION_QUICK_PANEL_RES));
        if (quickPanel.waitForExists(3L)) {
            Context context = testFramework.getInstrumentation().getContext();
            DisplayMetrics metrics = new DisplayMetrics();
            WindowManager windowManager = (WindowManager) context.
                    getSystemService(Context.WINDOW_SERVICE);
            windowManager.getDefaultDisplay().getMetrics(metrics);
            Display display = windowManager.getDefaultDisplay();
            Point point = new Point();
            display.getSize(point);
            int maxY = point.y;
            quickPanel.dragTo(0, maxY/2, 5);
        }
    }
}
