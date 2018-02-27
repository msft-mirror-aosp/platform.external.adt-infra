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

package com.android.devtools.systemimage.uitest.smoke;

import android.app.Instrumentation;
import android.os.Environment;
import android.support.test.runner.AndroidJUnit4;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiSelector;
import android.util.Log;

import com.android.devtools.systemimage.uitest.annotations.TestInfo;
import com.android.devtools.systemimage.uitest.common.Res;
import com.android.devtools.systemimage.uitest.framework.SystemImageTestFramework;
import com.android.devtools.systemimage.uitest.utils.AppLauncher;
import com.android.devtools.systemimage.uitest.utils.ShellUtil;
import com.android.devtools.systemimage.uitest.utils.Wait;
import com.android.devtools.systemimage.uitest.watchers.CameraAccessPermissionsWatcher;

import org.junit.Assert;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.Timeout;
import org.junit.runner.RunWith;

import java.io.File;
import java.util.concurrent.TimeUnit;

/**
 * Test on shell utility.
 */
@RunWith(AndroidJUnit4.class)
public class CameraTest {
    private final String TAG = "CameraTest";
    private final File dcimStorage = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DCIM);
    private final String photoDir = dcimStorage.toString() + "/Camera";

    @Rule
    public final SystemImageTestFramework testFramework = new SystemImageTestFramework();

    @Rule
    public Timeout globalTimeout = Timeout.seconds(120);

    /**
     * Tests the camera photo capture feature.
     * <p>
     * TT ID: ab5f9585-433b-4261-bd15-5c7136f6127b
     * <p>
     *   <pre>
     *   Test Steps:
     *   1. Start the emulator.
     *   2. Get list of photos already stored in the Gallery.
     *   3. Open the Camera application.
     *   4. Take a photo.
     *   5. Get an updated list of photos stored in the Gallery.
     *   6. Click on the photo thumbnail.
     *   7. Delete the photo.
     *   8. Get a final list of photos stored in the Gallery.
     *   Verify:
     *      1. Confirm that after taking a photo, the current photo list does not match the original photo list.
     *      2. Confirm that after deleting the photo, the final photo list does match the original photo list.
     */
    @Test
    @TestInfo(id = "ab5f9585-433b-4261-bd15-5c7136f6127b")
    public void testPhotoCapture() throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();
        final UiDevice device = UiDevice.getInstance(instrumentation);
        String originalPhotoList = listPhotos(instrumentation);

        if (testFramework.getApi() >= 24) {
            AppLauncher.launchPath(instrumentation, new String[]{"Camera"});
            new CameraAccessPermissionsWatcher(device).checkForCondition();
            UiObject shutterButton = device.findObject(new UiSelector().resourceId(Res.CAMERA_SHUTTER_BUTTON_RES));
            if (shutterButton.waitForExists(3L)) {
                shutterButton.clickAndWaitForNewWindow();
            }

            String newPhotoList = listPhotos(instrumentation);
            Assert.assertFalse("Photo gallery has not been updated", originalPhotoList.equals(newPhotoList));

            UiObject photoThumbnail = device.findObject(new UiSelector().resourceId(Res.CAMERA_PHOTO_THUMBNAIL_RES));
            if (photoThumbnail.waitForExists(3L)) {
                photoThumbnail.clickAndWaitForNewWindow();
            }

            UiObject trashCan = device.findObject(new UiSelector().resourceId(Res.CAMERA_PHOTO_DELETE_RES));
            if (trashCan.waitForExists(3L)) {
                trashCan.click();
            }
            device.pressBack();
            device.pressHome();

            String lastPhotoList = listPhotos(instrumentation);
            Assert.assertTrue("New photo was not deleted", originalPhotoList.equals(lastPhotoList));
        }
    }

    private String listPhotos(Instrumentation instrumentation) throws Exception {
        final UiDevice device = UiDevice.getInstance(instrumentation);
        final String cmd = "ls " + photoDir;

        final ShellUtil.ShellResult result = ShellUtil.invokeCommand(cmd);

        boolean photosListed = new Wait(TimeUnit.MILLISECONDS.convert(10L, TimeUnit.SECONDS)).until(
                new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() throws Exception {
                        return result != null && result.stderr != null && result.stderr.length() == 0;
                    }
                });
        Assert.assertTrue("Photo ls command failed", photosListed);
        Log.d(TAG, "ls result " + result.stdout);
        return result.stdout;
    }
}