package com.android.devtools.systemimage.uitest.utils;

import android.app.Instrumentation;
import android.graphics.Rect;
import android.os.RemoteException;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiObjectNotFoundException;
import android.support.test.uiautomator.UiSelector;
import android.view.Surface;

/**
 * Task Manager.
 */
public class TaskManager {
    private static final int DEFAULT_SWIPE_STEPS = 10;

    /**
     * Kill an app through recent apps menu.
     *
     * @param instrumentation see {@link android.test.InstrumentationTestCase#getInstrumentation()
     *                        getInstrumentation}
     * @param appName         the app name to kill
     * @throws UiObjectNotFoundException if it fails to find a UI widget.
     * @throws RemoteException           if it fails to press recent apps button.
     */
    public static void killApp(Instrumentation instrumentation, String appName)
            throws UiObjectNotFoundException, RemoteException {
        UiDevice device = UiDevice.getInstance(instrumentation);
        UiObject screen = device.findObject(new UiSelector());
        Rect screenRect = screen.getBounds();

        device.pressRecentApps();
        // Decide the current rotation.
        int rotation = device.getDisplayRotation();
        // Decide if it is a pad.
        boolean wideScreen =
                device.isNaturalOrientation() && device.getDisplayWidth() > device.getDisplayHeight();

        UiObject appLabel =
                device.findObject(new UiSelector().packageName("com.android.systemui").text(appName));
        Rect labelRect = appLabel.getBounds();
        if (!wideScreen && (rotation == Surface.ROTATION_0 || rotation == Surface.ROTATION_180)) {
            // Swipe right
            device.swipe(
                    labelRect.left,
                    labelRect.centerY(),
                    screenRect.right,
                    labelRect.centerY(),
                    DEFAULT_SWIPE_STEPS);
        } else {
            // Swipe up
            device.swipe(
                    labelRect.centerX(),
                    labelRect.centerY(),
                    labelRect.centerX(),
                    screenRect.top,
                    DEFAULT_SWIPE_STEPS);
        }
        device.pressHome();
    }
}
