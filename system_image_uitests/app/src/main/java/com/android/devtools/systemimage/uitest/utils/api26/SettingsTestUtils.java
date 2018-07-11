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

package com.android.devtools.systemimage.uitest.utils.api26;

import android.app.Instrumentation;
import android.support.test.uiautomator.By;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiObject2;
import android.support.test.uiautomator.UiObjectNotFoundException;
import android.support.test.uiautomator.UiScrollable;
import android.support.test.uiautomator.UiSelector;
import android.util.Log;
import android.widget.Switch;

import com.android.devtools.systemimage.uitest.common.Res;
import com.android.devtools.systemimage.uitest.watchers.CameraAccessPermissionsWatcher;
import com.android.devtools.systemimage.uitest.watchers.SettingsTestPopupWatcher;

import static org.junit.Assert.assertTrue;

/**
 * Test class for Android Settings page on Google API images.
 */
public class SettingsTestUtils {
    private final static String TAG = "SettingsTest";

    /**
     * Common code for finding a checkbox/switch in the Date & time settings.
     */
    public static UiObject2 navigateToDateTimeSwitch(String text,
                                                     Instrumentation instrumentation,
                                                     final String container) {
        try {
            return UiAutomatorPlus.findObjectByRelative(
                    instrumentation,
                    By.clazz("android.widget.Switch"),
                    By.text(text),
                    By.res(container));
        } catch (UiObjectNotFoundException e1) {
            try {
                return UiAutomatorPlus.findObjectByRelative(
                        instrumentation,
                        By.clazz("android.widget.CheckBox"),
                        By.text(text),
                        By.res(container));
            } catch (UiObjectNotFoundException e2) {
                assertTrue("Could not find Date Time switch", false);
            }
        }
        return null;
    }

    /**
     * Check if the the selected policy is checked or not.
     */
    public static boolean checkStatusOfPolicy(Instrumentation instrumentation, UiDevice device, String switchWidget)
            throws Exception {
        UiSelector listViewSelector = new UiSelector().resourceId(Res.ANDROID_LIST_RES);

        new SettingsTestPopupWatcher(device).checkForCondition();
        assertTrue(device.findObject(listViewSelector).exists());

        // Get all the available "Device administrators" options
        int size = device.findObject(listViewSelector).getChildCount();

        // Verify that the correct checkbox (Sample Device Admin) is checked
        for (int i = 0; i < size; i++) {
            UiSelector sampleDeviceSelection = listViewSelector.childSelector(new
                    UiSelector().index(i));

            UiObject2 sampleDeviceAdminCheckbox = UiAutomatorPlus.findObjectByRelative(
                    instrumentation,
                    By.clazz(switchWidget),
                    By.text("Sample Device Admin"),
                    By.res(Res.ANDROID_LIST_RES));

            if (sampleDeviceAdminCheckbox != null) {
                boolean isChecked = sampleDeviceAdminCheckbox.isChecked();
                return isChecked;
            }
        }
        return false;
    }

    public static UiObject findObjectInScrollable(UiSelector selector) throws UiObjectNotFoundException {
        UiScrollable scrollable = new UiScrollable(new UiSelector().scrollable(true));
        scrollable.scrollIntoView(selector);
        return scrollable.getChild(selector);
    }

    public static void setCameraEnabled(final boolean enableCameraDevices, Instrumentation instrumentation, final UiDevice device) throws Exception {
        boolean isAPIDemoInstalled = PackageInstallationUtil.isPackageInstalled(instrumentation,
                "com.example.android.apis");

        if (isAPIDemoInstalled) {
            final boolean enableCameras = enableCameraDevices;
            String cameraCheckboxLabel = enableCameras ? "Device cameras disabled" :
                    "Device cameras enabled";
            final UiObject enableCamerasCheckbox = device.findObject(
                    new UiSelector().text(cameraCheckboxLabel));

            AppLauncher.launch(instrumentation, "API Demos");
            boolean widgetExists = new Wait().until(new Wait.ExpectedCondition() {
                @Override
                public boolean isTrue() throws Exception {
                    return device.findObject(new UiSelector().textContains("App")).exists();
                }
            });
            if (widgetExists) {
                device.findObject(new UiSelector().textContains("App")).click();
            }
            widgetExists = new Wait().until(new Wait.ExpectedCondition() {
                @Override
                public boolean isTrue() throws Exception {
                    return device.findObject(new UiSelector().text("Device Admin")).exists();
                }
            });

            if (widgetExists) {
                device.findObject(new UiSelector().text("Device Admin")).click();
            }
            widgetExists = new Wait().until(new Wait.ExpectedCondition() {
                @Override
                public boolean isTrue() throws Exception {
                    return device.findObject(new UiSelector().text("General")).exists();
                }
            });
            if (widgetExists) {
                device.findObject(new UiSelector().text("General")).click();
            }

            widgetExists = new Wait().until(new Wait.ExpectedCondition() {
                @Override
                public boolean isTrue() throws Exception {
                    return enableCamerasCheckbox.exists();
                }
            });

            if (widgetExists) {
                enableCamerasCheckbox.click();
            }

            device.pressHome();
        } else {
            Log.w(TAG, "setCameraEnabled: required APK is missing");
        }
    }

    public static void gotoCameraApp(Instrumentation instrumentation, UiDevice device) throws Exception {
        AppLauncher.launch(instrumentation, "Camera");
        new CameraAccessPermissionsWatcher(device).checkForCondition();
    }

    public static boolean verifyCameraAppDisabled(UiDevice device) {
        return device.hasObject(By.textContains(
                "Camera has been disabled because of security policies")) ||
                device.hasObject(By.text("Can't connect to the camera."));
    }

    public static UiObject findObjectByRelative(UiScrollable verticalList, String childText, String classType) throws Exception{
        UiObject uiObject = verticalList.getChildByText(new UiSelector().className(classType),childText);
        return uiObject.getChild(new UiSelector().className(Switch.class.getName()));
    }
}