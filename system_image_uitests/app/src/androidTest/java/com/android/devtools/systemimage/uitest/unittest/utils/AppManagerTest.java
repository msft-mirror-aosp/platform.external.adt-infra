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

package com.android.devtools.systemimage.uitest.unittest.utils;

import com.android.devtools.systemimage.uitest.framework.SystemImageTestFramework;
import com.android.devtools.systemimage.uitest.utils.AppManager;

import org.junit.Assert;
import org.junit.Rule;
import org.junit.Test;
import org.junit.runner.RunWith;

import android.app.Instrumentation;
import android.support.test.runner.AndroidJUnit4;

/**
 * Unit test on {@link AppManager}.
 */
@RunWith(AndroidJUnit4.class)
public class AppManagerTest {
    @Rule
    public final SystemImageTestFramework testFramework = new SystemImageTestFramework();

    @Test
    public void testAppManager() throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();

        AppManager.installApp(instrumentation, "FredVPN.apk");
        AppManager.installApp(instrumentation, "HelloCompute.apk");
        Assert.assertTrue(
                "Failed to find FredVPN.",
                AppManager.isAppInstalled(instrumentation, "TestVPN", null)
        );
        Assert.assertTrue(
                "Failed to find RsHelloCompute.",
                AppManager.isAppInstalled(instrumentation, "RsHelloCompute", null)
        );
        AppManager.uninstallApp(instrumentation, "TestVPN", null);
        AppManager.uninstallApp(instrumentation, "RsHelloCompute", null);
    }
}
