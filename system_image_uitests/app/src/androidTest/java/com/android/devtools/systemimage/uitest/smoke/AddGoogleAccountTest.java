/*
 * Copyright (C) 2016 The Android Open Source Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.android.devtools.systemimage.uitest.smoke;

import com.android.devtools.systemimage.uitest.framework.AbstractSystemImageTestCase;
import com.android.devtools.systemimage.uitest.utils.AppLauncher;
import com.android.devtools.systemimage.uitest.utils.TestUtils;

import android.app.Instrumentation;
import android.support.test.filters.SdkSuppress;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiSelector;

/**
 * Test suite for adding a Google account.
 */
@SdkSuppress(minSdkVersion = 18)
public class AddGoogleAccountTest extends AbstractSystemImageTestCase {

    private static final String TAG = AddGoogleAccountTest.class.getName();

    @Override
    public void setUp() throws Exception {
        super.setUp();
    }

    @Override
    public void tearDown() throws Exception {
        super.tearDown();
    }

    /**
     * Verifies able to add a Google account using Contacts app.
     * <p>
     * Test Bug ID: b/28053652
     */
    public void testAddAccountUsingContactsApp() throws Exception {
        Instrumentation instrumentation = getInstrumentation();
        UiDevice device = UiDevice.getInstance(instrumentation);
        TestUtils.disableHomeOverlayItems(device);
        TestUtils.disableAppsOverlayItems(device);
        if (TestUtils.getApiLevel() > 19) {
            AppLauncher.launch(instrumentation, "Contacts");
            // Check if the app is running for the first time.
            UiObject checkingInfo = device.findObject(new UiSelector().textContains(
                    "Checking Info"));
            if (checkingInfo.exists()) {
                device.pressBack();
            }
            AppLauncher.launch(instrumentation, "Contacts");
        } else {
            AppLauncher.launch(instrumentation, "People");
            // Check if the app is running for the first time.
            UiObject notNow = device.findObject(new UiSelector().textContains("Not now"));
            if (notNow.exists()) {
                notNow.click();
            }
        }
        device.findObject(
                new UiSelector().textContains("NEW CONTACT")).clickAndWaitForNewWindow();
        device.findObject(new UiSelector().textContains("ADD ACCOUNT")).click();
    }
}