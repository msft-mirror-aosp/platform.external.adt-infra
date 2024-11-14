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

package com.android.devtools.systemimage.uitest.framework;

import org.junit.Assert;
import org.junit.rules.TestRule;
import org.junit.runner.Description;
import org.junit.runners.model.Statement;

import android.app.Instrumentation;
import android.content.pm.PackageManager;
import android.os.Bundle;
import android.os.Environment;
import android.os.RemoteException;
import androidx.test.InstrumentationRegistry;
import androidx.test.uiautomator.UiDevice;
import androidx.test.uiautomator.UiObject;
import androidx.test.uiautomator.UiObjectNotFoundException;
import androidx.test.uiautomator.UiSelector;
import android.util.Log;

import java.io.File;
import java.io.PrintWriter;
import java.util.concurrent.TimeUnit;

/**
 * System image test framework that standardizes a test's initialization and finalization.
 */
public class SystemImageTestFramework implements TestRule {

    private static final Instrumentation mInstrumentation = InstrumentationRegistry.getInstrumentation();
    private final UiDevice mDevice = UiDevice.getInstance(mInstrumentation);
    private final Bundle args = InstrumentationRegistry.getArguments();
    private static final int RETRY_COUNT = 2;

    public Instrumentation getInstrumentation() {
        return mInstrumentation;
    }

    public UiDevice getDevice() {
        return mDevice;
    }

    public int getApi() {
        return Integer.parseInt(args.getString("api"));
    }

    public String getAbi() {
        return args.getString("abi");
    }

    public String getTag() {
        return args.getString("tag");
    }

    public boolean isGoogleApiImage() {
        return "google_apis".equals(getTag());
    }

    public boolean isGoogleApiAndPlayImage() {
        return "google_apis_playstore".equals(getTag());
    }

    public String getOrigin() {
        return args.getString("origin");
    }

    private static boolean isExternalStorageWritable() {
        String state = Environment.getExternalStorageState();
        if (Environment.MEDIA_MOUNTED.equals(state) && !Environment.MEDIA_MOUNTED_READ_ONLY.equals(state)) {
            return true;
        }
        return false;
    }

    private static boolean checkWriteExternalPermission()
    {
        String permission = "android.permission.WRITE_EXTERNAL_STORAGE";
        int res = mInstrumentation.getContext().checkCallingOrSelfPermission(permission);
        return (res == PackageManager.PERMISSION_GRANTED);
    }

    /*
     * Retrieve the default logging directory for a specified class and test method.
     * Create the directory if it doesn't exist.
     *
     * @param className The name of the class.
     * @param methodName The name of the test method.
     * @return The path to the logging directory for the specified method.
     */
    public static File getLoggingDir(String testClassName, String testMethodName) {
        Assert.assertTrue("Failed to write to external storage.", isExternalStorageWritable());
        Assert.assertTrue("Failed to acquire permission.", checkWriteExternalPermission());
        File externalStorageDocumentsDir =
                new File(Environment.getExternalStorageDirectory().getPath(), "Documents");
        File externalStorageLogsDir = new File(externalStorageDocumentsDir, "Logs");
        if (!externalStorageLogsDir.exists())
            externalStorageLogsDir.mkdir();
        File loggingDir = new File(new File(externalStorageLogsDir.getPath(), testClassName),
                testMethodName);
        loggingDir.mkdirs();
        return loggingDir;
    }

    private void resetDeviceState() throws RemoteException, UiObjectNotFoundException {
        // Close all recently opened apps so that the next retry can start afresh
        mDevice.pressHome();
        mDevice.pressRecentApps();

        UiObject apps = mDevice.findObject(new UiSelector().resourceId("android:id/content"));
        mDevice.drag(apps.getBounds().left,
                apps.getBounds().centerY(),
                apps.getBounds().right,
                apps.getBounds().centerY(),
                10);

        UiObject clearButton = mDevice.findObject(new UiSelector().text("Clear all"));
        if ( clearButton.waitForExists(5)) clearButton.click();

        Log.i("Framework", "Clear recently opened apps");
        mDevice.pressHome();
    }

    @Override
    public Statement apply(final Statement base, final Description description) {
        return statement(base, description);
    }

    private Statement statement (final Statement base, final Description description) {
        return new Statement() {
            @Override
            public void evaluate() throws Throwable {
                Throwable throwable = null;

                mDevice.wakeUp();
                Assert.assertTrue("Failed to wake up the device.", mDevice.isScreenOn());
                // Press "Menu" to unlock screen if any.
                mDevice.pressMenu();
                // Reset device to dismiss a lock screen if any.
                resetDeviceState();

                // Implement retry logic here
                for (int i = 0; i < RETRY_COUNT; i++) {
                    Log.i("Framework", "Try " + i);
                    throwable = null;
                    try {
                        base.evaluate();
                        mDevice.pressHome();
                    } catch (Throwable t) {
                        throwable = t;
                        if ( i == RETRY_COUNT-1 ) {
                            File loggingDir = getLoggingDir(description.getTestClass().getSimpleName(),
                                                            description.getMethodName());

                            // Capture the window UI hierarchy when a test fails.
                            mDevice.dumpWindowHierarchy(new File(loggingDir, "hierarchy_primary.xml"));

                            // Snap the screenshot when a test fails.
                            mDevice.takeScreenshot(new File(loggingDir, "screenshot_primary.png"));

                            // wait for 30 seconds
                            TimeUnit.SECONDS.sleep(30);

                            // Log the error message
                            PrintWriter error =
                                    new PrintWriter(new File(loggingDir, "error.txt").getPath(), "UTF-8");
                            t.printStackTrace(error);
                            error.close();
                        }
                        // clear all recently opened apps if any before retry
                        resetDeviceState();
                    }
                    if (throwable == null) {
                        return;
                    }
                }
                throw throwable;
            }
        };
    }
}
