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

/**
 * Application launcher.
 */
public class AppLauncher {

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
        device.findObject(new UiSelector().descriptionContains("Apps")).clickAndWaitForNewWindow();
        UiScrollable appList =
                new UiScrollable(
                        new UiSelector().resourceIdMatches(Res.LAUNCHER_LIST_CONTAINER_RES)
                );

        // Note that the direction of scrolling, even the res-id could change with future Android
        // releases. We may need a check here to determine the launcher and res-id used to decide
        // what appropriate gestures to perform.
        UiObject app;
        try {
            appList.setAsVerticalList();
            app = appList.getChildByText(
                    new UiSelector().className("android.widget.TextView"),
                    appName);
        } catch (UiObjectNotFoundException e) {
            appList.setAsHorizontalList();
            app = appList.getChildByText(
                    new UiSelector().className("android.widget.TextView"),
                    appName);
        }
        app.clickAndWaitForNewWindow();
    }
}
