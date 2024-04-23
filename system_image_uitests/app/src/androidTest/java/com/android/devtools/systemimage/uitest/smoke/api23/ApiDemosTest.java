/*
 * Copyright (c) 2017 The Android Open Source Project
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

package com.android.devtools.systemimage.uitest.smoke.api23;

import android.app.Instrumentation;
import.androidx.test.runner.AndroidJUnit4;
import.androidx.test.uiautomator.UiDevice;
import.androidx.test.uiautomator.UiObject;
import.androidx.test.uiautomator.UiScrollable;
import.androidx.test.uiautomator.UiSelector;

import com.android.devtools.systemimage.uitest.annotations.TestInfo;
import com.android.devtools.systemimage.uitest.common.Res;
import com.android.devtools.systemimage.uitest.framework.SystemImageTestFramework;
import com.android.devtools.systemimage.uitest.utils.ApiDemosInstaller;
import com.android.devtools.systemimage.uitest.utils.ApiDemosTestUtil;
import com.android.devtools.systemimage.uitest.utils.AppLauncher;
import com.android.devtools.systemimage.uitest.utils.PackageInstallationUtil;
import com.android.devtools.systemimage.uitest.utils.SettingsUtil;

import junit.framework.Assert;

import org.junit.After;
import org.junit.Before;
import org.junit.Ignore;
import org.junit.Rule;
import org.junit.Test;
import org.junit.runner.RunWith;

import java.util.concurrent.TimeUnit;

/**
 * Test to verify the functionality of "PASSWORD CONTROLS".
 */
@RunWith(AndroidJUnit4.class)
public class ApiDemosTest {

    @Rule
    public final SystemImageTestFramework testFramework = new SystemImageTestFramework();

    private Instrumentation instrumentation = testFramework.getInstrumentation();
    private UiDevice device = testFramework.getDevice();

    @Before
    public void activateDeviceAdmin() throws Exception {
        ApiDemosInstaller.installApp("Security", "Device administrators");
    }

    /**
     * To test if the password is adhering to the conditions set in "PASSWORD QUALITY".
     * <p>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p>
     * TR ID: T144630615
     * <p>
     *   <pre>
     *   Test Steps:
     *   1. Goto API Demos —> App —> Device Admin —> Password quality.
     *   2. Set Password Quality fields by following following rules:
     *      Password quality: Complex Minimum.
     *      Minimum Length: 6 Minimum.
     *      Minimum Letters: 1.
     *      Minimum Numeric: 1.
     *      Minimum Lower case: 1.
     *      Minimum Upper Case: 1.
     *      Minimum Symbols: 1.
     *      Minimum non-Letters: 1.
     *   Verify:
     *   1. Settings —> Security —> Screen Lock —> Set it to Password.
     *      You are asked to set password according to rules mentioned above.
     *    </pre>
     *
     */
    @Test
    @TestInfo(id = "T144630615")
    @Ignore("Disable due to b/146500804 until further clarification.")
    public void testPasswordQuality() throws Exception {
        boolean isAPIDemoInstalled = PackageInstallationUtil.isPackageInstalled(instrumentation,
                "com.example.android.apis");
        if (isAPIDemoInstalled) {
            AppLauncher.launch(instrumentation, "API Demos");
            for (int i = 0; i < 5; i++) {
                device.pressBack();
            }
            AppLauncher.launch(instrumentation, "API Demos");

            UiScrollable itemList =
                    new UiScrollable(new UiSelector().resourceId(Res.ANDROID_LIST_RES));
            itemList.setAsVerticalList();
            Assert.assertTrue(itemList.exists());
            UiObject appItem = itemList.getChildByText(
                    new UiSelector().className("android.widget.TextView"), "App");
            appItem.waitForExists(TimeUnit.SECONDS.toMillis(3L));
            appItem.click();
            UiObject deviceAdminItem = itemList.getChildByText(
                    new UiSelector().className("android.widget.TextView"), "Device Admin");
            deviceAdminItem.waitForExists(TimeUnit.SECONDS.toMillis(3L));
            deviceAdminItem.click();
            UiObject passwordQualityItem = itemList.getChildByText(
                    new UiSelector().className("android.widget.TextView"), "Password quality");
            passwordQualityItem.waitForExists(TimeUnit.SECONDS.toMillis(3L));
            passwordQualityItem.clickAndWaitForNewWindow(3L);

            passwordQualityItem = itemList.getChildByText(
                    new UiSelector().className("android.widget.RelativeLayout"), "Password quality");
            passwordQualityItem.waitForExists(TimeUnit.SECONDS.toMillis(3L));
            passwordQualityItem.clickAndWaitForNewWindow(3L);

            // Set the criteria for password to 'Complex' type.
            device.findObject(new UiSelector().text("Complex")).clickAndWaitForNewWindow();

            // Set minimum length to 6.
            ApiDemosTestUtil.setPasswordCriteria("Minimum length", "6", device);

            // Set minimum letters to 1.
            ApiDemosTestUtil.setPasswordCriteria("Minimum letters", "1", device);

            // Set minimum numerics to 1.
            ApiDemosTestUtil.setPasswordCriteria("Minimum numeric", "1", device);

            // Set minimum lower case letters to 1.
            ApiDemosTestUtil.setPasswordCriteria("Minimum lower case", "1", device);

            // Set minimum upper case letters  to 1.
            ApiDemosTestUtil.setPasswordCriteria("Minimum upper case", "1", device);

            // Set minimum special symbols to 1.
            ApiDemosTestUtil.setPasswordCriteria("Minimum symbols", "1", device);

            // Set minimum non-letter to 1.
            ApiDemosTestUtil.setPasswordCriteria("Minimum non-letter", "1", device);

            //Verify that setting the password meets the "PASSWORD QUALITY" criteria.
            ApiDemosTestUtil.verifyPasswordQuality(instrumentation, device, "Security", "Continue");
        }
    }

    @After
    public void restoreState() throws Exception{
        //Deactivate "Device Admin" to restore the state.
        SettingsUtil.deactivate(instrumentation, "Sample Device Admin", "Security", "Device administrators");
    }
}