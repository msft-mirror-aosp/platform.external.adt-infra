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

package com.android.devtools.systemimage.uitest.smoke.api32;

import android.app.Instrumentation;
import androidx.test.runner.AndroidJUnit4;
import androidx.test.uiautomator.UiDevice;
import androidx.test.uiautomator.UiObject;
import androidx.test.uiautomator.UiSelector;

import com.android.devtools.systemimage.uitest.annotations.TestInfo;
import com.android.devtools.systemimage.uitest.common.Res;
import com.android.devtools.systemimage.uitest.framework.SystemImageTestFramework;
import com.android.devtools.systemimage.uitest.utils.AppLauncher;
import com.android.devtools.systemimage.uitest.utils.Wait;
import com.android.devtools.systemimage.uitest.watchers.watcher;

import org.junit.Ignore;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.Timeout;
import org.junit.runner.RunWith;
import static org.junit.Assert.assertTrue;

/**
 * Test for adding a Google account.
 */
@RunWith(AndroidJUnit4.class)
public class AddGoogleAccountTest {
    @Rule
    public final SystemImageTestFramework testFramework = new SystemImageTestFramework();

    @Rule
    public Timeout globalTimeout = Timeout.seconds(120);

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
     *   Verify:
     *   User is prompted to sign in to a Google Account.
     *   </pre>
     */
    @Test
    @Ignore("Covered by FAT")
    public void testAddAccountUsingContactsApp() throws Exception {
        final Instrumentation instrumentation = testFramework.getInstrumentation();
        final UiDevice mDevice = testFramework.getDevice();

        AppLauncher.launch(instrumentation, "Contacts");
        // Check if the app is running for the first time.
        UiObject checkingInfo =
                mDevice.findObject(new UiSelector().textContains("Checking Info"));
        if (checkingInfo.exists()) {
            mDevice.pressBack();
        }
        AppLauncher.launch(instrumentation, "Contacts");

        UiObject addAccount = mDevice.findObject(
                new UiSelector().resourceId((Res.ADD_NEW_CONTACT)));

        boolean isFound = addAccount.waitForExists(5L);
        if (isFound) {
            addAccount.clickAndWaitForNewWindow();
        }

        UiObject signInHeader = mDevice.findObject(
                new UiSelector().textMatches(("(?i)sign in(?-i)")).resourceId("headingText"));
        boolean isSignInPage = signInHeader.waitForExists(1000);

        UiObject createNewContact = mDevice.findObject(
                new UiSelector().text("Create new contact"));

        boolean isNewContactsPage = false;

        if (!isSignInPage) {
            new watcher(mDevice, Res.ADD_GOOGLE_ACC_WATCHER_PATTERN).checkForCondition();
            isNewContactsPage = createNewContact.waitForExists(1000);
        }

        assertTrue("Add Google account page not found",
                isSignInPage || isNewContactsPage);
    }
}
