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

package com.android.devtools.systemimage.uitest.utils.api22;

import android.app.Instrumentation;
import android.os.Environment;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiObjectNotFoundException;
import android.support.test.uiautomator.UiSelector;
import android.util.Log;

import com.android.devtools.systemimage.uitest.common.Res;
import com.android.devtools.systemimage.uitest.watchers.CameraAccessPermissionsWatcher;

import org.junit.Assert;

import java.io.File;
import java.util.concurrent.TimeUnit;

/**
 * Test on shell utility.
 */
public class CameraTestUtils {
    private static final String TAG = "CameraTest";

    //public final SystemImageTestFramework testFramework = new SystemImageTestFramework();

    //public Timeout globalTimeout = Timeout.seconds(120);

    /* A helper method to perform the common camera actions of both the photo and video tests,
     * based on the mode parameter */
    public static boolean useCamera(Instrumentation instrumentation, String mode) throws Exception {
        final UiDevice device = UiDevice.getInstance(instrumentation);

        AppLauncher.launchPath(instrumentation, new String[]{"Camera"});
        new CameraAccessPermissionsWatcher(device).checkForCondition();

        device.pressBack();
        device.pressHome();

        AppLauncher.launchPath(instrumentation, new String[]{"Camera"});
        UiObject cameraFrame = device.findObject(new UiSelector().resourceId(Res.CAMERA_FRAME_RES));
        if (cameraFrame.waitForExists(5L)) {
            cameraFrame.click();
            cameraFrame.swipeRight(3);
        }

        new CameraAccessPermissionsWatcher(device).checkForCondition();

        boolean cameraModeButtonExists = new Wait().until(new Wait.ExpectedCondition() {
                @Override
                public boolean isTrue() {
                    return device.findObject(new UiSelector().descriptionStartsWith("Switch to")).exists();
                }
            });

        Assert.assertTrue("Button to select " + mode + " mode not found", cameraModeButtonExists);

        if (mode.equals("Camera")) {
            device.findObject(new UiSelector().description("Switch to Camera Mode")).click();
        } else {
            device.findObject(new UiSelector().description("Switch to Video Camera")).click();
        }

        createTestFile(device, mode);
        deleteTestFile(device);

        String originalFileList = listGalleryFiles(instrumentation);

        AppLauncher.launchPath(instrumentation, new String[]{"Camera"});
        new CameraAccessPermissionsWatcher(device).checkForCondition();

        createTestFile(device, mode);

        String fileExt = mode.equals("Camera") ? ".jpg" : ".mp4";
        String newFileList = listGalleryFiles(instrumentation);

        Log.d(TAG, "Test mode is " + mode);
        Log.d(TAG, "Original gallery file list is " + originalFileList);
        Log.d(TAG, "Gallery file list after create is " + newFileList);

        Assert.assertTrue("New file was not added to the gallery",
                !originalFileList.equals(newFileList) && newFileList.contains(fileExt));

        deleteTestFile(device);

        String lastFileList = listGalleryFiles(instrumentation);
        Log.d(TAG, "Gallery file list after delete is " + lastFileList);

        return originalFileList.equals(lastFileList);
    }


    /* A helper method to list the contents on the external media files storage directory */
    private static String listGalleryFiles(Instrumentation instrumentation) throws Exception {
        final File externalStorage = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DCIM);
        final String externalStorageDir = externalStorage.toString() + "/Camera";
        final String cmd = "ls " + externalStorageDir;

        final ShellUtil.ShellResult result = ShellUtil.invokeCommand(cmd);

        boolean photosListed = new Wait(
                TimeUnit.MILLISECONDS.convert(10L, TimeUnit.SECONDS)).until(
                    new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() {
                        return result.stderr != null && result.stderr.length() == 0;
                    }
                });

        if (!photosListed) {
            Log.e(TAG, "Gallery files not listed. Error: " + result.stderr);
            Log.w(TAG, "External storage directory is " + externalStorageDir);
            Log.w(TAG, "Shell command (" + cmd + ") results: " + result.stdout);
        }

        Assert.assertTrue("Media gallery 'ls' command failed.", photosListed);
        Log.d(TAG, "ls result " + result.stdout);
        return result.stdout;
    }

    /* A helper method to generate either a new photo or video, and then select view it */
    private static void createTestFile(UiDevice device, String mode) throws UiObjectNotFoundException {
        UiObject shutterButton = device.findObject(new UiSelector().resourceId(Res.CAMERA_SHUTTER_BUTTON_RES));
        UiObject fileThumbnail = device.findObject(new UiSelector().resourceId(Res.CAMERA_FILE_THUMBNAIL_RES));

        if (shutterButton.waitForExists(3L)) {
            shutterButton.click();
            if (mode.equals("Video")) {
                fileThumbnail.waitForExists(3L);
                shutterButton.click();
            }

            if (fileThumbnail.waitForExists(3L)) {
                fileThumbnail.clickAndWaitForNewWindow();
            }
        }
    }

    /* A helper method to delete a new photo or video */
    private static void deleteTestFile(UiDevice device) throws UiObjectNotFoundException {
        UiObject trashCan = device.findObject(new UiSelector().resourceId(Res.CAMERA_FILE_DELETE_RES));
        UiObject fileThumbnail = device.findObject(new UiSelector().resourceId(Res.CAMERA_FILE_THUMBNAIL_RES));

        if (fileThumbnail.waitForExists(3L)) {
            fileThumbnail.clickAndWaitForNewWindow();
        }

        if (trashCan.waitForExists(3L)) {
            trashCan.click();
        }

        device.pressBack();
        device.pressHome();
    }
}