/*
 * Copyright (c) 2020 The Android Open Source Project
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

package com.android.devtools.adbtestutils;

import android.app.Instrumentation;
import android.support.test.runner.AndroidJUnit4;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiSelector;
import android.util.Log;

import org.junit.Rule;
import org.junit.Test;
import org.junit.runner.RunWith;

/**
 * Test class for Android Settings page on Google API images.
 **/
@RunWith(AndroidJUnit4.class)
public class AdbTestUtils {
    @Rule
    public final Framework testFramework = new Framework();
    private final Instrumentation instrumentation = testFramework.getInstrumentation();
    private final UiDevice device = UiDevice.getInstance(instrumentation);
    private final static String TAG = "ADBWireless";

    @Test
    public void openPairCode() throws Exception {
        AppLauncher.launchPath(instrumentation,
                true,
                "Settings",
                "About phone",
                "Build number");

        UiSelector buildNumberLable = new UiSelector().textContains("Build number");
        UiObject buildNumber = device.findObject(buildNumberLable);
        for ( int i=0; i<10; i++) {
            buildNumber.click();
        }

        AppLauncher.launchPath(instrumentation,
            true,
            "Settings",
            "System",
            "Advanced",
            "Developer options",
            "Wireless debugging");

        final UiObject wirelessSwitch =
            device.findObject(new UiSelector().resourceId("com.android.settings:id/switch_widget"));
        boolean status = wirelessSwitch.isChecked();
        if (!status) {
            wirelessSwitch.clickAndWaitForNewWindow();

            final UiObject allowCheck =
                device.findObject(new UiSelector().resourceId("android:id/alwaysUse"));
            if (allowCheck.waitForExists(5L)) {
                allowCheck.click();

                final UiObject allowButton =
                    device.findObject(new UiSelector().resourceId("android:id/button1"));
                allowButton.click();
            }
        }

        final UiObject ipPort =
            device
            .findObject(new UiSelector().resourceId("com.android.settings:id/recycler_view"))
            .getChild(new UiSelector().index(1));
        String ip =
            ipPort.getChild(new UiSelector().index(0)).getChild(new UiSelector().index(1)).getText();

        final UiObject pair = device.findObject(new UiSelector().text("Pair device with pairing code"));
        pair.clickAndWaitForNewWindow();

        final UiObject pairCodeLayout =
            device
            .findObject(new UiSelector().resourceId("com.android.settings:id/l_pairing_six_digit"))
            .getChild(new UiSelector().index(0));
        String pairCode = pairCodeLayout.getChild(new UiSelector().index(1)).getText();
        String ipPair = pairCodeLayout.getChild(new UiSelector().index(3)).getText();

        Log.i(TAG, "connect ip " + ip);
        Log.i(TAG, "pair ip " + ipPair);
        Log.i(TAG, "pair code " + pairCode);
    }
}
