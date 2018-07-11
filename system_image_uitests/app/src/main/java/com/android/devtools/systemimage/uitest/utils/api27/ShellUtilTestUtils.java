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

package com.android.devtools.systemimage.uitest.utils.api27;

import android.support.test.uiautomator.UiDevice;
import android.util.Log;

/**
 * Test on shell utility.
 */
public class ShellUtilTestUtils {
    private final static String TAG = "ShellUtilTest";

    public static void deleteBugReportFiles(String reportDir, UiDevice device) throws Exception {
        Log.i(TAG, "Deleting any existing bug report files");

        // Delete all png and zip bug reports. Delete the files one at a time, as wildcards
        // don't work.
        String lsResult = device.executeShellCommand("ls " + reportDir);
        String[] files = lsResult.split("\\s+");
        String filename = "bugreport.*\\.(png|zip)";

        for (String file : files) {
            if (file.matches(filename)) {
                device.executeShellCommand(String.format("rm %s/%s", reportDir, file));
            }
        }
    }
}
