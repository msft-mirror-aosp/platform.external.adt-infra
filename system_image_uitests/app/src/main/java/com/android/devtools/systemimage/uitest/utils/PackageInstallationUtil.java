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

import android.annotation.TargetApi;
import android.app.Instrumentation;
import android.content.Context;
import android.content.res.AssetManager;
import android.net.Uri;
import androidx.test.uiautomator.UiDevice;
import androidx.test.uiautomator.UiObject;
import androidx.test.uiautomator.UiObjectNotFoundException;
import androidx.test.uiautomator.UiScrollable;
import androidx.test.uiautomator.UiSelector;
import androidx.core.content.FileProvider;
import android.util.Log;

import com.android.devtools.systemimage.uitest.common.Res;
import com.android.devtools.systemimage.uitest.watchers.watcher;

import org.junit.Rule;
import org.junit.Assert;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.file.Files;
import java.util.List;
import java.util.concurrent.TimeUnit;

import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.pm.ApplicationInfo;

import com.android.devtools.systemimage.uitest.framework.SystemImageTestFramework;

/**
 * Package installation utility
 */
public class PackageInstallationUtil {

    private PackageInstallationUtil() {
        throw new AssertionError();
    }
    private final static String TAG = "PackageInstallationUtil";
    private final static String INSTALL_COMPLETE = "";
    private final static long INSTALL_WAIT = 20L;

    @Rule
    public final static SystemImageTestFramework testFramework = new SystemImageTestFramework();
    /**
     * Checks if a given package is installed on the android image, for builds < Android 11
     *
     * @param instrumentation see {@link android.test.InstrumentationTestCase#getInstrumentation()
     *                        getInstrumentation}
     * @param packageName     the name of the package to verify (ie com.example.android.apis)
     */
    public static boolean isPackageInstalled(Instrumentation instrumentation, String packageName) {
        Context context = testFramework.getInstrumentation().getContext();
        final PackageManager pm = context.getPackageManager();
        // As of Android 11, this method no longer returns information about all apps; see https://g.co/dev/packagevisibility for details
        List<ApplicationInfo> packages = pm.getInstalledApplications(PackageManager.GET_META_DATA);

        for (ApplicationInfo packageInfo : packages) {
            if (packageInfo.packageName.contains(packageName)) {
                Log.d(TAG, packageName + " is installed.");
                return true;
            }
        }
        Log.d(TAG, packageName + " is not installed.");
        return false;
    }

    /**
     * Checks if a given package is installed on the android image, for use with API 31
     *
     * @param instrumentation test instrumentation
     * @param appName     the name of the package to verify (ie "TestApp")
     */
    public static boolean isPackageInstalled_V2(Instrumentation instrumentation, String appName)
            throws Exception {
        UiDevice device = UiDevice.getInstance(instrumentation);
        AppLauncher.launchPath(instrumentation, true, "Settings", "Apps");

        UiObject seeAll = device.findObject(new UiSelector()
                .textContains("See all"));

        if (seeAll.waitForExists(3L)){
            seeAll.clickAndWaitForNewWindow();
        }

        UiScrollable appPermissionsList = new UiScrollable(
                new UiSelector().resourceId(Res.ANDROID_CONTENT_RES));

        UiObject appTitle = device.findObject(
                new UiSelector().text(appName));
        return appPermissionsList.scrollIntoView(appTitle);
    }

