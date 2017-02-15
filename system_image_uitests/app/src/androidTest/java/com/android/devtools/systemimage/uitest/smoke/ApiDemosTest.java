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

package com.android.devtools.systemimage.uitest.smoke;

import android.app.Instrumentation;
import android.support.test.runner.AndroidJUnit4;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiScrollable;
import android.support.test.uiautomator.UiSelector;

import com.android.devtools.systemimage.uitest.annotations.TestInfo;
import com.android.devtools.systemimage.uitest.common.Res;
import com.android.devtools.systemimage.uitest.framework.SystemImageTestFramework;
import com.android.devtools.systemimage.uitest.utils.AppLauncher;
import com.android.devtools.systemimage.uitest.utils.SettingsUtil;

import junit.framework.Assert;

import org.junit.After;
import org.junit.Before;
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

    @Before
    public void activateDeviceAdmin() throws Exception{
        Instrumentation instrumentation = testFramework.getInstrumentation();
        UiDevice device = testFramework.getDevice();
        SettingsUtil.activate(instrumentation, "Sample Device Admin");
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
     *   Verify:
     *   1. Settings —> Security —> Screen Lock —> Set it to Password.
     *      You are asked to set password according to rules mentioned above.
     *    </pre>
     *
     */
    @Test
    @TestInfo(id = "T144630615")
    public void testPasswordQuality() throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();
        UiDevice device = testFramework.getDevice();
        UiObject editText;
        AppLauncher.launch(instrumentation, "API Demos");
        UiScrollable itemList =
                new UiScrollable(new UiSelector().resourceId(Res.ANDROID_LIST_RES));
        itemList.setAsVerticalList();
        Assert.assertTrue(itemList.exists());
        itemList.getChildByText(new UiSelector().className("android.widget.TextView"),
                "App").clickAndWaitForNewWindow();
        itemList.getChildByText(new UiSelector().className("android.widget.TextView"),
                "Device Admin").clickAndWaitForNewWindow();
        itemList.getChildByText(new UiSelector().className("android.widget.TextView"),
                "Password quality").clickAndWaitForNewWindow();

        //Specify list items to choose from "PASSWORD QUALITY".
        itemList.getChildByText(
                new UiSelector().className("android.widget.RelativeLayout"), "Password quality")
                .clickAndWaitForNewWindow();
        device.findObject(new UiSelector().text("Complex")).clickAndWaitForNewWindow();

        itemList.getChildByText(new UiSelector().className("android.widget.TextView"),
                "Minimum length").clickAndWaitForNewWindow();
        editText = device.findObject(new UiSelector().className("android.widget.EditText"));
        editText.setText("6");
        device.findObject(new UiSelector().text("OK")).click();

        itemList.getChildByText(new UiSelector().className("android.widget.TextView"),
                "Minimum letters").clickAndWaitForNewWindow();
        editText = device.findObject(new UiSelector().className("android.widget.EditText"));
        editText.setText("1");
        device.findObject(new UiSelector().text("OK")).click();

        itemList.getChildByText(new UiSelector().className("android.widget.TextView"),
                "Minimum numeric").clickAndWaitForNewWindow();
        editText = device.findObject(new UiSelector().className("android.widget.EditText"));
        editText.setText("1");
        device.findObject(new UiSelector().text("OK")).click();

        //Verify that setting the password meets the "PASSWORD QUALITY" criteria.
        verifyPasswordQuality(instrumentation, device);

    }

    /**
     *  Verify the functionality of "PASSWORD QUALITY".
     */
    private void verifyPasswordQuality(
            Instrumentation instrumentation, UiDevice device) throws Exception {
        Assert.assertTrue(SettingsUtil.openItem(instrumentation, "Security"));

        UiScrollable itemList =
                new UiScrollable(
                        new UiSelector().resourceIdMatches(Res.SETTINGS_LIST_CONTAINER_RES)
                );
        itemList.setAsVerticalList();

        itemList.getChildByText( new UiSelector().className("android.widget.TextView"),
                "Screen lock").clickAndWaitForNewWindow();
        itemList.getChildByText( new UiSelector().className("android.widget.TextView"),
                "Password").clickAndWaitForNewWindow();

        UiObject passwordField = device.findObject(
                new UiSelector().className("android.widget.EditText"));

        //Assert "Minimum Length".
        passwordField.setText("ab!1b");
        Assert.assertTrue(
                device.findObject(
                        new UiSelector().textContains("Must be at least 6 characters")).exists());
        pressDeleteKey(device, 5);

        //Assertion for a valid password that meets all the "PASSWORD QUALITY" criteria.
        passwordField.setText("abc1!d");
        UiObject ContinueButton = device.findObject(
                new UiSelector().className("android.widget.Button").textContains("Continue"));
        ContinueButton.waitForExists(TimeUnit.SECONDS.toMillis(3L));
        Assert.assertTrue(ContinueButton.isEnabled());

    }

    /**
     * Common code to delete all the characters in the password field.
     */
    private void pressDeleteKey(UiDevice device, int n){
        while(n > 0){
            device.pressDelete();
            n--;
        }
    }

    @After
    public void restoreState() throws Exception{
        Instrumentation instrumentation = testFramework.getInstrumentation();
        UiDevice device = testFramework.getDevice();

        //Deactivate "Device Admin" to restore the state.
        SettingsUtil.deactivate(instrumentation, "Sample Device Admin");
    }

}
