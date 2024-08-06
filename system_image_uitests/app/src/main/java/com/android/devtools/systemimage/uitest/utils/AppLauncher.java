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
import androidx.test.uiautomator.UiDevice;
import androidx.test.uiautomator.UiObject;
import androidx.test.uiautomator.UiObjectNotFoundException;
import androidx.test.uiautomator.UiScrollable;
import androidx.test.uiautomator.UiSelector;
import android.util.Log;
import android.view.KeyEvent;

import java.util.Objects;

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
    public static boolean launch(Instrumentation instrumentation, String appName) throws Exception {
        Log.i(TAG, "Open " + appName);
        UiDevice device = UiDevice.getInstance(instrumentation);
        device.pressHome();

        final UiObject appsLabel = device.findObject(new UiSelector().descriptionContains("Apps"));

        UiObject scrollView = device.findObject(new UiSelector().resourceId("android:id/content"));
        int startY = new Wait().until(appsLabel::exists) ? appsLabel.getBounds().top : 1000;
        int endY = new Wait().until(scrollView::exists) ? scrollView.getBounds().top : 0;

        // Scroll to the end to open app drawer.
        device.drag(
                0,
                startY,
                0,
                endY,
                10);
        //  }

        // Attempt to scroll through the list twice, first vertically, and then horizontally.
        // If the target object cannot be found while scrolling, fling forward by a
        // maximum of 5 swipes. The combination of these techniques is intended to mediate
        // against any gesture-based failures, which can occur due to UI changes between APIs.

        final UiScrollable scrollable = new UiScrollable(new UiSelector().scrollable(true)).setAsVerticalList();
        final UiSelector appSelector = new UiSelector().text(appName);
        final UiObject appObject = device.findObject(appSelector);

        boolean appNameFound = false;
        if (new Wait().until(appObject::exists) && api < 22) {
            appObject.clickAndWaitForNewWindow();
            Log.i(TAG, "Opened app in first attempt");
        } else {
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
            if (api == 30 || api == 31) {
                throw new UiObjectNotFoundException("Catch due to known instability");
            }
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
            UiObject clearAllButton = device.findObject(
                    new UiSelector().resourceId(Res.DISMISS_TEST_RES));
            if (clearAllButton.waitForExists(3L)) {
                clearAllButton.clickAndWaitForNewWindow();
            }
            device.pressHome();
            device.drag(
                    0,
                    startY,
                    0,
                    endY,
                    10);

            if (!appObject.exists()) {
                if (api >= 29) {
                    device.pressKeyCode(KeyEvent.KEYCODE_A, KeyEvent.META_CTRL_ON);
                    final UiObject launcherDismiss = device.findObject(new UiSelector().
                            resourceId(Res.LAUNCHER_LIST_DISMISS_RES));
                    if (new Wait().until(launcherDismiss::exists)) {
                        launcherDismiss.clickAndWaitForNewWindow();
                    }
                } else {
                    device.pressHome();
                    final UiObject launcherList = api == 25 ?
                            device.findObject(new UiSelector().resourceId(
                                    Res.ALL_APPS_HANDLE_RES)) :
                            device.findObject(new UiSelector().resourceId(
                                    Res.LAUNCHER_LIST_CONTAINER_RES));
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

        if (!status && api == 31) {
            return launchPath_v2(instrumentation, appPath);
        }

        if (!status) {
            return false;
        }

        for (int i = 1; i < appPath.length && status; ++i) {
            status = false;
            Log.i(TAG, "Open " + appPath[i]);
            UiSelector regexSelector = new UiSelector().textMatches(appPath[i]);
            UiSelector textSelector = new UiSelector().textContains(appPath[i]);

            UiObject appByRegex = device.findObject(regexSelector);
            UiObject appByText = device.findObject(regexSelector);

            if (appByRegex.waitForExists(5L)) {
                appByRegex.clickAndWaitForNewWindow();
                status = true;
                continue;
            } else if (appByText.waitForExists(5L)) {
                appByText.clickAndWaitForNewWindow();
                status = true;
                continue;
            }

            try {
                UiScrollable scrollable = new UiScrollable(new UiSelector().scrollable(true));
                if (!scrollable.waitForExists(5L)) {
                    Log.i(TAG, "Scrollable object does not exist");
                    continue;
                } else if (!scrollable.isScrollable()) {
                    Log.i(TAG, "Scrollable cannot be scrolled");
                    continue;
                } else {
                    if (scrollable.scrollIntoView(regexSelector)) {
                        Log.i(TAG, "Scrolling to " + appPath[i] + " using regexSelector");
                        appByRegex.clickAndWaitForNewWindow();
                        status = true;
                        continue;
                    } else if (scrollable.scrollIntoView(textSelector)) {
                        Log.i(TAG, "Scrolling to " + appPath[i] + " using textSelector");
                        appByText.clickAndWaitForNewWindow();
                        status = true;
                        continue;
                    }
                }
                if (api == 31) {
                    return launchPath_v2(instrumentation, appPath);
                }
                Log.i(TAG, "Failed to scroll to " + appPath[i]);
                return false;
            } catch (UiObjectNotFoundException e) {
                Log.w(TAG, Objects.requireNonNull(e.getMessage()));
                Log.w(TAG, "Application " + appPath[i] + " could not be launched");
            }
        }

        if (firstAttempt && !status && api == 31) {
            return launchPath_v2(instrumentation, appPath);
        }

        return status;
    }

    /**
     * Launches a sequence of apps specified by the appPath array, specifically designed for API 31.
     * This method attempts to launch each app in the array in order, starting from the second app.
     * It uses a UiSelector to find a scrollable object with a specific resource ID, and then scrolls through
     * this object to find and click on each app. If an app cannot be found after scrolling through the entire list,
     * the method logs an error message and returns false.
     *
     * @param instrumentation the instrumentation instance used to interact with the UI
     * @param swipesLimit     the maximum number of swipes to attempt before giving up on scrolling to an app
     * @param appPath         an array of Strings where each String is the name of an app to launch
     * @return a boolean indicating whether the method was able to find and click on all the apps in the appPath array
     * @throws Exception if an error occurs while interacting with the UI
     */
    public static boolean launchPath_v2(Instrumentation instrumentation, Integer swipesLimit, String... appPath)
            throws Exception {
        final UiDevice device = UiDevice.getInstance(instrumentation);

        if (api != 31) {
            Log.i(TAG, "LaunchPath_v2 is only supported on API 31.");
            return false;
        }
        boolean status = launch(instrumentation, appPath[0]);

        if (!status) {
            Log.i(TAG, "Failed to launch " + appPath[0]);
            return false;
        }

        UiObject recyclerView = device.findObject(
                new UiSelector().resourceId(Res.ANDROID_SETTING_LIST_RES));

        if (!recyclerView.waitForExists(10000L)) {
            Log.i(TAG, "RecyclerView does not exist");
            return false;
        }

        int startX = recyclerView.getBounds().centerX();
        int startY = recyclerView.getBounds().bottom - 10;
        int endY = recyclerView.getBounds().top + 10;

        for (int i = 1; i < appPath.length; ++i) {
            status = false;
            Log.i(TAG, "Open " + appPath[i]);
            UiSelector regexSelector = new UiSelector().textMatches(appPath[i]);
            UiObject appByRegex = device.findObject(regexSelector);

            boolean canScrollMore = true;
            while (canScrollMore && swipesLimit-- > 0) {
                canScrollMore = device.swipe(startX, startY, startX, endY, 50);
                if (appByRegex.waitForExists(1L)) {
                    Log.i(TAG, "Scrolling to " + appPath[i] + " using regexSelector");
                    appByRegex.click();
                    appByRegex.waitUntilGone(5L);
                    status = true;
                    break;
                }
            }
            if (!status) {
                Log.i(TAG, "Failed to scroll to " + appPath[i]);
                startY = recyclerView.getBounds().top + 10;
                endY = recyclerView.getBounds().bottom - 10;
                device.swipe(startX, startY, startX, endY, 50);
                return false;
            }
        }

        return status;
    }

     /**
     * Launches application in path by launcher.
     *
     * @param instrumentation see {@link android.test.InstrumentationTestCase#getInstrumentation()
     *                        getInstrumentation}
     * @param appPath         the app path to launch
     * @throws UiObjectNotFoundException if it fails to find a UI object.
     */
    public static boolean launchPath_v2(Instrumentation instrumentation, String... appPath)
            throws Exception {
        return launchPath_v2(instrumentation, 100, appPath);
    }

    /**
     * Scrolls through a UiScrollable object until a UiObject with a specified text is found, then clicks on it.
     *
     * @param device     The UiDevice instance that represents an emulator or a connected device.
     * @param scrollable The UiScrollable object to scroll through.
     * @param appNames   The text of the UiObject to find and click on.
     * @return true if the UiObject with the specified text is found and clicked on, false otherwise.
     * @throws UiObjectNotFoundException if the UiObject with the specified text is not found.
     */
    public static boolean scrollAndClick(UiDevice device, UiScrollable scrollable, String... appNames) throws UiObjectNotFoundException {
        for (String appName : appNames) {
            UiSelector appSelector = new UiSelector().textMatches(appName);
            UiObject appByRegex = device.findObject(appSelector);

            scrollable.waitForExists(10000L);

            boolean appFound = scrollable.scrollIntoView(appSelector);
            if (appFound) {
                Log.i(TAG, "Scrolling to " + appName + " using regexSelector");
                appByRegex.click();
                appByRegex.waitUntilGone(5L);
            } else {
                Log.i(TAG, "Failed to scroll to " + appName);
                return false;
            }
        }
        return true;
    }
}
