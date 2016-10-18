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

import com.android.devtools.systemimage.uitest.annotations.TestInfo;
import com.android.devtools.systemimage.uitest.framework.SystemImageTestFramework;
import com.android.devtools.systemimage.uitest.utils.AppLauncher;

import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.Timeout;
import org.junit.runner.RunWith;

import android.app.Instrumentation;
import android.support.test.runner.AndroidJUnit4;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiSelector;

import java.util.concurrent.TimeUnit;

/**
 * Test for adding a Google account.
 */
@RunWith(AndroidJUnit4.class)
public class AddGoogleAccountTest {
    @Rule
    public final SystemImageTestFramework testFramework = new SystemImageTestFramework();

    @Rule
    public Timeout globalTimeout = Timeout.seconds(60);

    /**
     * Verifies able to add a Google account using Contacts app.
     * <p>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p>
     * TR ID: C14581151
     * <p>
     *   <pre>
     *   Test Steps:
     *   1. Start the emulator.
     *   2. Open Contacts app.
     *   3. Tap on "Add Account"
     *   4. Tap on "Add Contact" and choose "Add Account"
     *   Verify:
     *   User is prompted to sign in to a Google Account.
     *   </pre>
     */
    @Test
    @TestInfo(id = "14581151")
    public void testAddAccountUsingContactsApp() throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();
        UiDevice mDevice = testFramework.getDevice();

        if (testFramework.getApi() > 19) {
            AppLauncher.launch(instrumentation, "Contacts");
            // Check if the app is running for the first time.
            UiObject checkingInfo =
                    mDevice.findObject(new UiSelector().textContains("Checking Info"));
            if (checkingInfo.exists()) {
                mDevice.pressBack();
            }
            AppLauncher.launch(instrumentation, "Contacts");
        } else {
            AppLauncher.launch(instrumentation, "People");
            // Check if the app is running for the first time.
            UiObject notNow = mDevice.findObject(new UiSelector().textContains("Not now"));
            if (notNow.exists()) {
                notNow.click();
            }
        }
        // Verification step requires sign in to a Google Account,
        // which requires Google API support. Test is irrelevant on API 24.
        if (testFramework.getApi() > 23 && testFramework.isGoogleApiImage()) {
            UiObject add_contact = mDevice.findObject(
                    new UiSelector().description("add new contact"));
            add_contact.clickAndWaitForNewWindow();
        } else {
            UiObject add_contact = mDevice.findObject(
                    new UiSelector().textContains("NEW CONTACT"));
            add_contact.waitForExists(TimeUnit.SECONDS.toMillis(5));
            add_contact.clickAndWaitForNewWindow();
        }
        mDevice.findObject(new UiSelector().textContains("ADD ACCOUNT")).click();
    }
}