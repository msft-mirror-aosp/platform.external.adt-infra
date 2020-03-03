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
import com.android.devtools.systemimage.uitest.watchers.watcher;

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
 */
public class AppLauncher {
    private final static String TAG = "AppLauncher";

    private AppLauncher() {
        throw new AssertionError();
    }

    private static final int api = SystemUtil.getApiLevel();

    /**
     * Launches application by launcher.
     *
     * @param instrumentation see {@link android.test.InstrumentationTestCase#getInstrumentation()
     *                        getInstrumentation}
     * @param appName         the app name to launch
     * @throws UiObjectNotFoundException if it fails to find a UI object.
     */
    public static boolean launch(Instrumentation instrumentation, String appName) throws Exception  {
        Log.i(TAG, "Open "+ appName);
        UiDevice device = UiDevice.getInstance(instrumentation);
        device.pressHome();

        final UiObject appsLabel = device.findObject(new UiSelector().descriptionContains("Apps"));

        UiObject scrollView = device.findObject(new UiSelector().resourceId("android:id/content"));
        // Scroll to the end to open app drawer.
        device.drag(
                0,
                appsLabel.getBounds().top,
                0,
                scrollView.getBounds().top,
                10);

        // Attempt to scroll through the list twice, first vertically, and then horizontally.
        // If the target object cannot be found while scrolling, fling forward by a
        // maximum of 5 swipes. The combination of these techniques is intended to mediate
        // against any gesture-based failures, which can occur due to UI changes between APIs.

        final UiScrollable scrollable = new UiScrollable(new UiSelector().scrollable(true)).setAsVerticalList();
        final UiSelector appSelector = new UiSelector().text(appName);
        final UiObject appObject = device.findObject(appSelector);

        boolean appNameFound = false;
        if (new Wait().until(appObject::exists) && (api < 22 || api > 24)) {
            appObject.clickAndWaitForNewWindow();
            Log.i(TAG, "Opened app in first attempt");
        }
        else {
            if (api >= 18 && api <= 24 ) {
                device.pressHome();
                final UiObject launcherIcon = device.findObject(new UiSelector().
                        className("android.widget.TextView").
                        packageName(device.getLauncherPackageName()).
                        description("Apps")
                );
                if (new Wait().until(launcherIcon::exists)) {
                    launcherIcon.clickAndWaitForNewWindow();
                    new watcher(device, Res.APP_WATCHER_PATTERN).checkForCondition();
                }
            }
            try {
                appNameFound = new Wait().until(appObject::exists);
                if (!appNameFound) {
                    scrollable.setAsVerticalList();
                    appNameFound = new Wait().until(() -> scrollable.scrollIntoView(appSelector));

                    if (!appNameFound) {
                        scrollable.setAsHorizontalList();
                        appNameFound = new Wait().until(() -> scrollable.scrollIntoView(appSelector));
                    }
                }
            } catch (UiObjectNotFoundException e) {
                device.pressHome();
                device.drag(
                        0,
                        appsLabel.getBounds().top,
                        0,
                        scrollView.getBounds().top,
                        10);

                if (!appObject.exists()) {
                    if (api >= 28) {
                        device.pressKeyCode(KeyEvent.KEYCODE_A, KeyEvent.META_CTRL_ON);
                        final UiObject launcherDismiss = device.findObject(new UiSelector().
                                resourceId(Res.LAUNCHER_LIST_DISMISS_RES));
                        if (new Wait().until(launcherDismiss::exists)) {
                            launcherDismiss.clickAndWaitForNewWindow();
                        }
                    } else {
                        final UiObject launcherList = device.findObject(new UiSelector().
                                resourceId(Res.LAUNCHER_LIST_CONTAINER_RES));
                        boolean launcherListFound = new Wait().until(launcherList::exists);
                        if (launcherListFound) {
                            launcherList.clickAndWaitForNewWindow();
                        } else if (scrollable.exists()) {
                            scrollable.flingForward();
                        }
                    }
                }
                appNameFound = new Wait().until(appObject::exists);
            }

            if (appNameFound) {
                appObject.clickAndWaitForNewWindow();
                Log.i(TAG, "Opened app in second attempt");
            }
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
     */
    public static boolean launchPath(Instrumentation instrumentation, boolean firstAttempt, String... appPath)
            throws Exception {
        final UiDevice device = UiDevice.getInstance(instrumentation);
        boolean status = launch(instrumentation, appPath[0]);

        if ( !status ) return false;

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

        if ( firstAttempt && !status ) {
            return launchPath(instrumentation, false, appPath);
        }
        return status;
    }
}