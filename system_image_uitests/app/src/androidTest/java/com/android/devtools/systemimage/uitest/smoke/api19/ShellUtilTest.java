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

package com.android.devtools.systemimage.uitest.smoke.api19;

import android.app.Instrumentation;
import android.support.test.runner.AndroidJUnit4;

import com.android.devtools.systemimage.uitest.annotations.TestInfo;
import com.android.devtools.systemimage.uitest.framework.SystemImageTestFramework;
import com.android.devtools.systemimage.uitest.utils.ShellUtil;

import org.hamcrest.Matchers;
import org.junit.Assert;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.Timeout;
import org.junit.runner.RunWith;

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
    public Timeout globalTimeout = Timeout.seconds(120);

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
}