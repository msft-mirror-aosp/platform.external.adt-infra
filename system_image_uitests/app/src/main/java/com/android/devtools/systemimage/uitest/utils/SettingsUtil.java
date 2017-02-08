package com.android.devtools.systemimage.uitest.utils;

import android.app.Instrumentation;
import android.graphics.Rect;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiObjectNotFoundException;
import android.support.test.uiautomator.UiScrollable;
import android.support.test.uiautomator.UiSelector;

import com.android.devtools.systemimage.uitest.common.Res;

import junit.framework.Assert;

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
        UiObject item = itemList.getChildByText(new UiSelector().className("android.widget.TextView"), name);
        if (item.waitForExists(TimeUnit.SECONDS.toMillis(5))) {
            return item;
        } else {
            throw new UiObjectNotFoundException("Failed to find the item in Settings.");
        }
    }

    /**
     * Launches Settings and launch the item with the given name. Returns the result of the click call.
     */
    public static boolean openItem(Instrumentation instrumentation, String name) throws UiObjectNotFoundException {
        return findItem(instrumentation, name).clickAndWaitForNewWindow();
    }

    /**
     * Activate "Sample Device Admin" policy under Device administrators.
     *
     * @param instrumentation see {@link android.test.InstrumentationTestCase#getInstrumentation()
     *                        getInstrumentation}
     * @param adminName admin policy name
     * @throws UiObjectNotFoundException if it fails to find a UI widget.
     */
    public static void activate(Instrumentation instrumentation, String adminName)
            throws UiObjectNotFoundException {
        changePolicyActivation(instrumentation, adminName, "Activate");
    }

    /**
     * Deactivate "Sample Device Admin" policy under Device administrators.
     *
     * @param instrumentation see {@link android.test.InstrumentationTestCase#getInstrumentation()
     *                        getInstrumentation}
     * @param adminName admin policy name
     * @throws UiObjectNotFoundException if it fails to find a UI widget.
     */
    public static void deactivate(Instrumentation instrumentation, String adminName)
            throws UiObjectNotFoundException {
        changePolicyActivation(instrumentation, adminName, "Deactivate");
    }


    private static void changePolicyActivation(Instrumentation instrumentation, String adminName,
                                               String change) throws UiObjectNotFoundException {

        SettingsUtil.openItem(instrumentation, "Security");
        UiDevice device = UiDevice.getInstance(instrumentation);
        UiScrollable itemList =
                new UiScrollable(
                        new UiSelector().resourceIdMatches(Res.SETTINGS_LIST_CONTAINER_RES)
                );
        itemList.setAsVerticalList();
        // Go to device administrators page.
        itemList.getChildByText( new UiSelector().className("android.widget.TextView"),
                "Device administrators").clickAndWaitForNewWindow();

        // Select admin option to activate/deactivate.
        device.findObject(new UiSelector().text(adminName)).clickAndWaitForNewWindow();
        UiObject scrollView = device.findObject(
                new UiSelector().className("android.widget.ScrollView"));

        scrollView.waitForExists(TimeUnit.SECONDS.toMillis(3L));

        // Scroll to the end to see Activate/Deactivate button.
        Rect labelRect = scrollView.getBounds();
        device.swipe(
                labelRect.centerX(),
                labelRect.centerY(),
                labelRect.centerX(),
                labelRect.top,
                10);


        UiObject actionButton = device.findObject(
                new UiSelector().resourceId("com.android.settings:id/action_button"));

        actionButton.waitForExists(TimeUnit.SECONDS.toMillis(3L));

        Assert.assertTrue(actionButton.getText().contains(change));

        if (change.equalsIgnoreCase("Activate")) {
            actionButton.clickAndWaitForNewWindow();
            return;
        }
        // Only for deactivation: For deactivation and extra alert box is displayed.
        actionButton.click();
        UiObject okButton = device.findObject(new UiSelector().text("OK"));
        okButton.waitForExists(TimeUnit.SECONDS.toMillis(3L));
        okButton.click();
    }
}

