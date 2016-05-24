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

import com.android.devtools.systemimage.uitest.framework.SystemImageTestFramework;
import com.android.devtools.systemimage.uitest.utils.AppLauncher;
import com.android.devtools.systemimage.uitest.utils.AppManager;

import org.junit.Rule;
import org.junit.Test;
import org.junit.runner.RunWith;

import android.app.Instrumentation;
import android.support.test.runner.AndroidJUnit4;

/**
 * Test for app interactions.
 */
@RunWith(AndroidJUnit4.class)
public class AppTest {
    @Rule
    public final SystemImageTestFramework testFramework = new SystemImageTestFramework();

    /**
     * Verifies the renderscript app runs on the emulator.
     * <p>
     * The test installs, launches, and uninstalls the app.
     * <p>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p>
     * TR ID: C14578823
     * <p>
     *   <pre>
     *   Test Steps:
     *   1. Start the emulator.
     *   2. Install HelloComputer app.
     *   3. Open the app.
     *   Verify:
     *   App runs on the emulator. Image of a leaf is displayed on the emulator.
     *   </pre>
     */
    @Test
    public void testAppInstallAndLaunch() throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();

        AppManager.installApp(instrumentation, "HelloCompute.apk");
        AppLauncher.launch(instrumentation, "RsHelloCompute");
        AppManager.uninstallApp(instrumentation, "RsHelloCompute", null);
    }
}
