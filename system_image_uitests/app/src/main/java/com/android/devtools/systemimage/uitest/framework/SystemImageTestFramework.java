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

package com.android.devtools.systemimage.uitest.framework;

import com.android.devtools.systemimage.uitest.watchers.AndroidLauncherWelcomeClingWatcher;
import com.android.devtools.systemimage.uitest.watchers.AndroidWelcomeClingWatcher;
import com.android.devtools.systemimage.uitest.watchers.CrashWatcher;
import com.android.devtools.systemimage.uitest.watchers.LockScreenWatcher;

import org.junit.Assert;
import org.junit.rules.TestRule;
import org.junit.runner.Description;
import org.junit.runners.model.Statement;

import android.app.Instrumentation;
import android.content.Context;
import android.os.Bundle;
import android.support.test.InstrumentationRegistry;
import android.support.test.uiautomator.UiDevice;
import android.telephony.TelephonyManager;

/**
 * System image test framework that standardizes a test's initialization and finalization.
 */
public class SystemImageTestFramework implements TestRule {

    private final Instrumentation mInstrumentation = InstrumentationRegistry.getInstrumentation();
    private final UiDevice mDevice = UiDevice.getInstance(mInstrumentation);
    private final Bundle args = InstrumentationRegistry.getArguments();

    public Instrumentation getInstrumentation() {
        return mInstrumentation;
    }

    public UiDevice getDevice() {
        return mDevice;
    }

    public String getApi() {
        return args.getString("api");
    }

    public String getAbi() {
        return args.getString("abi");
    }

    public String getTag() {
        return args.getString("tag");
    }

    public String getOrigin() {
        return args.getString("origin");
    }

    @Override
    public Statement apply(final Statement base, final Description description) {
        return new Statement() {
            @Override
            public void evaluate() throws Throwable {
                mDevice.wakeUp();
                Assert.assertTrue("Failed to wake up the device.", mDevice.isScreenOn());
                // Press "Home" to dismiss a lock screen if any.
                mDevice.pressMenu();
                mDevice.pressHome();

                CrashWatcher crashWatcher =
                        new CrashWatcher(
                                mDevice,
                                mInstrumentation.getTargetContext().getExternalFilesDir(null)
                        );
                mDevice.registerWatcher(CrashWatcher.class.getName(), crashWatcher);
                mDevice.registerWatcher(
                        LockScreenWatcher.class.getName(),
                        new LockScreenWatcher(mDevice)
                );
                mDevice.registerWatcher(
                        AndroidWelcomeClingWatcher.class.getName(),
                        new AndroidWelcomeClingWatcher(mDevice)
                );
                mDevice.registerWatcher(
                        AndroidLauncherWelcomeClingWatcher.class.getName(),
                        new AndroidLauncherWelcomeClingWatcher(mDevice)
                );

                base.evaluate();

                // Must check the crash watcher again for finalization,
                // or could miss a crash if it happens at the end of a test case.
                crashWatcher.checkForCondition();

                mDevice.pressHome();

                mDevice.removeWatcher(CrashWatcher.class.getName());
                mDevice.removeWatcher(LockScreenWatcher.class.getName());
                mDevice.removeWatcher(AndroidWelcomeClingWatcher.class.getName());
                mDevice.removeWatcher(AndroidLauncherWelcomeClingWatcher.class.getName());
            }
        };
    }

}
