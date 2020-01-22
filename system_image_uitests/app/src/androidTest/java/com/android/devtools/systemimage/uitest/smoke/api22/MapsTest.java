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
package com.android.devtools.systemimage.uitest.smoke.api22;

import android.app.Instrumentation;
import android.support.test.runner.AndroidJUnit4;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiSelector;
import android.view.KeyEvent;

import com.android.devtools.systemimage.uitest.annotations.TestInfo;
import com.android.devtools.systemimage.uitest.common.Res;
import com.android.devtools.systemimage.uitest.framework.SystemImageTestFramework;
import com.android.devtools.systemimage.uitest.utils.AppLauncher;
import com.android.devtools.systemimage.uitest.utils.Wait;
import com.android.devtools.systemimage.uitest.watchers.watcher;

import org.junit.Assert;
import org.junit.Rule;
import org.junit.Test;
import org.junit.runner.RunWith;


/**
 * Sanity test for Maps App
 */

@RunWith(AndroidJUnit4.class)
public class MapsTest {
    private static final String QUERY_STRING = "San Francisco";

    @Rule
    public final SystemImageTestFramework testFramework = new SystemImageTestFramework();

    /**
     * Verify the functionality of navigation overview in Google Maps app.
     * <p>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p>
     * TT ID: 4578f63f-7d2e-4e5e-a4e0-0ce2ae67982e
     * <p>
     * <pre>
     *   Test Steps:
     *   1. Launch emulator avd.
     *   2. Open Maps app.
     *   3. Accept terms and condition.
     *   4. Tap on search bar.
     *   5. Enter search query, "San Francisco", select it from the auto fill results.
     *   6. "San Francisco" location card opens.
     *   7. Select "San Francisco".
     *   8. Tap on the Route icon.
     *   Verify:
     *   1. Map points to San Francisco location.
     *   2. Navigation overview is displayed.
     *   </pre>
     */
    @Test
    @TestInfo(id = "4578f63f-7d2e-4e5e-a4e0-0ce2ae67982e")
    public void testMapsApp() throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();
        UiDevice mDevice = testFramework.getDevice();

        if (testFramework.isGoogleApiImage()) {
            AppLauncher.launch(instrumentation, "Maps");

            final UiObject acceptButton = mDevice.findObject(new UiSelector()
                .resourceIdMatches(Res.GOOGLE_ACCEPT_BUTTON)
            );
            if (acceptButton.waitForExists(3000)) {
                acceptButton.click();
            }

            new watcher(mDevice, Res.MAPS_WATCHER_PATTERN).checkForCondition();

            final UiObject searchTextClear = mDevice.findObject(new UiSelector()
                .resourceIdMatches(Res.SEARCH_TEXT_CLEAR));
            if (searchTextClear.waitForExists(3000)) {
                searchTextClear.click();
            }

            final UiObject searchEditText = mDevice.findObject(new UiSelector()
                .resourceIdMatches(Res.SEARCH_TEXT_BOX)
            );
            if (searchEditText.waitForExists(3000)) {
                searchEditText.click();
                // This is required because the setText method on searchEditText was failing
                mDevice.pressKeyCode(KeyEvent.KEYCODE_S);
                mDevice.pressKeyCode(KeyEvent.KEYCODE_A);
                mDevice.pressKeyCode(KeyEvent.KEYCODE_N);
                mDevice.pressKeyCode(KeyEvent.KEYCODE_SPACE);
                mDevice.pressKeyCode(KeyEvent.KEYCODE_F);
                mDevice.pressKeyCode(KeyEvent.KEYCODE_R);
                mDevice.pressKeyCode(KeyEvent.KEYCODE_A);
                mDevice.pressKeyCode(KeyEvent.KEYCODE_N);
                mDevice.pressKeyCode(KeyEvent.KEYCODE_C);
                mDevice.pressKeyCode(KeyEvent.KEYCODE_I);
                mDevice.pressKeyCode(KeyEvent.KEYCODE_S);
                mDevice.pressKeyCode(KeyEvent.KEYCODE_C);
                mDevice.pressKeyCode(KeyEvent.KEYCODE_O);
            }

            final UiObject locationString = mDevice.findObject(new UiSelector().text(QUERY_STRING));
            Assert.assertTrue("Selected location " + QUERY_STRING + " not found.",
                new Wait().until(locationString::exists));
            locationString.clickAndWaitForNewWindow();

            final UiObject destinationLabelText = mDevice.findObject(new UiSelector()
                .text(QUERY_STRING)
            );
            boolean hasSearchText = new Wait().until(destinationLabelText::exists);
            if (hasSearchText) {
                Assert.assertTrue("Search string " + QUERY_STRING + " not found.",
                    destinationLabelText.getText().contains(QUERY_STRING));
            }

            // Verify that the route icon exists and clicking on it opens the directions page.
            UiObject routeIcon = mDevice.findObject(
                new UiSelector().descriptionMatches(".*Route.*"));
            Assert.assertTrue("Could not find route icon",
                routeIcon.waitForExists(3000));
            routeIcon.clickAndWaitForNewWindow();

            // Verify that the query string is pre filled in the destination field.
            UiObject destination = mDevice.findObject(new UiSelector().textContains(QUERY_STRING));
            Assert.assertTrue("Could not find destination icon",
                destination.waitForExists(3000));

            for (int i = 0; i < 5; i++) {
                mDevice.pressBack();
            }
        }
    }
}