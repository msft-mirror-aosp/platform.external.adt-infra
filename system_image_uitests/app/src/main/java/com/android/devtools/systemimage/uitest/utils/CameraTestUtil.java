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

import com.android.devtools.systemimage.uitest.common.Res;
import com.android.devtools.systemimage.uitest.watchers.CameraAccessPermissionsWatcher;

import android.app.Instrumentation;
import android.os.Environment;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiObjectNotFoundException;
import android.support.test.uiautomator.UiSelector;
import android.util.Log;

import org.junit.Assert;

import java.io.File;
import java.util.concurrent.TimeUnit;

import static java.util.concurrent.TimeUnit.*;

public class CameraTestUtil {

    private static String TAG = "CameraTest";

    private CameraTestUtil() {
        throw new AssertionError();
    }

    /* A helper method to list the contents on the external media files storage directory */
    private static String listGalleryFiles() throws Exception {
        final File externalStorage = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DCIM);
        final String externalStorageDir = externalStorage.toString() + "/Camera";
        final String cmd = "ls " + externalStorageDir;

        final ShellUtil.ShellResult result = ShellUtil.invokeCommand(cmd);

        boolean photosListed = new Wait(
                MILLISECONDS.convert(10L, SECONDS)).until(
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

        org.junit.Assert.assertTrue("Media gallery 'ls' command failed.", photosListed);
        Log.d(TAG, "ls result " + result.stdout);
        return result.stdout;
    }

    /* A helper method to generate either a new photo or video, and then select view it
    * For API <= 25
    */
    private static void createTestFile_v1(UiDevice device, String mode) throws UiObjectNotFoundException, InterruptedException {
        UiObject shutterButton = device.findObject(new UiSelector().resourceId("com.android.camera:id/shutter_button"));
        UiObject fileThumbnail = device.findObject(new UiSelector().resourceId("com.android.camera:id/thumbnail"));

        if (shutterButton.waitForExists(15L)) {
            shutterButton.click();
            if (mode.equals("Videos")) {
                fileThumbnail.waitForExists(15L);
                shutterButton.click();
            }
        }

        TimeUnit.SECONDS.sleep(10);
    }

    /* A helper method to generate either a new photo or video, and then select view it
    * For API >= 26
    */
    private static void createTestFile_v2(UiDevice device, String mode) throws UiObjectNotFoundException, InterruptedException {
        UiObject shutterButton = device.findObject(new UiSelector().resourceId(Res.CAMERA_SHUTTER_BUTTON_RES));
        UiObject fileThumbnail = device.findObject(new UiSelector().resourceId(Res.CAMERA_FILE_THUMBNAIL_RES));

        if (shutterButton.waitForExists(15L)) {
            shutterButton.click();
            if (mode.equals("Video")) {
                fileThumbnail.waitForExists(15L);
                shutterButton.click();
            }
        }

        TimeUnit.SECONDS.sleep(10);
    }

    /* A helper method to perform the common camera actions of both the photo and video tests,
     * based on the mode parameter
     *
     * for API <= 25
     */
    public static boolean useCamera_v1(Instrumentation instrumentation, String mode) throws Exception {
        final UiDevice device = UiDevice.getInstance(instrumentation);

        AppLauncher.launchPath(instrumentation, new String[]{"Camera"});

        UiObject cameraFrame = device.findObject(new UiSelector().resourceId("com.android.camera:id/mode_0"));
        if (cameraFrame.waitForExists(10L)) {
            cameraFrame.click();
        }

        String resId = mode.equals("Camera") ? "com.android.camera:id/mode_camera" :
                "com.android.camera:id/mode_video";
        UiObject ModeButton = device.findObject(new UiSelector()
                .resourceId(resId));
        if (ModeButton.waitForExists(10L)) {
            ModeButton.click();
        }
        else {
            Assert.assertTrue("Button to select mode does not exist", false);
        }

        createTestFile_v1(device, mode);
        deleteTestFile_v1(instrumentation, device, mode);

        AppLauncher.launchPath(instrumentation, new String[]{"Camera"});
        String originalFileList = listGalleryFiles();

        createTestFile_v1(device, mode);

        String fileExt = mode.equals("Camera") ? ".jpg" : ".mp4";
        String newFileList = listGalleryFiles();

        Log.d(TAG, "Test mode is " + mode);
        Log.d(TAG, "Original gallery file list is " + originalFileList);
        Log.d(TAG, "Gallery file list after create is " + newFileList);

        Assert.assertTrue("New file was not added to the gallery",
                !originalFileList.equals(newFileList) && newFileList.contains(fileExt));

        deleteTestFile_v1(instrumentation, device, mode);

        String lastFileList = listGalleryFiles();
        Log.d(TAG, "Gallery file list after delete is " + lastFileList);

        return originalFileList.equals(lastFileList);
    }

