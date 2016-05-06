package com.android.devtools.systemimage.uitest.utils;

import android.app.Instrumentation;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiObjectNotFoundException;
import android.support.test.uiautomator.UiScrollable;
import android.support.test.uiautomator.UiSelector;

import com.android.devtools.systemimage.uitest.common.Res;

/**
 * Developer options manager.
 */
public class DeveloperOptionsManager {

    /**
     * Enables developer options.
     *
     * @param instrumentation see {@link android.test.InstrumentationTestCase#getInstrumentation()
     *                        getInstrumentation}
     * @throws UiObjectNotFoundException if it fails to find a UI widget.
     */
    public static void enableDeveloperOptions(Instrumentation instrumentation)
            throws UiObjectNotFoundException {
        AppLauncher.launch(instrumentation, "Settings");

        // Click "About phone".
        UiScrollable itemList =
                new UiScrollable(new UiSelector().resourceIdMatches(Res.SETTINGS_LIST_CONTAINER_RES));
        itemList.setAsVerticalList();
        UiObject item =
                itemList.getChildByText(
                        new UiSelector().className("android.widget.TextView"), "About phone");
        item.clickAndWaitForNewWindow();

        // Click "Build number"
        itemList =
                new UiScrollable(new UiSelector().resourceIdMatches(Res.ABOUT_PHONE_LIST_CONTAINER_RES));
        itemList.setAsVerticalList();
        item =
                itemList.getChildByText(
                        new UiSelector().className("android.widget.TextView"), "Build number");

        // Currently, UiAutomator cannot catch toast messages (see b/26511336).
        // We simply repeat for 10 times without verification. Will improve if it causes flakiness.
        for (int i = 0; i < 10; i++) {
            item.click();
        }
    }

    /**
     * Checks if the developer options is enabled.
     *
     * @param instrumentation see {@link android.test.InstrumentationTestCase#getInstrumentation()
     *                        getInstrumentation}
     * @return {@code true} if the developer options is enabled, or {@code false} otherwise.
     * @throws UiObjectNotFoundException if it fails to find a UI widget.
     */
    public static boolean isDeveloperOptionsEnabled(Instrumentation instrumentation)
            throws UiObjectNotFoundException {
        AppLauncher.launch(instrumentation, "Settings");

        // Look for "Developer options".
        UiScrollable itemList =
                new UiScrollable(new UiSelector().resourceIdMatches(Res.SETTINGS_LIST_CONTAINER_RES));
        itemList.setAsVerticalList();
        try {
            itemList.getChildByText(
                    new UiSelector().className("android.widget.TextView"), "Developer options");
            return true;
        } catch (UiObjectNotFoundException e) {
            return false;
        }
    }
}
