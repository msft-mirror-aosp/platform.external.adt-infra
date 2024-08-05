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
import com.android.devtools.systemimage.uitest.watchers.watcher;

import android.app.Instrumentation;
import androidx.test.uiautomator.UiDevice;
import androidx.test.uiautomator.UiObject;
import androidx.test.uiautomator.UiObjectNotFoundException;
import androidx.test.uiautomator.UiScrollable;
import androidx.test.uiautomator.UiSelector;

import org.junit.Assert;

import java.util.concurrent.TimeUnit;


/**
 * Developer options manager.
 */
public class DeveloperOptionsManager {

    private DeveloperOptionsManager() {
        throw new AssertionError();
    }


    /**
     * Interface for defining navigation strategies.
     */
    public interface NavigationStrategy {
        /**
         * Navigate to the target UiObject.
         *
         * @param device the UiDevice instance.
         * @param target the target UiObject to navigate to.
         * @throws UiObjectNotFoundException if the target UiObject is not found.
         */
        void navigate(UiDevice device, UiObject target) throws UiObjectNotFoundException;
    }


    /**
     * Implementation of NavigationStrategy that uses scrolling.
     */
    public static class ScrollNavigationStrategy implements NavigationStrategy {
        /**
         * Scroll to the target UiObject.
         *
         * @param device the UiDevice instance.
         * @param target the target UiObject to scroll to.
         * @throws UiObjectNotFoundException if the target UiObject is not found.
         */
        @Override
        public void navigate(UiDevice device, UiObject target) throws UiObjectNotFoundException {
            UiScrollable itemList = new UiScrollable(new UiSelector().resourceIdMatches(Res.ABOUT_PHONE_LIST_CONTAINER_RES));
            itemList.setAsVerticalList();
            itemList.scrollIntoView(target);
        }
    }


    /**
     * Implementation of NavigationStrategy that uses swiping.
     */
    public static class SwipeNavigationStrategy implements NavigationStrategy {
        /**
         * Swipe to the target UiObject.
         *
         * @param device the UiDevice instance.
         * @param target the target UiObject to swipe to.
         * @throws UiObjectNotFoundException if the target UiObject is not found.
         */
        @Override
        public void navigate(UiDevice device, UiObject target) throws UiObjectNotFoundException {
            while (!target.exists()) {
                device.swipe(device.getDisplayWidth() / 2, device.getDisplayHeight() / 2,
                        device.getDisplayWidth() / 2, 0, 100);
            }
        }
    }


    /**
     * Enables developer options using the default ScrollNavigationStrategy.
     *
     * @param instrumentation the Instrumentation instance.
     * @throws Exception if an error occurs during the operation.
     */
    public static void enableOptions(Instrumentation instrumentation) throws Exception {
        enableOptions(instrumentation, new ScrollNavigationStrategy(), true);
    }


    /**
     * Enables developer options using a specified NavigationStrategy.
     *
     * @param instrumentation the Instrumentation instance.
     * @param strategy the NavigationStrategy to use for navigation.
     *                 The strategy is used to navigate to the "Build number" label.
     *                 The default strategy is ScrollNavigationStrategy.
     * @param hasAdvancedMenu {@code true} if the device has an advanced menu, or {@code false} otherwise.
     * @throws Exception if an error occurs during the operation.
     */
    public static void enableOptions(Instrumentation instrumentation, NavigationStrategy strategy, boolean hasAdvancedMenu) throws Exception {
        UiDevice device = UiDevice.getInstance(instrumentation);
        if (hasAdvancedMenu) {
            SettingsUtil.clickAdvancedMenu(device);
        }

        // Click "Build number"
        UiObject buildNumberLabel = device.findObject(
                new UiSelector().className("android.widget.TextView").text("Build number"));

        // Use the navigation strategy to navigate to the target
        strategy.navigate(device, buildNumberLabel);

        boolean hasBuildNumberLabel = new Wait(TimeUnit.MILLISECONDS.convert(
                10L, TimeUnit.SECONDS)).
                until(buildNumberLabel::exists);

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
     * Version 1 for api <= 25 and api >= 28
     *
     * @param testFramework see {
     *   @link android.devtools.systemimage.uitest.framework.SystemImageTestFramework() }
     * @throws Exception if it fails to find a UI widget.
     */
    public static void enableDeveloperOptions_v1(SystemImageTestFramework testFramework)
            throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();
        try {
            selectDeviceByType_v1(instrumentation,"phone");
        } catch (Exception e) {
            selectDeviceByType_v1(instrumentation,"emulated device");
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
        UiDevice device = UiDevice.getInstance(instrumentation);
        device.pressHome();

        try {
            AppLauncher.launchPath(instrumentation, true, "Settings", "System", "About emulated device");
        } catch (UiObjectNotFoundException e) {
            try {
                AppLauncher.launchPath(instrumentation, true, "Settings", "System", "About phone");
            } catch (UiObjectNotFoundException e1) {
                try {
                    AppLauncher.launchPath(instrumentation, true, "Settings", "About emulated device");
                } catch (UiObjectNotFoundException e2) {
                    AppLauncher.launchPath(instrumentation, true, "Settings", "About phone");
                }
            }
        }

        enableOptions(instrumentation);
    }


    /**
     * Enables developer options.
     *
     * Version 3 for api == 29
     *
     * @param testFramework see {
     *   @link android.devtools.systemimage.uitest.framework.SystemImageTestFramework() }
     * @throws Exception if it fails to find a UI widget.
     */
    public static void enableDeveloperOptions_v3(SystemImageTestFramework testFramework)
            throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();
        try {
            selectDeviceByType_v2(instrumentation,"phone");
        } catch (Exception e) {
            selectDeviceByType_v2(instrumentation,"emulated device");
        }
        enableOptions(instrumentation);
    }

