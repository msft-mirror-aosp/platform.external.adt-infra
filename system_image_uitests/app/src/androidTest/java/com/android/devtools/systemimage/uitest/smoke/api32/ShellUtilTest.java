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

package com.android.devtools.systemimage.uitest.smoke.api32;

import android.app.Instrumentation;
import androidx.test.runner.AndroidJUnit4;
import androidx.test.uiautomator.UiDevice;
import androidx.test.uiautomator.UiObject;
import androidx.test.uiautomator.UiObjectNotFoundException;
import androidx.test.uiautomator.UiScrollable;
import androidx.test.uiautomator.UiSelector;
import android.util.Log;

import com.android.devtools.systemimage.uitest.annotations.TestInfo;
import com.android.devtools.systemimage.uitest.common.Res;
import com.android.devtools.systemimage.uitest.framework.SystemImageTestFramework;
import com.android.devtools.systemimage.uitest.utils.AppLauncher;
import com.android.devtools.systemimage.uitest.utils.DeveloperOptionsManager;
import com.android.devtools.systemimage.uitest.utils.ShellUtil;
import com.android.devtools.systemimage.uitest.utils.Wait;

import org.hamcrest.Matchers;
import org.junit.Assert;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.Timeout;
import org.junit.runner.RunWith;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.TimeUnit;

import static org.junit.Assert.assertTrue;


/**
 * Test on shell utility.
 */
@RunWith(AndroidJUnit4.class)
public class ShellUtilTest {
    private final String TAG = "ShellUtilTest";

    @Rule
    public final SystemImageTestFramework testFramework = new SystemImageTestFramework();

    @Rule
    public Timeout globalTimeout = Timeout.seconds(240);

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

        String cmd = "ls /system/bin";
        ShellUtil.ShellResult result = ShellUtil.invokeCommand(cmd);
        // Check if the cmd is executed correctly.
        Assert.assertEquals(result.stderr, 0, result.stderr.length());

        // Verify the integrity of the shell utilities.
        InputStream inputStream = instrumentation.getTargetContext().getAssets().open("util.txt");
        BufferedReader reader = new BufferedReader(new InputStreamReader(inputStream, StandardCharsets.UTF_8));
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
     *   Verify that a bug report is taken by checking for the png and zip file in the bugreport
     *     directory.
     *   </pre>
     */
    @Test
    @TestInfo(id = "14581588")
    public void createBugReport() throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();
        final UiDevice device = UiDevice.getInstance(instrumentation);
        final String BUG_REPORT_DIR = "/bugreports";

        ShellUtil.deleteBugReportFiles(BUG_REPORT_DIR, testFramework);

        AppLauncher.launch(instrumentation, "Settings");
        UiScrollable recyclerView = new UiScrollable(new UiSelector().resourceId(Res.ANDROID_SETTING_LIST_RES));

        if (!AppLauncher.scrollAndClick(device, recyclerView,"System", "Developer options")) {
            try {
                AppLauncher.launch(instrumentation, "Settings");
                AppLauncher.scrollAndClick(device, recyclerView,"About emulated device");
            } catch (UiObjectNotFoundException e) {
                AppLauncher.launch(instrumentation, "Settings");
                assertTrue("Information About Device not found", AppLauncher.scrollAndClick(device, recyclerView,"About phone"));
            }
            DeveloperOptionsManager.enableOptions(instrumentation, new DeveloperOptionsManager.SwipeNavigationStrategy(), false);
            AppLauncher.launch(instrumentation, "Settings");
            assertTrue("Developer Options settings not found", AppLauncher.scrollAndClick(device, recyclerView,"System", "Developer options"));
        }

        UiObject developerOptionsButton = device.findObject(
                new UiSelector().text("Developer Option"));
        developerOptionsButton.waitUntilGone(10000L);

        UiObject bugReportButton = device.findObject(
                new UiSelector().text("Bug report"));
        assertTrue("Bug report button not found", bugReportButton.waitForExists(10000L));
        bugReportButton.clickAndWaitForNewWindow();

        UiObject fullReportButton = device.findObject(new UiSelector().textMatches("(?i)full report(?-i)"));
        if (fullReportButton.exists()) {
            fullReportButton.clickAndWaitForNewWindow();
        }

        UiObject reportButton = device.findObject(new UiSelector().textMatches("(?i)report(?-i)"));
        if (reportButton.exists()) {
            reportButton.click();
        }

        boolean gotPngAndZip = new Wait(
                TimeUnit.MILLISECONDS.convert(30L, TimeUnit.SECONDS)).until(
                () -> {
                    String result = device.executeShellCommand("ls " + BUG_REPORT_DIR);
                    Log.d(TAG, "ls result " + result);
                    return result.matches("(?s).*bugreport.*\\.png.*")
                            && result.matches("(?s).*bugreport.*\\.zip.*");
                });
        assertTrue("Missing bug report files for png and zip.", gotPngAndZip);

        ShellUtil.deleteBugReportFiles(BUG_REPORT_DIR, testFramework);
    }
}