    private static boolean allowInstallation(UiDevice device) throws UiObjectNotFoundException {
        UiObject settingsButton = device.findObject(new UiSelector().textMatches("(?i)settings(?-i)").
                className("android.widget.Button"));
        if (settingsButton.waitForExists(5000)) {
            settingsButton.clickAndWaitForNewWindow();
        }

        final UiScrollable settingsList = new UiScrollable(new UiSelector().scrollable(true));
        settingsList.setAsVerticalList();
        boolean permissionGranted = false;
        UiObject allowSwitch = device.findObject(new UiSelector()
                .textMatches(Res.UNKNOWN_SOURCES_PATTERN));
        if (!allowSwitch.waitForExists(5000)) {
            allowSwitch = device.findObject(new UiSelector()
                    .textMatches(Res.UNKNOWN_SOURCES_PATTERN));
        }
        if (settingsList.waitForExists(5000) && settingsList.scrollIntoView(allowSwitch)) {
            allowSwitch.click();
            UiObject allowMessage = device.findObject(new UiSelector()
                    .textMatches(Res.UNKNOWN_SOURCES_PATTERN));
            boolean hasAllowMessage = allowMessage.waitForExists(TimeUnit.MILLISECONDS.convert(
                    INSTALL_WAIT, TimeUnit.SECONDS));
            if (!hasAllowMessage) {
                allowSwitch.click();
                permissionGranted = true;
            } else {
                permissionGranted = new watcher(device, Res.PKG_INSTALL_WATCHER_PATTERN).
                        checkForCondition();
            }
            device.pressBack();
        } else {
            allowSwitch = device.findObject(new UiSelector().className("android.widget.Switch"));
            if (settingsList.exists()) {
                settingsList.scrollToBeginning(10);
                settingsList.scrollIntoView(allowSwitch);
            }
            if (allowSwitch.waitForExists(3000)) {
                if (allowSwitch.getText().equals("OFF") || !allowSwitch.isChecked()) {
                    allowSwitch.click();
                    if (SystemUtil.getApiLevel() < 33) {
                        device.pressBack();
                    }
                    return true;
                }
            }
        }
        return permissionGranted;
    }
    /**
     * Installs the target apk on the android image
     *
     * @param instrumentation see {@link android.test.InstrumentationTestCase#getInstrumentation()
     *                        getInstrumentation}
     * @param apkName         the name of the apk to be installed (ie ApiDemos_x86.apk)
     * @param isV2            if present and true, use newer createIntent method
     */
    @TargetApi(26)
    public static String installApk(Instrumentation instrumentation, String apkName, Boolean... isV2) throws Exception {
        Context context = instrumentation.getTargetContext();
        UiDevice device = UiDevice.getInstance(instrumentation);
        AssetManager assetManager = context.getAssets();
        InputStream in = assetManager.open(apkName);
        File apkFile = new File(context.getExternalFilesDir(null), apkName);
        OutputStream out = Files.newOutputStream(apkFile.toPath());
        copyFile(in, out);
        in.close();
        out.close();

        StringBuilder result = new StringBuilder(INSTALL_COMPLETE);

        if (isV2.length == 0) {
            context.startActivity(createIntent_v1(apkFile));
        }
        else if (isV2[0]) {
            context.startActivity(createIntent_v2(context, apkFile));
        } else {
            UiObject allowFromSourceOff = UiDevice.getInstance(instrumentation).
                    findObject(new UiSelector().textMatches("(?i)off(?-i)").
                            className("android.widget.Switch"));
            if (!allowFromSourceOff.waitForExists(5000)) {
                context.startActivity(createIntent_v3(context, apkFile));
            }
        }

        UiObject settingsButton = device.findObject(new UiSelector().textMatches("(?i)settings(?-i)").
                className("android.widget.Button"));

        boolean hasSettings = settingsButton.waitForExists(TimeUnit.MILLISECONDS.convert(
                INSTALL_WAIT*2, TimeUnit.SECONDS));

        if (hasSettings || !isV2[0]) {
            if (!allowInstallation(device)) {
                result.append("Could not allow installation from outside sources.");
            }
        } else {
            result.append("Could not find settings icon. ");
        }

        UiObject[] installButtonObjects = {
                device.findObject(new UiSelector().resourceId(Res.ANDROID_BUTTON_ONE).text("Install")),
                device.findObject(new UiSelector().textMatches("(?i)install(?-i)").
                        className("android.widget.Button")),
                device.findObject(new UiSelector().resourceId(Res.PACKAGE_INSTALL_OK_RES)),
                device.findObject(new UiSelector().textMatches("(?i)update(?-i)").
                        className("android.widget.Button")),
        };

        boolean hasInstallButton = false;
        for (UiObject installButton : installButtonObjects) {
            if (installButton.waitForExists(INSTALL_WAIT/4)) {
                installButton.clickAndWaitForNewWindow();
                hasInstallButton = true;
                break;
            }
        }

                final UiObject unsafeAppDetailsButton = device.findObject(new UiSelector().
                text("More details").packageName(Res.GOOGLE_PLAY_VENDING_RES));
        if (unsafeAppDetailsButton.waitForExists(10000L)) {
            unsafeAppDetailsButton.clickAndWaitForNewWindow();
        }

        final UiObject installAnywayButton = device.findObject(new UiSelector().
                textContains("Install anyway").packageName(Res.GOOGLE_PLAY_VENDING_RES));
        if (installAnywayButton.waitForExists(5000L)) {
            installAnywayButton.clickAndWaitForNewWindow();
        }

        boolean finalHasInstallButton = hasInstallButton;
        boolean isInstallationSuccess = new Wait(INSTALL_WAIT*12).
                until(() -> finalHasInstallButton);
        if (!isInstallationSuccess) {
            result.append("Could not find install button.");
        }

        final UiObject installBlockedAppButton = device.findObject(new UiSelector().
                resourceId(Res.ANDROID_BUTTON_TWO).packageName(Res.GOOGLE_PLAY_VENDING_RES));
        if (installBlockedAppButton.waitForExists(30000)) {
            installBlockedAppButton.clickAndWaitForNewWindow();
        }

        new watcher(device, Res.PKG_INSTALL_WATCHER_PATTERN).checkForCondition();

        final UiObject doneButtonText = device.findObject(new UiSelector().textMatches("(?i)done(?-i)").
                className("android.widget.Button"));
        final UiObject doneButtonRes = device.findObject(new UiSelector().resourceId(Res.PACKAGE_INSTALL_DONE_RES));
        final UiObject doneLabel = device.findObject(new UiSelector().text("App installed."));

        boolean installationSuccess = new Wait(INSTALL_WAIT*12).
                until(() -> doneButtonText.exists() || doneButtonRes.exists() || doneLabel.exists());

        if (installationSuccess) {
            result = new StringBuilder(INSTALL_COMPLETE);
        } else if (result.length() > 0) {
            Log.w(TAG, result.toString());
            Assert.fail("Package installation was unsuccessful: " + result);
        }

        UiObject[] doneButtonObjects = { doneButtonText, doneButtonRes };

        for (UiObject doneButton : doneButtonObjects) {
            if (doneButton.waitForExists(INSTALL_WAIT/2)) {
                doneButton.clickAndWaitForNewWindow();
                break;
            }
        }

        device.pressHome();
        return result.toString();
    }