    /**
     * Enables developer options.
     *
     * Version 4 for api == 31
     *
     * @param testFramework see {
     *   @link android.devtools.systemimage.uitest.framework.SystemImageTestFramework() }
     * @throws Exception if it fails to find a UI widget.
     */
    public static void enableDeveloperOptions_v4(SystemImageTestFramework testFramework)
            throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();
        try {
            selectDeviceByType_v3(instrumentation,"emulated device");
        } catch (Exception e) {
            selectDeviceByType_v3(instrumentation,"phone");
        }
        enableOptions(instrumentation);
    }

    /**
     * Attempt to enable developer options by trying both 'About phone' and
     * 'About emulated device' links for api's < 29
     *
     * @param instrumentation
     * @param type
     * @throws Exception if it fails to find a UI widget.
     */
    private static void selectDeviceByType_v1(Instrumentation instrumentation, String type)
            throws Exception {
        UiDevice device = UiDevice.getInstance(instrumentation);
        AppLauncher.launchPath(instrumentation, true, "Settings", "System");
        String deviceLabel = "About " +  type;
        UiObject aboutDevice = device.findObject(new UiSelector().textContains(deviceLabel));

        if (aboutDevice.waitForExists(5L)) {
            aboutDevice.clickAndWaitForNewWindow();
        } else {
            throw new UiObjectNotFoundException(deviceLabel + " not found");
        }
    }

    /**
     * Attempt to enable developer options by trying both 'About phone' and
     * 'About emulated device' links for api 29
     *
     * @param instrumentation
     * @param type
     * @throws Exception if it fails to find a UI widget.
     */
    private static void selectDeviceByType_v2(Instrumentation instrumentation, String type)
            throws Exception {
        UiDevice device = UiDevice.getInstance(instrumentation);
        AppLauncher.launchPath(instrumentation, true, "Settings");
        String deviceLabel = "About " +  type;

        UiScrollable scrollable = new UiScrollable(new UiSelector().scrollable(true));
        final UiObject aboutDevice = device.findObject(new UiSelector().textContains(deviceLabel));

        if (scrollable.scrollIntoView(aboutDevice)) {
            aboutDevice.clickAndWaitForNewWindow();
        } else {
            throw new UiObjectNotFoundException(deviceLabel + " not found");
        }
    }

    /**
     * Attempt to enable developer options by trying both 'About phone' and
     * 'About emulated device' links for api 31
     *
     * @param instrumentation
     * @param type
     * @throws Exception if it fails to find a UI widget.
     */
    private static void selectDeviceByType_v3(Instrumentation instrumentation, String type)
            throws Exception {
        String deviceLabel = "About " +  type;
        AppLauncher.launchPath(
                instrumentation, true, "Settings", deviceLabel);
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

        new watcher(device, Res.SETTINGS_WATCHER_PATTERN).checkForCondition();

        try {
            SettingsUtil.findItem_v2(instrumentation);
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

        try {
            SettingsUtil.openItem(instrumentation, "System");
            SettingsUtil.clickAdvancedMenu(device);
            return device.findObject(new UiSelector().text("Developer options")).exists();
        } catch (UiObjectNotFoundException e) {
            return false;
        }
    }
}