    /* A helper method to delete a new photo or video
    *
    * For API <= 25
    */
    private static void deleteTestFile_v1(Instrumentation instrumentation, UiDevice device, String mode) throws Exception {
        device.pressHome();

        AppLauncher.launchPath(instrumentation, new String[]{"Downloads"});

        String desc = mode.equals("Camera") ? "Images" : "Videos";
        UiObject fileButton = device.findObject(new UiSelector().text(desc));

        if ( fileButton.waitForExists(10)) {
            fileButton.click();
            device.findObject(new UiSelector().text("Camera")).click();
        }

        UiObject fileThumbnail = device.findObject(new UiSelector().resourceId("com.android.documentsui:id/icon_thumb"));

        if (fileThumbnail.waitForExists(15L)) {
            fileThumbnail.dragTo(fileThumbnail, 20);
        }

        UiObject trashButton = device.findObject(new UiSelector().resourceId("com.android.documentsui:id/menu_sort"));

        if (trashButton.waitForExists(15L)) {
            trashButton.click();
        }

        UiObject okButton = device.findObject(new UiSelector().resourceId("android:id/button1"));

        if (okButton.waitForExists(15L)) {
            okButton.click();
        }

        device.pressHome();
    }

    /* A helper method to perform the common camera actions of both the photo and video tests,
     * based on the mode parameter
     *
     * For API >= 26
     */
    public static boolean useCamera_v2(Instrumentation instrumentation, String mode) throws Exception {
        final UiDevice device = UiDevice.getInstance(instrumentation);

        AppLauncher.launchPath(instrumentation, new String[]{"Camera"});
        new CameraAccessPermissionsWatcher(device).checkForCondition();

        UiObject cameraFrame = device.findObject(new UiSelector().resourceId(Res.CAMERA_FRAME_RES));
        if (cameraFrame.waitForExists(30L)) {
            cameraFrame.longClick();
            cameraFrame.swipeRight(20);
        }

        new CameraAccessPermissionsWatcher(device).checkForCondition();

        boolean cameraModeButtonExists = device.findObject(new UiSelector()
                .descriptionStartsWith("Switch to")).waitForExists(30L);

        org.junit.Assert.assertTrue("Button to select " + mode + " mode not found", cameraModeButtonExists);

        if (mode.equals("Camera")) {
            device.findObject(new UiSelector().description("Switch to Camera Mode")).click();
        } else {
            device.findObject(new UiSelector().description("Switch to Video Camera")).click();
        }

        createTestFile_v2(device, mode);
        deleteTestFile_v2(instrumentation, device, mode);

        String originalFileList = listGalleryFiles();

        AppLauncher.launchPath(instrumentation, new String[]{"Camera"});
        new CameraAccessPermissionsWatcher(device).checkForCondition();

        createTestFile_v2(device, mode);

        String fileExt = mode.equals("Camera") ? ".jpg" : ".mp4";
        String newFileList = listGalleryFiles();

        Log.d(TAG, "Test mode is " + mode);
        Log.d(TAG, "Original gallery file list is " + originalFileList);
        Log.d(TAG, "Gallery file list after create is " + newFileList);

        org.junit.Assert.assertTrue("New file was not added to the gallery",
                !originalFileList.equals(newFileList) && newFileList.contains(fileExt));

        deleteTestFile_v2(instrumentation, device, mode);

        String lastFileList = listGalleryFiles();
        Log.d(TAG, "Gallery file list after delete is " + lastFileList);

        return originalFileList.equals(lastFileList);
    }

    /* A helper method to delete a new photo or video
    *
    * for API >= 26
    */
    private static void deleteTestFile_v2(Instrumentation instrumentation, UiDevice device, String mode) throws Exception {
        device.pressHome();

        AppLauncher.launchPath(instrumentation, new String[]{"Files"});

        device.findObject(new UiSelector().description("Show roots")).click();

        String desc = mode.equals("Camera") ? "Images" : "Videos";
        UiObject fileButton = device.findObject(new UiSelector().text(desc));

        if ( fileButton.waitForExists(10)) {
            fileButton.click();
            device.findObject(new UiSelector().text("Camera")).click();
        }
        UiObject fileThumbnail = device.findObject(new UiSelector().resourceId("com.android.documentsui:id/icon_thumb"));

        if (fileThumbnail.waitForExists(15L)) {
            fileThumbnail.dragTo(fileThumbnail, 20);
        }

        UiObject trashButton = device.findObject(new UiSelector().resourceId("com.android.documentsui:id/option_menu_list"));

        if (trashButton.waitForExists(15L)) {
            trashButton.click();
        }

        UiObject okButton = device.findObject(new UiSelector().resourceId("android:id/button1"));

        if (okButton.waitForExists(15L)) {
            okButton.click();
        }

        device.pressHome();
    }
}
