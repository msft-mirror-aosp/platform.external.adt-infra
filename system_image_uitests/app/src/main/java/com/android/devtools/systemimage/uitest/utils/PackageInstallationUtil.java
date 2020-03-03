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
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiObjectNotFoundException;
import android.support.test.uiautomator.UiScrollable;
import android.support.test.uiautomator.UiSelector;
import android.support.v4.content.FileProvider;
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
    private final static long INSTALL_WAIT = 5L;

    @Rule
    public final static SystemImageTestFramework testFramework = new SystemImageTestFramework();
    /**
     * Checks if a given package is installed on the android image
     *
     * @param instrumentation see {@link android.test.InstrumentationTestCase#getInstrumentation()
     *                        getInstrumentation}
     * @param packageName     the name of the package to verify (ie com.example.android.apis)
     */
    public static boolean isPackageInstalled(Instrumentation instrumentation, String packageName) {
        Context context = testFramework.getInstrumentation().getContext();
        final PackageManager pm = context.getPackageManager();
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

    private static boolean allowInstallation(UiDevice device) throws UiObjectNotFoundException {
        UiObject settingsButton = device.findObject(new UiSelector().textMatches("(?i)settings(?-i)").
                className("android.widget.Button"));
        if (!settingsButton.waitForExists(5000)) {
            return false;
        }

        settingsButton.clickAndWaitForNewWindow();
        final UiScrollable settingsList = new UiScrollable(new UiSelector().scrollable(true));
        settingsList.setAsVerticalList();
        boolean permissionGranted = false;
        UiObject allowSwitch = device.findObject(new UiSelector()
                .textMatches(Res.UNKNOWN_SOURCES_PATTERN));
        if (settingsList.scrollIntoView(allowSwitch)) {
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
            settingsList.scrollToBeginning(10);
            allowSwitch = device.findObject(new UiSelector().className("android.widget.Switch"));
            if (settingsList.scrollIntoView(allowSwitch)) {
                if (allowSwitch.getText().equals("OFF")) {
                    allowSwitch.click();
                }
                device.pressBack();
                permissionGranted = true;
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
        AssetManager assetManager = context.getAssets();
        InputStream in = assetManager.open(apkName);
        File apkFile = new File(context.getExternalFilesDir(null), apkName);
        OutputStream out = new FileOutputStream(apkFile);
        copyFile(in, out);
        in.close();
        out.close();

        String result = "";

        boolean useV2 = isV2.length > 0 ? isV2[0] : false;
        if (useV2) {
            context.startActivity(createIntent_v2(context, apkFile));
        } else {
            context.startActivity(createIntent_v1(apkFile));
        }

        UiDevice device = UiDevice.getInstance(instrumentation);
        UiObject settingsButton = device.findObject(new UiSelector().textMatches("(?i)settings(?-i)").
                className("android.widget.Button"));

        boolean hasSettings = settingsButton.waitForExists(TimeUnit.MILLISECONDS.convert(
                INSTALL_WAIT, TimeUnit.SECONDS));

        if (hasSettings) {
            if (!allowInstallation(device)) {
                result += "Could not allow installation from outside sources.";
            }
        } else {
            result += "Could not find settings icon. ";
        }

        UiObject installButton = device.findObject(new UiSelector().textMatches("(?i)install(?-i)").
                className("android.widget.Button"));
        boolean hasInstallButton = installButton.waitForExists(TimeUnit.MILLISECONDS.convert(
                INSTALL_WAIT*2, TimeUnit.SECONDS));
        if (hasInstallButton) {
            installButton.clickAndWaitForNewWindow();
        } else {
            installButton = device.findObject(new UiSelector().resourceId(Res.PACKAGE_INSTALL_OK_RES));
            if (installButton.exists()) {
                installButton.clickAndWaitForNewWindow();
            } else {
                result += "Could not find install button.";
            }
        }

        new watcher(device, Res.PKG_INSTALL_WATCHER_PATTERN).checkForCondition();

        final UiObject doneButtonText = device.findObject(new UiSelector().textMatches("(?i)done(?-i)").
                className("android.widget.Button"));
        final UiObject doneButtonRes = device.findObject(new UiSelector().resourceId(Res.PACKAGE_INSTALL_DONE_RES));
        final UiObject doneLabel = device.findObject(new UiSelector().text("App installed."));

        boolean installationSuccess = new Wait(INSTALL_WAIT * 12L).
                until(() -> doneButtonText.exists() || doneButtonRes.exists() || doneLabel.exists());

        result = installationSuccess ? INSTALL_COMPLETE : result + "Could not find done button. ";

        if (!result.isEmpty()) {
            Log.w(TAG, result);
            Assert.fail("Package installation was unsuccessful: " + result);
        }

        device.pressHome();
        return result;
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

    private static void copyFile(InputStream in, OutputStream out) throws IOException {
        byte[] buffer = new byte[1024];
        int read;
        while ((read = in.read(buffer)) != -1) {
            out.write(buffer, 0, read);
        }
    }
}
