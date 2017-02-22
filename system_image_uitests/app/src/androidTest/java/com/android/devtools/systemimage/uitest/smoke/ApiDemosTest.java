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

import java.util.StringTokenizer;
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

        // Set the criteria for password to 'Complex' type.
        itemList.getChildByText(
                new UiSelector().className("android.widget.RelativeLayout"), "Password quality")
                .clickAndWaitForNewWindow();
        device.findObject(new UiSelector().text("Complex")).clickAndWaitForNewWindow();

        // Set minimum length to 6.
        setPasswordCriteria(device, "Minimum length", "6");

        // Set minimum letters to 1.
        setPasswordCriteria(device, "Minimum letters", "1");

        // Set minimum numerics to 1.
        setPasswordCriteria(device, "Minimum numeric", "1");

        // Set minimum lower case letters to 1.
        setPasswordCriteria(device, "Minimum lower case", "1");

        // Set minimum upper case letters  to 1.
        setPasswordCriteria(device, "Minimum upper case", "1");

        // Set minimum special symbols to 1.
        setPasswordCriteria(device, "Minimum symbols", "1");

        // Set minimum non-letter to 1.
        setPasswordCriteria(device, "Minimum non-letter", "1");

        //Verify that setting the password meets the "PASSWORD QUALITY" criteria.
        verifyPasswordQuality(instrumentation, device);

    }


    /**
     *  Set the criteria for password.
     */
    private void setPasswordCriteria(
            UiDevice device,
            String criteria,
            String value) throws Exception{
        UiScrollable itemList =
                new UiScrollable(new UiSelector().resourceId(Res.ANDROID_LIST_RES));
        itemList.setAsVerticalList();
        itemList.getChildByText(new UiSelector().className("android.widget.TextView"),
                criteria).clickAndWaitForNewWindow();
        UiObject editText = device.findObject(new UiSelector().className("android.widget.EditText"));
        editText.setText(value);
        device.findObject(new UiSelector().text("OK")).clickAndWaitForNewWindow();
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
        passwordField.waitForExists(TimeUnit.SECONDS.toMillis(3L));

        //Assert "Minimum Length".
        validateWrongPassword(device, "aB!1b", "Must be at least 6 characters");

        //Assert "Minimum Upper Case".
        validateWrongPassword(device, "abc1!d", "Must contain at least 1 uppercase letter");

        //Assert "Minimum Lower Case".
        validateWrongPassword(device, "ABC1!D", "Must contain at least 1 lowercase letter");

        //Assert "Minimum Numerical Digits".
        validateWrongPassword(device, "AaBC!D", "Must contain at least 1 numerical digit");

        //Assert "Minimum Special Symbols".
        validateWrongPassword(device, "AaBC1D", "Must contain at least 1 special symbol");

        //Assertion for a valid password that meets all the "PASSWORD QUALITY" criteria.
        passwordField.setText("Abc1!d");
        UiObject ContinueButton = device.findObject(
                new UiSelector().className("android.widget.Button").textContains("Continue"));
        ContinueButton.waitForExists(TimeUnit.SECONDS.toMillis(3L));
        Assert.assertTrue(ContinueButton.isEnabled());
    }


    /**
     * Assert the wrong password value with the correct error message.
     */
    private void validateWrongPassword(UiDevice device,
                                       String password,
                                       String errorMessage) throws Exception {
        UiObject passwordField = device.findObject(
                new UiSelector().className("android.widget.EditText"));

        passwordField.setText(password);
        Assert.assertTrue(
                device.findObject(
                        new UiSelector().textContains(errorMessage)).exists());
        pressDeleteKey(device, password.length());
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