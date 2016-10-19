package com.android.devtools.systemimage.uitest.utils;

import android.app.Instrumentation;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiObjectNotFoundException;
import android.support.test.uiautomator.UiScrollable;
import android.support.test.uiautomator.UiSelector;

import com.android.devtools.systemimage.uitest.common.Res;
import com.android.devtools.systemimage.uitest.framework.SystemImageTestFramework;

import java.util.concurrent.TimeUnit;

public class SettingsUtil {
    public static final String TAG = SettingsUtil.class.getName();

    private SettingsUtil() {
        throw new AssertionError();
    }

    /**
     * Launches Settings and get the item list as a @{code UiScrollable}, ready to search for
     * clickable items.
     */
    public static UiScrollable launchAndGetItemList(Instrumentation instrumentation) throws UiObjectNotFoundException {
        AppLauncher.launch(instrumentation, "Settings");

        UiScrollable itemList = new UiScrollable(new UiSelector().resourceIdMatches(
                Res.SETTINGS_LIST_CONTAINER_RES));
        if (!itemList.exists()) {
            itemList = new UiScrollable(new UiSelector().resourceIdMatches(
                    Res.SETTINGS_RECYCLER_VIEW_RES));
        }
        return itemList.setAsVerticalList();
    }

    /**
     * Launches Settings and scroll to the item whose name contains the given text. Returns
     * @{code true} iff the item is there.
     */
    public static boolean scrollToItem(Instrumentation instrumentation, String text) throws UiObjectNotFoundException {
        UiScrollable itemList = launchAndGetItemList(instrumentation);
        return itemList.scrollIntoView(new UiSelector().textContains(text));
    }

    /**
     * Launches Settings and find the item with the given name. Returns the item.
     */
    public static UiObject findItem(Instrumentation instrumentation, String name) throws UiObjectNotFoundException {
        UiScrollable itemList = launchAndGetItemList(instrumentation);
        SystemImageTestFramework testFramework = new SystemImageTestFramework();
        if(testFramework.getApi() >= 24){
            itemList.scrollIntoView(new UiSelector().textContains(name));
            return itemList.getChild(new UiSelector().text(name));
        }
        else {
            UiObject child = itemList.getChild(new UiSelector().text(name));
            child.waitForExists(TimeUnit.SECONDS.toMillis(5));
            itemList.scrollIntoView(child);
            return child;
        }
    }

    /**
     * Launches Settings and launch the item with the given name. Returns the result of the click call.
     */
    public static boolean openItem(Instrumentation instrumentation, String name) throws UiObjectNotFoundException {
        return findItem(instrumentation, name).clickAndWaitForNewWindow();
    }
}