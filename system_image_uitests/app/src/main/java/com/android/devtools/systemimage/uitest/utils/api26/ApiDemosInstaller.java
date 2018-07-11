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

package com.android.devtools.systemimage.uitest.utils.api26;

import android.app.Instrumentation;
import android.os.Build;
import android.text.TextUtils;

import com.android.devtools.systemimage.uitest.framework.SystemImageTestFramework;

import static org.junit.Assert.assertTrue;

/**
 * Install the ApiDemos application, based on chipset
 */
public class ApiDemosInstaller {

    private ApiDemosInstaller() {
        throw new AssertionError();
    }

    /**
     * Installs API Demos test onto image, if not present
     */

    public static void installApp()
            throws Exception {
        SystemImageTestFramework testFramework = new SystemImageTestFramework();
        Instrumentation instrumentation = testFramework.getInstrumentation();
        String result = "";

        if (testFramework.isGoogleApiImage() || testFramework.isGoogleApiAndPlayImage()) {
            String testPackageName = "com.example.android.apis";
            String testPackageAPK32 = "ApiDemos_x86.apk";
            String testPackageAPK64 = "ApiDemos_x86_64.apk";
            String apk = "";
            boolean isAPIDemoInstalled = false;

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
                apk = TextUtils.join(", ", Build.SUPPORTED_ABIS).contains("64") ?
                        testPackageAPK64 : testPackageAPK32;

                isAPIDemoInstalled = PackageInstallationUtil.isPackageInstalled(instrumentation,
                        testPackageName);

                if (!isAPIDemoInstalled) {
                    result = PackageInstallationUtil.installApk(instrumentation, apk);
                    isAPIDemoInstalled = PackageInstallationUtil.isPackageInstalled(instrumentation,
                            testPackageName);
                }
            }

            assertTrue("Application " + testPackageName + " (" + apk + ") is not installed. Result: " + result, isAPIDemoInstalled);

            SettingsUtil.activate(instrumentation, "Sample Device Admin");
        }
    }
}
