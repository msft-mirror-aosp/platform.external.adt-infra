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

package com.android.devtools.systemimage.uitest.smoke.api28;

import android.app.Instrumentation;
import android.support.test.runner.AndroidJUnit4;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiSelector;

import com.android.devtools.systemimage.uitest.annotations.TestInfo;
import com.android.devtools.systemimage.uitest.common.Res;
import com.android.devtools.systemimage.uitest.framework.SystemImageTestFramework;
import com.android.devtools.systemimage.uitest.utils.AppLauncher;
import com.android.devtools.systemimage.uitest.utils.CameraTestUtil;
import com.android.devtools.systemimage.uitest.utils.PackageInstallationUtil;
import com.android.devtools.systemimage.uitest.utils.Wait;
import com.android.devtools.systemimage.uitest.watchers.CameraAccessPermissionsWatcher;

import org.junit.Assert;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.Timeout;
import org.junit.runner.RunWith;

import static org.junit.Assert.assertTrue;

/**
 * Test on shell utility.
 */
@RunWith(AndroidJUnit4.class)
public class CameraTest {
    @Rule
    public final SystemImageTestFramework testFramework = new SystemImageTestFramework();

    @Rule
    public Timeout globalTimeout = Timeout.seconds(240);

    /**
     * Tests the photo capture functionality of the camera application.
     * <p>
     * TT ID: ab5f9585-433b-4261-bd15-5c7136f6127b
     * <p>
     *   <pre>
     *   Test Steps:
     *   1. Start the emulator.
     *   2. Open the Camera application.
     *   3. Take a photo.
     *   4. Delete the photo.
     *   5. Get list of files stored in the Gallery.
     *   6. Reopen the Camera application.
     *   7. Take another photo.
     *   8. Get an updated list of files stored in the Gallery.
     *   9. Delete the photo.
     *   10. Get a final list of files stored in the Gallery.
     *   Verify:
     *      1. Confirm that after taking a photo, the current file list does not match the original file list,
     *          and contains a file with a .jpg extension.
     *      2. Confirm that after deleting the photo, the final file list match the original file list.
     */
    @Test
    @TestInfo(id = "ab5f9585-433b-4261-bd15-5c7136f6127b")
    public void testPhotoCapture() throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();

        boolean photoTestSuccess = CameraTestUtil.useCamera_v2(instrumentation, "Camera");
        Assert.assertTrue("New photo was not deleted from the gallery", photoTestSuccess);
    }

    /**
     * Tests the video capture functionality of the camera application.
     * <p>
     * TT ID: ab5f9585-433b-4261-bd15-5c7136f6127b
     * <p>
     *   <pre>
     *   Test Steps:
     *   1. Start the emulator.
     *   2. Open the Camera application and set to Video.
     *   3. Take a video.
     *   4. Delete the video.
     *   5. Get list of files stored in the Gallery.
     *   6. Reopen the Camera application.
     *   7. Take another video.
     *   8. Get an updated list of files stored in the Gallery.
     *   9. Delete the video.
     *   10. Get a final list of files stored in the Gallery.
     *   Verify:
     *      1. Confirm that after taking a video, the current file list does not match the original video list,
     *          and contains a file with a .mp4 extension.
     *      2. Confirm that after deleting the video, the final file list match the original video list.
     */
    @Test
    @TestInfo(id = "ab5f9585-433b-4261-bd15-5c7136f6127b")
    public void testVideoCapture() throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();

        boolean videoTestSuccess = CameraTestUtil.useCamera_v2(instrumentation, "Video");
        Assert.assertTrue("New video was not deleted from the gallery", videoTestSuccess);
    }

    /**
     * Verifies that the augmented reality application can be installed and launched
     * <p>
     * TT ID: 61ba18b5-cfba-46a7-a3f2-abfc60e40303
     * <p>
     *   <pre>
     *   Test Steps:
     *   1. Start the emulator.
     *   2. Check if AR application is installed, and install if not found.
     *   3. Open the AR application.
     *   Verify:
     *      Confirm that the application launches, and the target text is displayed
     */
    @Test
    @TestInfo(id = "61ba18b5-cfba-46a7-a3f2-abfc60e40303")
    public void launchARApp() throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();
        final UiDevice device = testFramework.getDevice();

        if (!(testFramework.isGoogleApiImage()) || testFramework.isGoogleApiAndPlayImage()) {
            return;
        }

        String testPackageName = "com.google.ar.core.examples.c.helloar";
        String apk = "HelloAr_C.apk";
        String appName = "HelloAR C";
        String result = "";

        boolean isHelloARInstalled = PackageInstallationUtil.
                isPackageInstalled(instrumentation, testPackageName);

        if (!isHelloARInstalled) {
            result = PackageInstallationUtil.installApk(instrumentation, apk);
            isHelloARInstalled = PackageInstallationUtil.
                    isPackageInstalled(instrumentation, testPackageName);
        }

        assertTrue("Application " + apk + " is not installed. Result: " + result,
                isHelloARInstalled);

        AppLauncher.launchPath(instrumentation, new String[]{appName});
        new CameraAccessPermissionsWatcher(device).checkForCondition();

        assertTrue("'Searching for surfaces...' text is not visible",
                new Wait().until(new Wait.ExpectedCondition() {
                    @Override
                    public boolean isTrue() {
                        return device.findObject(new UiSelector().resourceId(
                                Res.GOOGLE_AR_SNACKBAR_RES).text("Searching for surfaces...")).exists();
                    }
                })
        );
    }
}