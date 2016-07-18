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

import com.android.devtools.systemimage.uitest.annotations.TestInfo;
import com.android.devtools.systemimage.uitest.common.Res;
import com.android.devtools.systemimage.uitest.framework.SystemImageTestFramework;
import com.android.devtools.systemimage.uitest.utils.ShellUtil;
import com.android.devtools.systemimage.uitest.utils.AppLauncher;
import com.android.devtools.systemimage.uitest.utils.DeveloperOptionsManager;


import org.hamcrest.Matchers;
import org.junit.Assert;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.Timeout;
import org.junit.runner.RunWith;

import android.app.Instrumentation;
import android.support.test.runner.AndroidJUnit4;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiScrollable;
import android.support.test.uiautomator.UiSelector;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;

/**
 * Test on shell utility.
 */
@RunWith(AndroidJUnit4.class)
public class ShellUtilTest {
    @Rule
    public final SystemImageTestFramework testFramework = new SystemImageTestFramework();

    @Rule
    public Timeout globalTimeout = Timeout.seconds(60);

    /**
     * Tests the integrity of Shell utilities.
     * <p>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p>
     * TR ID: C14578821
     * <p>
     *   <pre>
     *   Test Steps:
     *   1. Start the emulator.
     *   2. From the cmd line, run "adb shell ls /system/bin"
     *   Verify:
     *   Shell utilities are listed in SDK emulator image.
     *   </pre>
     */
    @Test
    @TestInfo(id = "14578821")
    public void testShellUtilIntegrity() throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();
        UiDevice device = UiDevice.getInstance(instrumentation);

        String cmd = "ls /system/bin";
        ShellUtil.ShellResult result = ShellUtil.invokeCommand(cmd);
        // Check if the cmd is executed correctly.
        Assert.assertTrue(result.stderr, result.stderr.length() == 0);

        // Verify the integrity of the shell utilities.
        InputStream inputStream = instrumentation.getTargetContext().getAssets().open("util.txt");
        BufferedReader reader = new BufferedReader(new InputStreamReader(inputStream, "UTF-8"));
        String line;
        StringBuilder util = new StringBuilder();
        while ((line = reader.readLine()) != null) {
            util.append(line).append("\n");
        }
        Assert.assertThat("Failure: The shell util is incomplete.", result.stderr,
                Matchers.isEmptyOrNullString());
    }

    /**
     * Tests take bug report in Developer Options.
     * <p>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p>
     * TR ID: C14581588
     * <p>
     *   <pre>
     *   Test Steps:
     *   1. Start the emulator.
     *   2. Open Settings > Developer Options.
     *   3. Tap on "Take Bug Report"
     *   4. Click on REPORT button.
     *   Verify:
     *   Verify that a bug report is taken by checking for the pnd and zip file in the bugreport
     *     directory.
     *   </pre>
     */
    @Test
    @TestInfo(id = "14581588")
    public void createBugReport() throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();
        UiDevice device = UiDevice.getInstance(instrumentation);
        if (testFramework.getApi() >= 21) {
            if (!DeveloperOptionsManager.isDeveloperOptionsEnabled(instrumentation)) {
                DeveloperOptionsManager.enableDeveloperOptions(testFramework.getInstrumentation());
            } else {
                // Launch the Settings app.
                AppLauncher.launch(instrumentation, "Settings");
                UiScrollable itemList = new UiScrollable(
                        new UiSelector().resourceIdMatches(Res.SETTINGS_LIST_CONTAINER_RES));
                itemList.setAsVerticalList();
                UiObject item = itemList.getChildByText(
                        new UiSelector().className("android.widget.TextView"), "Developer options");
                item.click();
                device.findObject(
                        new UiSelector().text("Take bug report")).clickAndWaitForNewWindow();
                if (device.findObject(new UiSelector().text("Report")).exists()) {
                    device.findObject(new UiSelector().text("Report")).click();
                }
            }

            String cmd = "ls -l cd data/data/com.android.shell/files/bugreports";
            device.executeShellCommand(cmd);
            String result = device.executeShellCommand(cmd);
            String[] arr = result.split(" ");

            boolean containsPng = false;
            boolean containsZip = false;
            String png = "";
            String zip = "";

            for (String ss : arr) {
                if (ss.contains("bugreport") && ss.contains(".png")) {
                    containsPng = true;
                    png = ss;
                }
                if (ss.contains("bugreport") && ss.contains(".zip")) {
                    containsZip = true;
                    zip = ss;
                }
            }

            Assert.assertTrue(
                    "Missing bug report files for png and zip.", containsPng && containsZip);

            // Clean up by deleting all png and zip bug reports. This factors out from having
            // to keep track of the timestamp and date of when the bug report files were created.
            cmd = "remove " + png;
            device.executeShellCommand(cmd);
            cmd = "remove " + zip;
            device.executeShellCommand(cmd);
        }
    }
}
