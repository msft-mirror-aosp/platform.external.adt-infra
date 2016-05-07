package com.android.devtools.systemimage.uitest.utils;

import android.support.test.uiautomator.By;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiSelector;
import android.support.test.uiautomator.Until;

import java.util.concurrent.TimeUnit;

/**
 * Class for utility functions.
 */
public class TestUtils {
    private static final String WIFI_ICONS_RES = "com.android.systemui:id/wifi_signal";
    private static final String MOBILE_TYPE_ICONS_RES = "com.android.systemui:id/mobile_type";

    private TestUtils() {
        throw new AssertionError();
    }

    /**
     * Returns the API level on the device or emulator.
     */
    public static int getApiLevel() {
        return android.os.Build.VERSION.SDK_INT;
    }

    /**
     * Disable all Home overlay items we see when we first start a newly installed emulator.
     */
    public static void disableHomeOverlayItems(UiDevice device) throws Exception {
        if (TestUtils.getApiLevel() == 22) {
            // Check for the overlay dialog on top by checking for the GOT IT text.
            if (device.findObject(new UiSelector().textContains("GOT IT")).exists()) {
                // Click the GOT IT text from the dialog that appears.
                device.findObject(new UiSelector().textContains("GOT IT")).click();
            }
        } else {
            // Check if the Make yourself at home screen is visible.
            if (device.findObject(new UiSelector().textContains("OK")).exists()) {
                // If overlay is visible, click the OK button to dismiss it.
                device.findObject(new UiSelector().textContains("OK")).click();
            }
        }
    }

    /**
     * Disable all App overlay items we see when we first start a newly installed emulator.
     */
    public static void disableAppsOverlayItems(UiDevice device) throws Exception {
        if (TestUtils.getApiLevel() == 19 || TestUtils.getApiLevel() == 21) {
            // Click the Apps button.
            device.findObject(
                    new UiSelector().descriptionContains("Apps")).clickAndWaitForNewWindow();
            // Check if the Choose some apps screen is visible.
            if (device.findObject(new UiSelector().textContains("OK")).exists()) {
                // If visible, click the OK button to dismiss it.
                device.findObject(new UiSelector().textContains("OK")).click();
            }
            // Exit the apps list.
            device.pressHome();
        }
    }

    /**
     * Checks network status. If the emulator is conencted to the internet via WiFi or mobile data.
     * <p>
     * The emulator returns to the home screen for either case.
     */
    public static boolean verifyNetworkStatus(UiDevice device) {
        // Verify that a mobile data or WiFi icon is on the status bar.
        device.openNotification();
        boolean hasWifi = verifyWifi(device);
        if (hasWifi) {
            device.pressHome();
            return true;
        }
        boolean hasMobileData = verifyMobileData(device);
        if (hasMobileData) {
            device.pressHome();
            return true;
        }
        device.pressHome();
        return false;
    }

    public static boolean verifyWifi(UiDevice device) {
        // Wait to check the notification bar items. Opening notification is an animation.
        boolean isTrue =
                device.wait(
                        Until.hasObject(By.res(WIFI_ICONS_RES)),
                        TimeUnit.MILLISECONDS.convert(3L, TimeUnit.SECONDS));

        return isTrue;
    }

    public static boolean verifyMobileData(UiDevice device) {
        // Wait to check the notification bar items. Opening notification is an animation.
        boolean isTrue =
                device.wait(
                        Until.hasObject(By.res(MOBILE_TYPE_ICONS_RES)),
                        TimeUnit.MILLISECONDS.convert(3L, TimeUnit.SECONDS));
        return isTrue;
    }
}