    private static Intent createIntent_v1(File apkFile) {
        Intent intent = new Intent(Intent.ACTION_VIEW);
        intent.setDataAndType(Uri.fromFile(apkFile), "application/vnd.android.package-archive");
        intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        return intent;
    }

    private static Intent createIntent_v2(Context context, File apkFile) {
        Intent intent = new Intent(Intent.ACTION_VIEW);
        intent.setFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_NEW_TASK);
        Uri apkURI = FileProvider.getUriForFile(
                context,
                context.getApplicationContext()
                        .getPackageName() + ".provider", apkFile);
        intent.setDataAndType(apkURI, "application/vnd.android.package-archive");
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
        return intent;
    }

    private static Intent createIntent_v3(Context context, File apkFile) {
        final int api = SystemUtil.getApiLevel();
        Uri apkURI = FileProvider.getUriForFile(
                context,
                context.getApplicationContext()
                        .getPackageName() + ".provider", apkFile);
        Intent intent = new Intent(Intent.ACTION_INSTALL_PACKAGE);
        intent.setDataAndType(apkURI, "application/vnd.android.package-archive");

        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
        if (api >= 24) {
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        }
        return intent;
    }

    private static void copyFile(InputStream in, OutputStream out) throws IOException {
        byte[] buffer = new byte[1024];
        int read;
        while ((read = in.read(buffer)) != -1) {
            out.write(buffer, 0, read);
        }
    }
}
