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

package com.android.devtools.systemimage.uitest.utils.api21;

import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiSelector;

import java.util.concurrent.TimeUnit;

import static org.junit.Assert.assertTrue;

/**
 * Test for app interactions.
 */
public class AppTestUtils {
    /**
     * Helper method to set a homepage.  Homepage vararg optionally takes 2 arguments,
     * the homepage type (ie. "Other", "Default page", etc.), and the target website url.
     * Note that a selection of "Default page" would not require a url to be given.
     */
    public static void setHomePage(UiDevice device, String ...homepage) throws Exception {
        device.pressMenu();

        UiObject settings = device.findObject(new UiSelector().text("Settings"));
        settings.waitForExists(TimeUnit.SECONDS.toMillis(5));
        settings.clickAndWaitForNewWindow();

        UiObject general = device.findObject(new UiSelector().text("General"));
        general.waitForExists(TimeUnit.SECONDS.toMillis(5));
        general.clickAndWaitForNewWindow();

        UiObject setHomepage = device.findObject(new UiSelector().text("Set homepage"));
        setHomepage.waitForExists(TimeUnit.SECONDS.toMillis(5));
        setHomepage.clickAndWaitForNewWindow();

        UiObject type = device.findObject(new UiSelector().text(homepage[0]));
        type.waitForExists(TimeUnit.SECONDS.toMillis(5));
        type.clickAndWaitForNewWindow();

        UiObject textField = device.findObject(
                new UiSelector().className("android.widget.EditText").
                        packageName("com.android.browser"));
        textField.click();
        textField.clearTextField();
        textField.setText(homepage[1]);

        UiObject ok = device.findObject(new UiSelector().text("OK"));
        ok.waitForExists(TimeUnit.SECONDS.toMillis(5));
        ok.clickAndWaitForNewWindow();
    }
}
