package com.android.devtools.systemimage.uitest.utils;

import android.app.Instrumentation;
import android.content.Context;
import android.content.Intent;
import android.content.res.AssetManager;
import android.net.Uri;
import android.os.Environment;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiObjectNotFoundException;
import android.support.test.uiautomator.UiScrollable;
import android.support.test.uiautomator.UiSelector;

import com.android.devtools.systemimage.uitest.common.Res;

import junit.framework.AssertionFailedError;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;

/**
 * Application managers.
 */
public class AppManager {

  private static boolean isExternalStorageAvailable() {
    String extStorageState = Environment.getExternalStorageState();
    if (Environment.MEDIA_MOUNTED.equals(extStorageState)) {
      return true;
    }
    return false;
  }

  /**
   * Installs a testing app. The app must be in main/assets.
   * @param instrumentation
   * see {@link android.test.InstrumentationTestCase#getInstrumentation() getInstrumentation}
   * @param apkName the APK file full name in main/assets
   * @throws IOException if File IO fails.
   * @throws UiObjectNotFoundException if it fails to find a UI widget.
   */
  public static void installApp(Instrumentation instrumentation, String apkName)
      throws IOException, UiObjectNotFoundException {
    Context context = instrumentation.getTargetContext();
    AssetManager assetManager = context.getAssets();
    InputStream in = assetManager.open(apkName);
    File apkFile = new File(context.getExternalFilesDir(null), apkName);
    OutputStream out = new FileOutputStream(apkFile);
    copyFile(in, out);
    in.close();
    out.close();

    // Install app via Intent and UiAutomator
    Intent intent = new Intent(Intent.ACTION_VIEW);
    intent.setDataAndType(Uri.fromFile(apkFile), "application/vnd.android.package-archive");
    intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
    context.startActivity(intent);
    UiDevice device = UiDevice.getInstance(instrumentation);
    UiObject installButton = device.findObject(new UiSelector().textMatches("(INSTALL|Install)"));
    if (installButton.exists()) {
      installButton.clickAndWaitForNewWindow();
    }
    device.findObject(new UiSelector().textMatches("(DONE|Done)")).click();
  }

  private static void copyFile(InputStream in, OutputStream out) throws IOException {
    byte[] buffer = new byte[1024];
    int read;
    while ((read = in.read(buffer)) != -1) {
      out.write(buffer, 0, read);
    }
  }

  /**
   * Uninstalls a testing app.
   * @param instrumentation
   * see {@link android.test.InstrumentationTestCase#getInstrumentation() getInstrumentation}
   * @param appName the app name
   * @param pkgName the app's package name which is used when the app (e.g., service) has no name.
   * @throws IOException if File IO fails.
   * @throws UiObjectNotFoundException if it fails to find a UI object.
   */
  public static void uninstallApp(Instrumentation instrumentation, String appName, String pkgName)
      throws IOException, UiObjectNotFoundException {
    UiDevice device = UiDevice.getInstance(instrumentation);

    // Find and click "appName" or "pkgName" in Settings/Apps
    openAppList(instrumentation);
    UiScrollable appList =
        new UiScrollable(new UiSelector().resourceIdMatches(Res.APPS_LIST_CONTAINER_RES));
    appList.setAsVerticalList();
    String searchedName;
    if (appName != null) {
      searchedName = appName;
    } else {
      if (pkgName == null) {
        throw new AssertionFailedError("Neither appName nor pkgName is non-null.");
      }
      searchedName = pkgName;
    }
    UiObject app =
        appList.getChildByText(new UiSelector().className("android.widget.TextView"), searchedName);
    app.clickAndWaitForNewWindow();

    // Uninstall
    device.findObject(new UiSelector().text("Uninstall")).clickAndWaitForNewWindow();
    device.findObject(new UiSelector().text("OK")).clickAndWaitForNewWindow();
  }

  /**
   * Checks if an app is installed.
   * @param instrumentation
   * see {@link android.test.InstrumentationTestCase#getInstrumentation() getInstrumentation}
   * @param appName the app name
   * @param pkgName the app's package name which is used when the app (e.g., service) has no name.
   * @return {@code true} if the app is installed, or {@code false} otherwise.
   * @throws UiObjectNotFoundException
   */
  public static boolean isAppInstalled(
      Instrumentation instrumentation, String appName, String pkgName)
      throws UiObjectNotFoundException {
    UiDevice device = UiDevice.getInstance(instrumentation);

    // Looking for "appName" or "pkgName" in Settings/Apps
    openAppList(instrumentation);
    UiScrollable appList =
        new UiScrollable(new UiSelector().resourceIdMatches(Res.APPS_LIST_CONTAINER_RES));
    appList.setAsVerticalList();
    String searchedName;
    if (appName != null) {
      searchedName = appName;
    } else {
      if (pkgName == null) {
        throw new AssertionFailedError("Neither appName nor pkgName is non-null.");
      }
      searchedName = pkgName;
    }
    try {
      appList.getChildByText(new UiSelector().className("android.widget.TextView"), searchedName);
      return true;
    } catch (UiObjectNotFoundException e) {
      return false;
    }
  }

  private static void openAppList(Instrumentation instrumentation)
      throws UiObjectNotFoundException {
    // Open settings
    AppLauncher.launch(instrumentation, "Settings");

    // Find and click "Apps" in Settings
    UiScrollable itemList =
        new UiScrollable(new UiSelector().resourceIdMatches(Res.SETTINGS_LIST_CONTAINER_RES));
    itemList.setAsVerticalList();
    UiObject item =
        itemList.getChildByText(new UiSelector().className("android.widget.TextView"), "Apps");
    item.clickAndWaitForNewWindow();
  }
}
