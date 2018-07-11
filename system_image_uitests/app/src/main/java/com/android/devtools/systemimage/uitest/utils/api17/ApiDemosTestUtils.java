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

package com.android.devtools.systemimage.uitest.utils.api17;

import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiScrollable;
import android.support.test.uiautomator.UiSelector;

import com.android.devtools.systemimage.uitest.common.Res;
import com.android.devtools.systemimage.uitest.watchers.ApiDemosWatcher;

import junit.framework.Assert;

import java.util.concurrent.TimeUnit;


/**
 * Utility functions for ApiDemosTest.
 */
public class ApiDemosTestUtils {
    /**
     *  Set the criteria for password.
     */
    public static void setPasswordCriteria(String criteria, String value, UiDevice device) throws Exception {
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
    public static void verifyPasswordQuality(final UiDevice device,
                                      String continueButtonLabel) throws Exception {
        UiScrollable itemList =
                new UiScrollable(
                        new UiSelector().resourceIdMatches(Res.SETTINGS_LIST_CONTAINER_RES)
                );

        itemList.setAsVerticalList();

        itemList.getChildByText(new UiSelector().className("android.widget.TextView"),
                "Screen lock").clickAndWaitForNewWindow();
        itemList.getChildByText(new UiSelector().className("android.widget.TextView"),
                "Password").clickAndWaitForNewWindow();

        new ApiDemosWatcher(device).checkForCondition();
        UiObject passwordField = device.findObject(
                new UiSelector().className("android.widget.EditText"));
        passwordField.waitForExists(TimeUnit.SECONDS.toMillis(3L));

        //Assert "Minimum Length".
        validateWrongPassword("aB!1b", "Must be at least 6 characters", device);

        //Assert "Minimum Upper Case".
        validateWrongPassword("abc1!d", "Must contain at least 1 uppercase letter", device);

        //Assert "Minimum Lower Case".
        validateWrongPassword("ABC1!D", "Must contain at least 1 lowercase letter", device);

        //Assert "Minimum Numerical Digits".
        validateWrongPassword("AaBC!D", "Must contain at least 1 numerical digit", device);

        //Assert "Minimum Special Symbols".
        validateWrongPassword("AaBC1D", "Must contain at least 1 special symbol", device);

        //Assertion for a valid password that meets all the "PASSWORD QUALITY" criteria.
        passwordField.setText("Abc1!d");

        UiObject continueButton = device.findObject(
                new UiSelector().className("android.widget.Button").textContains(continueButtonLabel));
        continueButton.waitForExists(TimeUnit.SECONDS.toMillis(3L));
        Assert.assertTrue(continueButton.isEnabled());
    }

    /**
     * Assert the wrong password value with the correct error message.
     */
    private static void validateWrongPassword(String password, String errorMessage, UiDevice device) throws Exception {
        UiObject passwordField = device.findObject(
                new UiSelector().className("android.widget.EditText"));

        passwordField.setText(password);
        UiObject passwordError = device.findObject(new UiSelector().textContains(errorMessage));
        passwordError.waitForExists(3L);
        Assert.assertTrue(passwordError.exists());
        pressDeleteKey(password.length(), device);
    }

    /**
     * Common code to delete all the characters in the password field.
     */
    private static void pressDeleteKey(int n, UiDevice device){
        while(n > 0){
            device.pressDelete();
            n--;
        }
    }
}