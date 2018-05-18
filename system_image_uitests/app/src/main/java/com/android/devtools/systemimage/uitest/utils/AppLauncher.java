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

import android.app.Instrumentation;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiObjectNotFoundException;
import android.support.test.uiautomator.UiScrollable;
import android.support.test.uiautomator.UiSelector;
import android.util.Log;

/**
 * Application launcher.
 */
public class AppLauncher {
    private final static String TAG = "AppLauncher";

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
    public static void launch(Instrumentation instrumentation, String appName)
            throws UiObjectNotFoundException {
        UiDevice device = UiDevice.getInstance(instrumentation);
        device.pressHome();

        boolean appsLabelFound = false;
        boolean appNameFound;
        UiScrollable scrollable = new UiScrollable(new UiSelector().scrollable(true));
        UiSelector textSelector = new UiSelector().text(appName);
        UiObject app = device.findObject(textSelector);
        final UiObject appsLabel = device.findObject(new UiSelector().descriptionContains("Apps"));

        try {
            appsLabelFound = new Wait().until(new Wait.ExpectedCondition() {
                @Override
                public boolean isTrue() {
                    return appsLabel.exists();
                }
            });
        } catch(Exception error) {
            Log.e(TAG, error.getMessage());
            Log.e(TAG,"Launch: Apps label not found on first attempt");
        }

        if (appsLabelFound) {
            device.findObject(new UiSelector().descriptionContains("Apps")).clickAndWaitForNewWindow();
        }

        // Attempt to scroll through the list twice, first vertically, and then horizontally.
        // If the target object cannot be found while scrolling, fling forward by a
        // maximum of 5 swipes. The combination of these techniques is intended to mediate
        // against any gesture-based failures, which can occur due to UI changes between APIs.
        try {
            scrollable.setAsVerticalList();
            appNameFound = scrollable.scrollIntoView(textSelector);
            if (!appNameFound) {
                scrollable.setAsHorizontalList();
                appNameFound = scrollable.scrollIntoView(textSelector);
            }
        } catch (UiObjectNotFoundException e) {
            device.pressHome();
            try {
                appsLabelFound = new Wait().until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() {
                        return appsLabel.exists();
                    }
                });
            } catch(Exception error) {
                Log.e(TAG, error.getMessage());
                Log.e(TAG,"Launch: Apps label not found on second attempt");
            }

            int swipes = 0;
            while (!app.exists() && swipes < 5) {
                scrollable.flingForward();
                swipes++;
            }
            appNameFound = app.exists();
        }
        if (appNameFound) {
            app.clickAndWaitForNewWindow();
        }
    }

    /**
     * Launches application in a specific path.
     *
     * @param instrumentation see {@link android.test.InstrumentationTestCase#getInstrumentation()
     *                        getInstrumentation}
     * @param appPath         the app path to launch
     * @throws UiObjectNotFoundException if it fails to find a UI object.
     */
    public static void launchPath(Instrumentation instrumentation, String... appPath)
            throws UiObjectNotFoundException {
        final UiDevice device = UiDevice.getInstance(instrumentation);
        launch(instrumentation, appPath[0]);

        for (int i = 1; i < appPath.length; ++i) {
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
            }
            catch (UiObjectNotFoundException e) {
                Log.e(TAG, e.getMessage());
            }
            target.clickAndWaitForNewWindow();
        }
    }
}