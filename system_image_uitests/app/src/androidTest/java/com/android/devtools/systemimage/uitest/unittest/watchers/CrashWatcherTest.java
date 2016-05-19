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

package com.android.devtools.systemimage.uitest.unittest.watchers;

import com.android.devtools.systemimage.uitest.framework.SystemImageTestFramework;
import com.android.devtools.systemimage.uitest.utils.AppLauncher;
import com.android.devtools.systemimage.uitest.utils.AppManager;

import org.hamcrest.core.StringStartsWith;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.ExpectedException;
import org.junit.runner.RunWith;
import org.junit.runners.JUnit4;

import android.app.Instrumentation;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiSelector;

/**
 * Unit test on {@link com.android.devtools.systemimage.uitest.watchers.CrashWatcher CrashWatcher}.
 * <p>
 * This unit test is expected to throw an assertion error. Note that we particularly use JUnit4 to
 * expect the exception message because AndroidJunit4 cannot expect the message correctly due to
 * an unknown reason.
 */
@RunWith(JUnit4.class)
public class CrashWatcherTest {
    @Rule
    public final ExpectedException exception = ExpectedException.none();
    @Rule
    public final SystemImageTestFramework testFramework = new SystemImageTestFramework();

    @Test
    public void testCrashWatcher() throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();
        UiDevice device = testFramework.getDevice();

        // CrashWatcher has been registered in SystemImageTestFramework#apply()
        // Here we only need to trigger the crash event, and expect the assertion failure.
        exception.expectMessage(StringStartsWith.startsWith("Caught an application crash."));
        AppManager.installApp(instrumentation, "CrashExample.apk");
        AppLauncher.launch(instrumentation, "DisplayingBitmaps");
        // Catch the crash by clicking an image.
        device.findObject(new UiSelector().className("android.widget.ImageView")).click();
    }
}
