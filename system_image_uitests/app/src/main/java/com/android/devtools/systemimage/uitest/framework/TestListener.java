/*
* Copyright (C) 2024 The Android Open Source Project
* Licensed under the Apache License, Version 2.0 (the "License");
* you may not use this file except in compliance with the License.
* You may obtain a copy of the License at
*
*  http://www.apache.org/licenses/LICENSE-2.0
*
* Unless required by applicable law or agreed to in writing, software
* distributed under the License is distributed on an "AS IS" BASIS,
* WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
* See the License for the specific language governing permissions and
* limitations under the License.
*/

package com.android.devtools.systemimage.uitest.framework;
import com.android.devtools.systemimage.uitest.listeners.IgnoredTestsReport;

import org.junit.runner.Description;
import org.junit.runner.notification.Failure;
import org.junit.runner.notification.RunListener;
import org.junit.runner.Result;

/**
 * Base Listener for Delegating Events to Custom Test Listeners
 */
public class TestListener extends RunListener {
    private final RunListener[] delegates;

    public TestListener() {
        // Initialize the custom listeners (processed in order listed)
        this.delegates = new RunListener[] {
                new IgnoredTestsReport()
        };
    }

    @Override
    public void testStarted(Description description) throws Exception {
        for (RunListener listener : delegates) {
            listener.testStarted(description);
        }
    }

    @Override
    public void testFinished(Description description) throws Exception {
        for (RunListener listener : delegates) {
            listener.testFinished(description);
        }
    }

    @Override
    public void testIgnored(Description description) throws Exception {
        for (RunListener listener : delegates) {
            listener.testIgnored(description);
        }
    }

    @Override
    public void testFailure(Failure failure) throws Exception {
        for (RunListener listener : delegates) {
            listener.testFailure(failure);
        }
    }

    @Override
    public void testRunFinished(Result result) throws Exception {
        for (RunListener listener : delegates) {
            listener.testRunFinished(result);
        }
    }
}
