/*
 * Copyright (c) 2018 The Android Open Source Project
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

package com.android.devtools.systemimage.uitest.wear.api28;

import android.app.Instrumentation;
import android.support.test.runner.AndroidJUnit4;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiObjectNotFoundException;
import android.support.test.uiautomator.UiScrollable;
import android.support.test.uiautomator.UiSelector;

import com.android.devtools.systemimage.uitest.annotations.TestInfo;
import com.android.devtools.systemimage.uitest.common.Res;
import com.android.devtools.systemimage.uitest.framework.SystemImageTestFramework;

import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.Timeout;
import org.junit.runner.RunWith;

import static org.junit.Assert.assertTrue;

/**
 * Test class for Settings page on Android Wear API images.
 */
@RunWith(AndroidJUnit4.class)
public class SettingsTest {
    @Rule
    public final SystemImageTestFramework testFramework = new SystemImageTestFramework();

    private Instrumentation instrumentation = testFramework.getInstrumentation();
    private UiDevice device = UiDevice.getInstance(instrumentation);

    private int MAX_BRIGHTNESS = 5;

    private final static String TAG = "SettingsTest";

    @Rule
    public Timeout globalTimeout = Timeout.seconds(120);

    /**
     * Verifies that the brightness of the watch can be adjusted.
     * <p>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p>
     * TT ID: f83bf063-2a8c-4d1b-808b-20fd76933135
     * <p>
     *   <pre>
     *   1. Start the Android Wear emulator.
     *   2. Open Settings > Display > Adjust brightness.
     *   3. Record the original brightness setting.
     *   4. Change the original brightness value.
     *   5. Change the new brightness value.
     *   6. Reset the original brightness value.
     *   Verify:
     *   1. The original brightness was changed.
     *   2. The new brightness was changed.
     *   3. The original brightness was restored.
     *   </pre>
     */
    @Test
    @TestInfo(id = "f83bf063-2a8c-4d1b-808b-20fd76933135")
    public void adjustBrightness() throws Exception {

        device.pressHome();
        device.pressBack();

        UiScrollable wheelList = new UiScrollable(new UiSelector().resourceId(Res.WEAR_LAUNCHER));
        wheelList.setAsVerticalList();

        UiSelector settingsOption = new UiSelector().text("Settings");
        if (wheelList.scrollIntoView(settingsOption)) {
            device.findObject(settingsOption).clickAndWaitForNewWindow();
        }

        UiScrollable itemList = new UiScrollable(new UiSelector().resourceId(Res.ANDROID_LIST_RES).
                packageName("com.google.android.apps.wearable.settings"));
        itemList.setAsVerticalList();

        UiSelector displayOption = new UiSelector().text("Display");
        if (itemList.scrollIntoView(displayOption)) {
            device.findObject(displayOption).clickAndWaitForNewWindow();
        }

        String originalBrightness = getBrightness();
        if (originalBrightness.equals("Automatic")) {
            setBrightness("1");
        } else {
            int level = Integer.parseInt(originalBrightness);
            if (level == MAX_BRIGHTNESS) {
                setBrightness("1");
            } else {
                setBrightness(Integer.toString(level+1));
            }
        }
        String newBrightness = getBrightness();
        assertTrue("Original brightness has not been changed",
                !newBrightness.equals(originalBrightness));

        int level = Integer.parseInt(newBrightness);
        if (level == MAX_BRIGHTNESS) {
            setBrightness("1");
        } else {
            setBrightness(Integer.toString(level+1));
        }
        assertTrue("New brightness has not been changed",
                !newBrightness.equals(getBrightness()));

        setBrightness(originalBrightness);
        assertTrue("Original brightness has not been restored",
                originalBrightness.equals(getBrightness()));
        device.pressHome();
    }

    // Open the adjust brightness setting.
    private void openBrightness() throws UiObjectNotFoundException {
        UiScrollable itemList = new UiScrollable(new UiSelector().resourceId(Res.ANDROID_LIST_RES).
                packageName("com.google.android.apps.wearable.settings"));
        itemList.setAsVerticalList();

        UiSelector adjustBrightnessOption = new UiSelector().text("Adjust brightness");

        if (itemList.scrollIntoView(adjustBrightnessOption)) {
            device.findObject(adjustBrightnessOption).clickAndWaitForNewWindow();
        }
    }

    // Get the brightness level.
    private String getBrightness() throws UiObjectNotFoundException {
        openBrightness();

        for (int i = 1; i <= MAX_BRIGHTNESS; i++) {
            UiScrollable itemList = new UiScrollable(new UiSelector().resourceId(Res.ANDROID_SELECT_LIST).
                    packageName("com.google.android.apps.wearable.settings"));
            itemList.setAsVerticalList();

            UiSelector brightnessOption = new UiSelector()
                    .className("android.widget.CheckedTextView").text(Integer.toString(i));

            if (itemList.scrollIntoView(brightnessOption)) {
                UiObject brightness = device.findObject(brightnessOption);
                if (brightness.waitForExists(3L) && brightness.isChecked()) {
                    return brightness.getText();
                }
            }
        }
        return "Automatic";
    }

    // Set the brightness to the level provided.
    private void setBrightness(String level)
            throws UiObjectNotFoundException {

        UiScrollable itemList = new UiScrollable(new UiSelector().resourceId(Res.ANDROID_SELECT_LIST).
                packageName("com.google.android.apps.wearable.settings"));
        itemList.setAsVerticalList();

        UiSelector brightnessOption = new UiSelector()
                .className("android.widget.CheckedTextView").text(level);

        if (itemList.scrollIntoView(brightnessOption)) {
            UiObject brightness = device.findObject(brightnessOption);
            if (brightness.waitForExists(3L)) {
                brightness.clickAndWaitForNewWindow();
            }
        }
    }
}