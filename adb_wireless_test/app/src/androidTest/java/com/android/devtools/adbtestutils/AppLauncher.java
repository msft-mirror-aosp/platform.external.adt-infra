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
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiObjectNotFoundException;
import android.support.test.uiautomator.UiScrollable;
import android.support.test.uiautomator.UiSelector;
import android.util.Log;
import android.view.KeyEvent;

/**
 * Application launcher.
 **/
class AppLauncher {
    private static final String TAG = "AppLauncher";

    private AppLauncher() {
        throw new AssertionError();
    }

    /**
     * Launches application by launcher.
     *
     * @param instrumentation see {@link android.test.InstrumentationTestCase#getInstrumentation()
     *                        getInstrumentation}
     * @param appName         the app name to launch
     * @throws UiObjectNotFoundException if it fails to find a UI object.
     */
    private static boolean launch(Instrumentation instrumentation, String appName) throws Exception  {
        Log.i(TAG, "Open "+ appName);
        UiDevice device = UiDevice.getInstance(instrumentation);
        device.pressHome();
        device.pressKeyCode(KeyEvent.KEYCODE_A, KeyEvent.META_CTRL_ON);

        final UiScrollable scrollable = new UiScrollable(new UiSelector().scrollable(true)).setAsVerticalList();
        scrollable.scrollToEnd(5);

        final UiSelector appSelector = new UiSelector().text(appName);
        final UiObject appObject = device.findObject(appSelector);

        boolean appNameFound = new Wait().until(appObject::exists);
        if (appNameFound) {
            appObject.clickAndWaitForNewWindow();
            Log.i(TAG, "Opened app in second attempt");
        }

        return appNameFound;
    }

    /**
     * Launches application in path by launcher.
     *
     * @param instrumentation see {@link android.test.InstrumentationTestCase#getInstrumentation()
     *                        getInstrumentation}
     * @param appPath         the app path to launch
     * @throws UiObjectNotFoundException if it fails to find a UI object.
     **/
    public static boolean launchPath(Instrumentation instrumentation, boolean firstAttempt, String... appPath)
            throws Exception {
        final UiDevice device = UiDevice.getInstance(instrumentation);
        boolean status = launch(instrumentation, appPath[0]);

        if (!status) return false;

        for (int i = 1; i < appPath.length && status; ++i) {
            status = false;
            Log.i(TAG, "Open "+appPath[i]);
            UiSelector regexSelector = new UiSelector().textMatches(appPath[i]);
            UiSelector textSelector = new UiSelector().textContains(appPath[i]);

            UiObject target = device.findObject(regexSelector);
            try {
                UiScrollable scrollable = new UiScrollable(new UiSelector().scrollable(true));
                boolean isFound = scrollable.scrollIntoView(regexSelector);
                if (!isFound) {
                    target = device.findObject(textSelector);
                    scrollable.scrollIntoView(textSelector);
                }
                target.clickAndWaitForNewWindow();
                status = true;
            }
            catch (UiObjectNotFoundException e) {
                Log.w(TAG, e.getMessage());
                if (target.exists()) {
                    target.clickAndWaitForNewWindow();
                    status = true;
                }
            }
        }

        if (firstAttempt && !status) {
            return launchPath(instrumentation, false, appPath);
        }
        return status;
    }
}
