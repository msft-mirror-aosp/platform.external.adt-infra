package com.android.devtools.systemimage.uitest.utils;

import android.app.Instrumentation;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiObjectNotFoundException;
import android.support.test.uiautomator.UiScrollable;
import android.support.test.uiautomator.UiSelector;

import com.android.devtools.systemimage.uitest.common.Res;

/**
 * Application launcher.
 */
public class AppLauncher {

  /**
   * Launches application by launcher.
   * @param instrumentation
   * see {@link android.test.InstrumentationTestCase#getInstrumentation() getInstrumentation}
   * @param appName the app name to launch
   * @throws UiObjectNotFoundException if it fails to find a UI object.
   */
  public static void launch(Instrumentation instrumentation, String appName)
      throws UiObjectNotFoundException {
    UiDevice device = UiDevice.getInstance(instrumentation);
    device.pressHome();
    device.findObject(new UiSelector().descriptionContains("Apps")).clickAndWaitForNewWindow();
    UiScrollable appList =
        new UiScrollable(new UiSelector().resourceIdMatches(Res.LAUNCHER_LIST_CONTAINER_RES_REGEX));

    // Note that the direction of scrolling, even the res-id could change with future Android
    // releases. We may need a check here to determine the launcher and res-id used to decide
    // what appropriate gestures to perform.
    appList.setAsVerticalList();
    UiObject app =
        appList.getChildByText(new UiSelector().className("android.widget.TextView"), appName);
    app.clickAndWaitForNewWindow();
  }
}
