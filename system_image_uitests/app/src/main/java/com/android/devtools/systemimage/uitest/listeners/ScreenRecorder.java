/*
 * Copyright (c) 2024 The Android Open Source Project
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.android.devtools.systemimage.uitest.listeners;
import android.util.Log;
import androidx.test.InstrumentationRegistry;
import androidx.test.uiautomator.UiDevice;
import org.junit.runner.notification.RunListener;
import com.android.devtools.systemimage.uitest.annotations.ScreenRecord;
import com.android.devtools.systemimage.uitest.framework.SystemImageTestFramework;
import org.junit.runner.Description;
import java.io.File;

/**
 * Manages screen recording for tests annotated with {@code @ScreenRecord}.
 *
 * <p>Uses ADB to start an independent thread for screen recording during the
 * test method execution. The recording is automatically stopped at test teardown,
 * creating sequential 180-seconds MP4 videos, which are saved in the method's log
 * folder.</p>
 */
public class ScreenRecorder extends RunListener {

    private final static String TAG = "ScreenRecorder";
    private UiDevice mDevice = UiDevice.getInstance(InstrumentationRegistry.getInstrumentation());
    private boolean recording = false;
    private File mp4File;
    private String fileName = "screen_recording";

    private void startRecording(Description description) {
        String className = description.getTestClass().getSimpleName();
        String methodName = description.getMethodName();
        File logDir = SystemImageTestFramework.getLoggingDir(className, methodName);
        recording = true;
        new Thread(() -> {
            int c = 0;
            String fileCounter = "";
            while (recording) {
                mp4File = new File(logDir, fileName + fileCounter + ".mp4");
                mp4File.delete();
                try {
                    String[] cmd = {"screenrecord", mp4File.getAbsolutePath()};
                    Log.i(TAG, "Launching screenrecord ...");
                    mDevice.executeShellCommand(String.join(" ", cmd));
                } catch (Exception e) {
                    Log.e(TAG, e.getMessage());
                }
                c += 1;
                fileCounter = "_" + c;
            }
        }).start();
    }

    private void stopRecording() {
        if (recording) {
            recording = false;
            Log.i(TAG, "Terminating screenrecord ...");
            try {
                String[] cmd = {"pkill", "-l", "2", "screenrecord"};
                Runtime.getRuntime().exec(cmd);
            } catch (Exception e) {
                Log.e(TAG, e.getMessage());
            }
        }
    }

    @Override
    public void testStarted(Description description) throws Exception {
        if (description.getAnnotation(ScreenRecord.class) != null) {
            Log.i(TAG, "ScreenRecorder SetUp");
            startRecording(description);
        }
    }

    @Override
    public void testFinished(Description description) throws Exception {
        if (description.getAnnotation(ScreenRecord.class) != null) {
            Log.d(TAG, "ScreenRecorder tearDown");
            stopRecording();
        }
    }
}
