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
import com.android.devtools.systemimage.uitest.framework.SystemImageTestFramework;
import com.android.devtools.systemimage.uitest.watchers.SettingsTestPopupWatcher;

import android.app.Instrumentation;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiObjectNotFoundException;
import android.support.test.uiautomator.UiScrollable;
import android.support.test.uiautomator.UiSelector;

import org.junit.Assert;

import java.util.concurrent.TimeUnit;

/**
 * Developer options manager.
 */
public class DeveloperOptionsManager {

    private DeveloperOptionsManager() {
        throw new AssertionError();
    }

    private static void enableOptions(Instrumentation instrumentation) throws Exception {
        UiDevice device = UiDevice.getInstance(instrumentation);
        SettingsUtil.clickAdvancedMenu(device);

        // Click "Build number"
        UiScrollable itemList =
                new UiScrollable(
                        new UiSelector().resourceIdMatches(Res.ABOUT_PHONE_LIST_CONTAINER_RES)
                );
        itemList.setAsVerticalList();

        final UiObject buildNumberLabel =
                itemList.getChildByText(
                        new UiSelector().className("android.widget.TextView"),
                        "Build number"
                );

        boolean hasBuildNumberLabel = new Wait(TimeUnit.MILLISECONDS.convert(
                10L, TimeUnit.SECONDS)).
                until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() {
                        return buildNumberLabel.waitForExists(10L);
                    }
                });

        Assert.assertTrue("Developer options could not be enabled.", hasBuildNumberLabel);

        // Currently, UiAutomator cannot catch toast messages (see b/26511336).
        // We simply repeat for 10 times without verification. Will improve if it causes flakiness.
        for (int i = 0; i < 10; i++) {
            buildNumberLabel.click();
        }
    }
    /**
     * Enables developer options.
     *
     * Version 1 for api <= 25
     *
     * @param testFramework see {
     *   @link android.devtools.systemimage.uitest.framework.SystemImageTestFramework() }
     * @throws Exception if it fails to find a UI widget.
     */
    public static void enableDeveloperOptions_v1(SystemImageTestFramework testFramework)
            throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();

        try {
            AppLauncher.launchPath(instrumentation, new String[]{"Settings", "About emulated device"});
        } catch (UiObjectNotFoundException e) {
            AppLauncher.launchPath(instrumentation, new String[]{"Settings", "About phone"});
        }

        enableOptions(instrumentation);
    }

    /**
     * Enables developer options.
     *
     * Version 2 for api 26, 27.
     *
     * @param testFramework see {
     *   @link android.devtools.systemimage.uitest.framework.SystemImageTestFramework() }
     * @throws Exception if it fails to find a UI widget.
     */
    public static void enableDeveloperOptions_v2(SystemImageTestFramework testFramework)
            throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();

        try {
            AppLauncher.launchPath(instrumentation, new String[]{"Settings", "System", "About emulated device"});
        } catch (UiObjectNotFoundException e) {
            AppLauncher.launchPath(instrumentation, new String[]{"Settings", "System", "About phone"});
        }

        enableOptions(instrumentation);
    }

    /**
     * Enables developer options.
     *
     * Version 3 for api >= 28.
     *
     * @param testFramework see {
     *   @link android.devtools.systemimage.uitest.framework.SystemImageTestFramework() }
     * @throws Exception if it fails to find a UI widget.
     */
    public static void enableDeveloperOptions_v3(SystemImageTestFramework testFramework)
            throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();

        try {
            AppLauncher.launchPath(instrumentation, new String[]{"Settings", "About emulated device"});
        } catch (UiObjectNotFoundException e) {
            AppLauncher.launchPath(instrumentation, new String[]{"Settings", "System", "About phone"});
        }

        enableOptions(instrumentation);
    }

    /**
     * Checks if the developer options is enabled.
     *
     * Version 1 for api <= 25
     *
     * @param testFramework see {
     *   @link android.devtools.systemimage.uitest.framework.SystemImageTestFramework() }
     * @return {@code true} if the developer options is enabled, or {@code false} otherwise.
     * @throws Exception is it fails to find a UI widget.
     */
    public static boolean isDeveloperOptionsEnabled_v1(SystemImageTestFramework testFramework) throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();
        final UiDevice device = UiDevice.getInstance(instrumentation);

        new SettingsTestPopupWatcher(device).checkForCondition();

        try {
            SettingsUtil.findItem(instrumentation, "Developer options");
            return true;
        } catch (UiObjectNotFoundException e) {
            return false;
        }
    }

    /**
     * Checks if the developer options is enabled.
     *
     * Version 2 for api >= 26
     *
     * @param testFramework see {
     *   @link android.devtools.systemimage.uitest.framework.SystemImageTestFramework() }
     * @return {@code true} if the developer options is enabled, or {@code false} otherwise.
     * @throws Exception is it fails to find a UI widget.
     */
    public static boolean isDeveloperOptionsEnabled_v2(SystemImageTestFramework testFramework) throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();
        final UiDevice device = UiDevice.getInstance(instrumentation);

        new SettingsTestPopupWatcher(device).checkForCondition();

        try {
            SettingsUtil.openItem(instrumentation, "System");
            SettingsUtil.clickAdvancedMenu(device);
            device.findObject(new UiSelector().text("Developer options")).click();
            return true;
        } catch (UiObjectNotFoundException e) {
            return false;
        }
    }
}
