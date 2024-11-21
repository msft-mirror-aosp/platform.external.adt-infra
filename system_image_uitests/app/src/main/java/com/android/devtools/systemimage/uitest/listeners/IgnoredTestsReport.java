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

package com.android.devtools.systemimage.uitest.listeners;

import android.content.pm.PackageManager;
import android.os.Environment;
import androidx.test.InstrumentationRegistry;

import org.junit.Assert;
import org.junit.Ignore;
import org.junit.runner.Description;
import org.junit.runner.Result;
import org.junit.runner.notification.RunListener;

import org.dom4j.Document;
import org.dom4j.DocumentHelper;
import org.dom4j.Element;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Custom JUnit RunListener for tracking and generating a XML report for ignored tests.
 *
 * Tracks information about ignored tests and generates an XML report with details
 * such as class name, method name, and ignore reason, after the test run finishes.
 */
public class IgnoredTestsReport extends RunListener {

    private List<Map<String, String>> ignoredTests = new ArrayList<>();

    @Override
    public void testIgnored(Description description) throws Exception {
        super.testIgnored(description);

        // Check if the @Ignore annotation is present
        if (description.getAnnotation(Ignore.class) != null) {
            String className = description.getClassName();
            String classSimpleName = description.getTestClass().getSimpleName();
            String methodName = description.getMethodName();
            Ignore ignoreAnnotation = description.getAnnotation(Ignore.class);
            String ignoreReason = (ignoreAnnotation != null) ? ignoreAnnotation.value() : "n/a";

            Map<String, String> ignoredTestInfo = new HashMap<>();
            ignoredTestInfo.put("className", className);
            ignoredTestInfo.put("classSimpleName", classSimpleName);
            ignoredTestInfo.put("methodName", methodName);
            ignoredTestInfo.put("ignoreReason", ignoreReason);

            ignoredTests.add(ignoredTestInfo);
        }
    }

    @Override
    public void testRunFinished(Result result) throws Exception {
        super.testRunFinished(result);
        if (!ignoredTests.isEmpty()) generateXmlSkipReport();
    }

    /**
     * Generate an XML report for the ignored tests
     * The XML file will contain details such as class name, method name,
     * and ignore reason (if available) for each ignored test.
     */
    private void generateXmlSkipReport() {
        Document document = DocumentHelper.createDocument();
        Element root = document.addElement("ignoredTests");

        for (Map<String, String> ignoredTest : ignoredTests) {
            Element testElement = root.addElement("ignoredTest");
            testElement.addElement("className").addText(ignoredTest.get("className"));
            testElement.addElement("classSimpleName").addText(ignoredTest.get("classSimpleName"));
            testElement.addElement("methodName").addText(ignoredTest.get("methodName"));
            testElement.addElement("ignoreReason").addText(ignoredTest.get("ignoreReason"));
        }

        checkStoragePermissions();
        String classSimpleName = ignoredTests.get(0).get("classSimpleName");
        File externalStorageDocumentsDir =
                new File(Environment.getExternalStorageDirectory().getPath(), "Documents");
        File logDir = new File(externalStorageDocumentsDir, "Logs");
        if (!logDir.exists())
            logDir.mkdir();
        File classLogDir = new File(logDir.getPath(), classSimpleName);
        classLogDir.mkdirs();

        try (FileWriter filewriter = new FileWriter(new File(classLogDir, "ignored_tests.xml"))) {
            document.write(filewriter);
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    /**
     * Check the external storage state and permission for writing.
     * Throw an AssertionError if the conditions are not met.
    */
    private void checkStoragePermissions() {
        // Check if the external storage is mounted and not read-only
        String state = Environment.getExternalStorageState();
        boolean isWritable = Environment.MEDIA_MOUNTED.equals(state) &&
                            !Environment.MEDIA_MOUNTED_READ_ONLY.equals(state);
        Assert.assertTrue("Failed to write to external storage.", isWritable);

        // Check if the app has the WRITE_EXTERNAL_STORAGE permission
        String permission = "android.permission.WRITE_EXTERNAL_STORAGE";
        int res = InstrumentationRegistry.getInstrumentation().getContext()
                                         .checkCallingOrSelfPermission(permission);
        boolean hasWritablePermission = (res == PackageManager.PERMISSION_GRANTED);
        Assert.assertTrue("Failed to acquire permission.", hasWritablePermission);
    }
}
