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
import com.android.devtools.systemimage.uitest.watchers.watcher;

import android.app.Instrumentation;
import android.support.test.uiautomator.UiCollection;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiObjectNotFoundException;
import android.support.test.uiautomator.UiSelector;

import java.util.concurrent.TimeUnit;
import static org.junit.Assert.assertTrue;

public class CameraTestUtil {

    private CameraTestUtil() {
        throw new AssertionError();
    }

    /* A helper method to generate either a new image or video, and then select view it
     */
    private static void createTestFile(UiDevice device, String mode) throws UiObjectNotFoundException, InterruptedException {
        UiObject shutterButton = device.findObject(new UiSelector().resourceId(Res.CAMERA_SHUTTER_BUTTON_RES));
        UiObject fileThumbnail = device.findObject(new UiSelector().resourceId(Res.CAMERA_FILE_THUMBNAIL_RES));

        if (shutterButton.waitForExists(15L)) {
            shutterButton.click();
            if (mode.equals("Videos")) {
                fileThumbnail.waitForExists(15L);
                shutterButton.click();
            }
        }

        TimeUnit.SECONDS.sleep(10);
    }

    /* A helper method to perform the common camera actions of both the photo and video tests,
     * based on the mode parameter
     */
    public static boolean useCamera(Instrumentation instrumentation, String mode, Integer version) throws Exception {
        final UiDevice device = UiDevice.getInstance(instrumentation);

        AppLauncher.launchPath(instrumentation, true, "Camera");
        new watcher(device, Res.CAMERA_ACCESS_PERM_WATCHER_PATTERN).checkForCondition();

        UiObject cameraFrame = device.findObject(new UiSelector().resourceId(Res.CAMERA_FRAME_RES));
        if (cameraFrame.waitForExists(30L)) {
            cameraFrame.longClick();
            cameraFrame.swipeRight(20);
        }

        new watcher(device, Res.CAMERA_ACCESS_PERM_WATCHER_PATTERN).checkForCondition();

        boolean cameraModeButtonExists = device.findObject(new UiSelector()
            .descriptionStartsWith("Switch to")).waitForExists(30L);

        org.junit.Assert.assertTrue("Button to select " + mode + " mode not found", cameraModeButtonExists);

        if (mode.equals("Images")) {
            device.findObject(new UiSelector().description("Switch to Camera Mode")).click();
        } else {
            device.findObject(new UiSelector().description("Switch to Video Camera")).click();
        }

        createTestFile(device, mode);
        if (version == 1) {
            deleteTestFile_v1(instrumentation, device, mode);
        } else {
            deleteTestFile_v2(instrumentation, device, mode);
        }

        AppLauncher.launchPath(instrumentation, true, "Camera");
        new watcher(device, Res.CAMERA_ACCESS_PERM_WATCHER_PATTERN).checkForCondition();

        createTestFile(device, mode);
        if (version == 1) {
            deleteTestFile_v1(instrumentation, device, mode);
        } else {
            deleteTestFile_v2(instrumentation, device, mode);
        }

        return true;
    }

    /* A helper method to delete a new photo or video
     *
     * For API <= 25
     */
    private static void deleteTestFile_v1(Instrumentation instrumentation, UiDevice device, String mode) throws Exception {
        device.pressHome();

        AppLauncher.launchPath(instrumentation, true, "Downloads");

        UiObject fileButton = device.findObject(new UiSelector().text(mode));

        if ( fileButton.waitForExists(10)) {
            fileButton.click();
            device.findObject(new UiSelector().text("Camera")).click();
        }

        int originalGallerySize = new UiCollection(new UiSelector().resourceId(Res.DIRECTORY_LIST_RES))
            .getChildCount(new UiSelector().resourceId(Res.IMAGE_ICON_THUMB_RES));

        UiObject trashButton = device.findObject(new UiSelector().resourceId(Res.OPTION_MENU_SORT_RES));

        if (trashButton.waitForExists(15L)) {
            trashButton.click();
        }

        int finalGallerySize = new UiCollection(new UiSelector().resourceId(Res.DIRECTORY_LIST_RES))
            .getChildCount(new UiSelector().resourceId(Res.IMAGE_ICON_THUMB_RES));

        assertTrue("Delete was not successful", finalGallerySize != originalGallerySize - 1);

        UiObject okButton = device.findObject(new UiSelector().resourceId(Res.ANDROID_BUTTON_ONE));

        if (okButton.waitForExists(15L)) {
            okButton.click();
        }

        device.pressHome();
    }

    /* A helper method to delete a new photo or video
     *
     * for API >= 26
     */
    private static void deleteTestFile_v2(Instrumentation instrumentation, UiDevice device, String mode) throws Exception {
        device.pressHome();

        AppLauncher.launchPath(instrumentation, true, "Files");

        device.findObject(new UiSelector().description("Show roots")).click();

        UiObject fileButton = device.findObject(new UiSelector().text(mode).className("android.widget.TextView"));

        if ( fileButton.waitForExists(10)) {
            fileButton.click();
            UiObject cameraButton = device.findObject(new UiSelector().text("Camera"));
            if ( cameraButton.waitForExists(5L) ) {
                cameraButton.click();
            }
        }
        UiObject fileThumbnail = device.findObject(new UiSelector().resourceId(Res.IMAGE_ICON_THUMB_RES));

        if (fileThumbnail.waitForExists(5L)) {
            fileThumbnail.dragTo(fileThumbnail, 20);
        }

        UiObject trashButton = device.findObject(new UiSelector().resourceIdMatches(Res.OPTION_MENU_LIST_RES));
        if (trashButton.waitForExists(5L)) {
            trashButton.click();
        } else {
            trashButton = device.findObject(new UiSelector().resourceIdMatches(Res.OPTION_MENU_SEARCH_RES));
            if (trashButton.waitForExists(5L)) {
                trashButton.click();
            }
        }

        UiObject okButton = device.findObject(new UiSelector().resourceId(Res.ANDROID_BUTTON_ONE));

        if (okButton.waitForExists(5L)) {
            okButton.click();
        }

        device.pressHome();
    }
}