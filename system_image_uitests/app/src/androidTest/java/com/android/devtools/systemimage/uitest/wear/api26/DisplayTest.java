/*
 * Copyright (c) 2018 The Android Open Source Project
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

package com.android.devtools.systemimage.uitest.wear.api26;

import android.app.Instrumentation;
import android.support.test.runner.AndroidJUnit4;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiObjectNotFoundException;
import android.support.test.uiautomator.UiScrollable;
import android.support.test.uiautomator.UiSelector;

import com.android.devtools.systemimage.uitest.annotations.TestInfo;
import com.android.devtools.systemimage.uitest.common.Res;
import com.android.devtools.systemimage.uitest.framework.SystemImageTestFramework;

import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.Timeout;
import org.junit.runner.RunWith;

import static org.junit.Assert.assertTrue;

/**
 * Test class for Display page on Android Wear API images.
 */
@RunWith(AndroidJUnit4.class)
public class DisplayTest {
    @Rule
    public final SystemImageTestFramework testFramework = new SystemImageTestFramework();

    private Instrumentation instrumentation = testFramework.getInstrumentation();
    private UiDevice device = UiDevice.getInstance(instrumentation);

    private int MAX_BRIGHTNESS = 5;

    @Rule
    public Timeout globalTimeout = Timeout.seconds(120);

    /**
     * Verifies that watch face type (analog/digital) can be changed.
     * <p>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p>
     * TT ID: f83bf063-2a8c-4d1b-808b-20fd76933135
     * <p>
     *   <pre>
     *   1. Start the Android Wear emulator.
     *   2. Open Settings > Display > Change watch face.
     *   3. Record the original watch face type.
     *   4. Add new analog watch face if its not found.
     *   5. Change the watch face type (either from analog to digital, or digital to analog).
     *   6. Change the watch face back to its original type.
     *   Verify:
     *   1. The original watch face type was changed to a new type.
     *   2. The watch face type was restored to the original setting.
     *   </pre>
     */
    @Test
    @TestInfo(id = "f83bf063-2a8c-4d1b-808b-20fd76933135")
    public void changeWatchFace() throws Exception {
        boolean isOriginalAnalog = getWatchFaceType();
        setWatchFaceType(false);

        assertTrue("Original watch face was not changed",
                getWatchFaceType() != isOriginalAnalog);

        setWatchFaceType(true);

        assertTrue("Original watch face was not restored",
                getWatchFaceType() == isOriginalAnalog);

        device.pressBack();
        device.pressHome();
    }

    /**
     * Verifies that the brightness of the watch can be changed.
     * <p>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p>
     * TT ID: f83bf063-2a8c-4d1b-808b-20fd76933135
     * <p>
     *   <pre>
     *   1. Start the Android Wear emulator.
     *   2. Open Settings > Display > Adjust brightness.
     *   3. Record the original brightness setting.
     *   4. Change the original brightness value.
     *   5. Change the new brightness value.
     *   6. Reset the original brightness value.
     *   Verify:
     *   1. The original brightness was changed.
     *   2. The new brightness was changed.
     *   3. The original brightness was restored.
     *   </pre>
     */
    @Test
    @TestInfo(id = "f83bf063-2a8c-4d1b-808b-20fd76933135")
    public void changeBrightness() throws Exception {
        openDisplaySetting();

        String originalBrightness = getBrightness();
        if (originalBrightness.equals("Automatic")) {
            setBrightness("1");
        } else {
            int level = Integer.parseInt(originalBrightness);
            if (level == MAX_BRIGHTNESS) {
                setBrightness("1");
            } else {
                setBrightness(Integer.toString(level+1));
            }
        }
        String newBrightness = getBrightness();
        assertTrue("Original brightness has not been changed",
                !newBrightness.equals(originalBrightness));

        int level = Integer.parseInt(newBrightness);
        if (level == MAX_BRIGHTNESS) {
            setBrightness("1");
        } else {
            setBrightness(Integer.toString(level+1));
        }
        assertTrue("New brightness has not been changed",
                !newBrightness.equals(getBrightness()));

        setBrightness(originalBrightness);
        assertTrue("Original brightness has not been restored",
                originalBrightness.equals(getBrightness()));
        device.pressHome();
    }

    /**
     * Verifies that the font size of the watch can be changed.
     * <p>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p>
     * TT ID: f83bf063-2a8c-4d1b-808b-20fd76933135
     * <p>
     *   <pre>
     *   1. Start the Android Wear emulator.
     *   2. Open Settings > Display.
     *   3. Record the original font size setting.
     *   4. Open Font Size
     *   4. Set the Font Size to Small.
     *   5. Set the Font Size to Normal.
     *   6. Set the Font Size to Large.
     *   7. Reset the Font Size to the original value.
     *   Verify:
     *   1. The font size was set to Small.
     *   2. The font size was set to Normal.
     *   3. The font size was set to Large.
     *   3. The original font size was restored.
     *   </pre>
     */
    @Test
    @TestInfo(id = "f83bf063-2a8c-4d1b-808b-20fd76933135")
    public void changeFontSize() throws Exception {
        openDisplaySetting();

        String originalFontSize = getFontSize();
        String originalFont = originalFontSize.substring(0,1).toUpperCase() +
                originalFontSize.substring(1).toLowerCase();

        setFontSize("Small");
        assertTrue("Font size is not set to Small", "SMALL".equals(getFontSize()));

        setFontSize("Normal");
        assertTrue("Font size is not set to Normal", "NORMAL".equals(getFontSize()));

        setFontSize("Large");
        assertTrue("Font size is not set to Large", "LARGE".equals(getFontSize()));

        setFontSize(originalFont);
        assertTrue("Font size is not reset to " + originalFontSize,
                originalFontSize.equals(getFontSize()));

        device.pressBack();
    }

    /**
     * Verifies that the Always-on screen setting can be changed.
     * <p>
     * This is run to qualify releases. Please involve the test team in substantial changes.
     * <p>
     * TT ID: f83bf063-2a8c-4d1b-808b-20fd76933135
     * <p>
     *   <pre>
     *   1. Start the Android Wear emulator.
     *   2. Open Settings > Display.
     *   3. Record the original always-on screen value.
     *   4. Toggle the Always-on screen value.
     *   5. Reset the Always-on screen setting to the original value.
     *   Verify:
     *   1. The Always-on screen value was changed.
     *   3. The original Always-on screen value was restored.
     *   </pre>
     */
    @Test
    @TestInfo(id = "f83bf063-2a8c-4d1b-808b-20fd76933135")
    public void changeAlwaysOnScreen() throws Exception {
        openDisplaySetting();

        boolean originalValue = getAlwaysOnValue();
        setAlwaysOnValue(!originalValue);

        assertTrue("Always-on value was not changed",
                originalValue != getAlwaysOnValue());

        setAlwaysOnValue(originalValue);

        assertTrue("Always-on value was not restored",
                originalValue == getAlwaysOnValue());

        device.pressBack();
        device.pressHome();
    }

    //Open the Display settings
    private void openDisplaySetting() throws UiObjectNotFoundException {
        device.pressHome();

        UiScrollable wheelList = new UiScrollable(new UiSelector().resourceId(Res.WEAR_LAUNCHER));
        if (wheelList.waitForExists(3L)) {
            wheelList.setAsVerticalList();
        } else {
            device.pressBack();
            if (wheelList.waitForExists(3L)) {
                wheelList.setAsVerticalList();
            }
        }

        UiSelector settingsOption = new UiSelector().text("Settings");
        if (wheelList.scrollIntoView(settingsOption)) {
            device.findObject(settingsOption).clickAndWaitForNewWindow();
        }

        UiScrollable itemList = new UiScrollable(new UiSelector().resourceId(Res.ANDROID_LIST_RES).
                packageName(Res.WEAR_SETTINGS));
        itemList.setAsVerticalList();

        UiSelector displayOption = new UiSelector().text("Display");
        if (itemList.scrollIntoView(displayOption)) {
            device.findObject(displayOption).clickAndWaitForNewWindow();
        }
    }

    //Get the  watch face type
    private boolean getWatchFaceType() throws UiObjectNotFoundException {
        openChangeWatchFace();

        UiObject analogSettingsButton = device.findObject(new UiSelector()
                .descriptionContains("Settings for Elements Analog").resourceId(
                        Res.WEAR_FACE_SETTINGS));

        return analogSettingsButton.waitForExists(3L);
    }

    //Set the watch face type, testing for the presence of analog watch face on initialization,
    //and adding it if not found.
    private void setWatchFaceType(boolean isInitialized) throws UiObjectNotFoundException {
        boolean isAnalogSet = getWatchFaceType();

        String faceToActivate = isAnalogSet ?
                "Elements Digital" : "Elements Analog";
        UiObject newWatchFace = device.findObject(new UiSelector().
                resourceId(Res.WEAR_PREVIEW_IMAGE).descriptionContains(faceToActivate));

        if (isInitialized) {
            if (newWatchFace.waitForExists(3L)) {
                newWatchFace.clickAndWaitForNewWindow();
            }
        } else {
            device.pressBack();
            openChangeWatchFace();
            if (newWatchFace.waitForExists(3L)) {
                device.pressBack();
                device.pressHome();
                setWatchFaceType(true);
            } else {
                UiObject showAllButton = device.findObject(new UiSelector().
                        resourceId(Res.WEAR_SHOW_ALL_BUTTON));
                if (showAllButton.waitForExists(2L)) {
                    showAllButton.clickAndWaitForNewWindow();
                }
                String newLabel = isAnalogSet ?
                        "Elements Digital" : "Elements Analog";
                UiObject newWatchPicker = device.findObject(new UiSelector().
                        resourceId(Res.WEAR_WATCH_FACE_PICKER).text(newLabel));
                if (newWatchPicker.waitForExists(3L)) {
                    newWatchPicker.clickAndWaitForNewWindow();
                }

                device.pressBack();
                device.pressHome();
                setWatchFaceType(true);
            }
        }
    }

    private void openChangeWatchFace() throws UiObjectNotFoundException {
        openDisplaySetting();

        UiScrollable settingsList = new UiScrollable(new UiSelector().resourceId(Res.ANDROID_LIST_RES).
                packageName(Res.WEAR_SETTINGS));
        settingsList.setAsVerticalList();

        UiSelector changeWatchFaceButton = new UiSelector().text("Change watch face");

        if (settingsList.scrollIntoView(changeWatchFaceButton)) {
            device.findObject(changeWatchFaceButton).clickAndWaitForNewWindow();
        }
    }

    //Get the brightness level
    private String getBrightness() throws UiObjectNotFoundException {
        UiScrollable settingsList = new UiScrollable(new UiSelector().resourceId(Res.ANDROID_LIST_RES).
                packageName(Res.WEAR_SETTINGS));
        settingsList.setAsVerticalList();

        UiSelector adjustBrightnessOption = new UiSelector().text("Adjust brightness");

        if (settingsList.scrollIntoView(adjustBrightnessOption)) {
            device.findObject(adjustBrightnessOption).clickAndWaitForNewWindow();
        }

        for (int i = 1; i <= MAX_BRIGHTNESS; i++) {
            UiScrollable brightnessList = new UiScrollable(new UiSelector().resourceId(Res.ANDROID_SELECT_LIST).
                    packageName(Res.WEAR_SETTINGS));
            brightnessList.setAsVerticalList();

            UiSelector brightnessOption = new UiSelector()
                    .className("android.widget.CheckedTextView").text(Integer.toString(i));

            if (brightnessList.scrollIntoView(brightnessOption)) {
                UiObject brightness = device.findObject(brightnessOption);
                if (brightness.waitForExists(3L) && brightness.isChecked()) {
                    return brightness.getText();
                }
            }
        }
        return "Automatic";
    }

    //Set the brightness to the level provided
    private void setBrightness(String level)
            throws UiObjectNotFoundException {

        UiScrollable itemList = new UiScrollable(new UiSelector().resourceId(Res.ANDROID_SELECT_LIST).
                packageName(Res.WEAR_SETTINGS));
        itemList.setAsVerticalList();

        UiSelector brightnessOption = new UiSelector()
                .className("android.widget.CheckedTextView").text(level);

        if (itemList.scrollIntoView(brightnessOption)) {
            UiObject brightness = device.findObject(brightnessOption);
            if (brightness.waitForExists(3L)) {
                brightness.clickAndWaitForNewWindow();
            }
        }
    }

    //Get the font size level
    private String getFontSize() throws UiObjectNotFoundException {
        String fontSizeValue = "";

        UiScrollable settingsList = new UiScrollable(new UiSelector().resourceId(Res.ANDROID_LIST_RES).
                packageName(Res.WEAR_SETTINGS));
        settingsList.setAsVerticalList();

        UiSelector fontSizeLabel = new UiSelector().resourceId(Res.ANDROID_SUMMARY_RES).
                packageName(Res.WEAR_SETTINGS);

        if (settingsList.scrollIntoView(fontSizeLabel)) {
            UiObject fontSizeOption = device.findObject(fontSizeLabel);
            if (fontSizeOption.waitForExists(3L)) {
                fontSizeValue = fontSizeOption.getText();
            }
        }
        return fontSizeValue;
    }

    //Set the font size level as indicated
    private void setFontSize(String fontSize) throws UiObjectNotFoundException {
        UiScrollable settingsList = new UiScrollable(new UiSelector().resourceId(Res.ANDROID_LIST_RES).
                packageName(Res.WEAR_SETTINGS));
        settingsList.setAsVerticalList();

        UiSelector setFontSize = new UiSelector().text("Font size");

        if (settingsList.scrollIntoView(setFontSize)) {
            device.findObject(setFontSize).clickAndWaitForNewWindow();
        }

        UiObject fontSizeOption = device.findObject(new UiSelector().text(fontSize));

        if (fontSizeOption.waitForExists(3L)) {
            fontSizeOption.clickAndWaitForNewWindow();
        }
    }


    //Get the always-on screen value
    private boolean getAlwaysOnValue() throws UiObjectNotFoundException {
        String fontSizeValue = "";

        UiScrollable settingsList = new UiScrollable(new UiSelector().resourceId(Res.ANDROID_LIST_RES).
                packageName(Res.WEAR_SETTINGS));
        settingsList.setAsVerticalList();

        UiSelector alwaysOnLabel = new UiSelector().text("Always-on screen").
                packageName(Res.WEAR_SETTINGS);
        UiSelector alwaysOnSwitch = new UiSelector().resourceId(Res.ANDROID_SWITCH_WIDGET).
                packageName(Res.WEAR_SETTINGS);

        if (settingsList.scrollIntoView(alwaysOnLabel)) {
            UiObject fontSizeOption = device.findObject(alwaysOnSwitch);
            if (fontSizeOption.waitForExists(3L) &&
                    "on".equals(fontSizeOption.getText().toLowerCase())) {
                return true;
            }
        }
        return false;
    }

    //Set the always-on screen value as indicated
    private void setAlwaysOnValue(boolean alwaysOn) throws UiObjectNotFoundException {
        String fontSizeValue = "";

        UiScrollable settingsList = new UiScrollable(new UiSelector().resourceId(Res.ANDROID_LIST_RES).
                packageName(Res.WEAR_SETTINGS));
        settingsList.setAsVerticalList();

        UiSelector alwaysOnLabel = new UiSelector().text("Always-on screen").
                packageName(Res.WEAR_SETTINGS);
        UiSelector alwaysOnSwitch = new UiSelector().resourceId(Res.ANDROID_SWITCH_WIDGET).
                packageName(Res.WEAR_SETTINGS);

        if (settingsList.scrollIntoView(alwaysOnLabel)) {
            UiObject fontSizeOption = device.findObject(alwaysOnSwitch);
            if (fontSizeOption.waitForExists(3L)) {
                if ((alwaysOn && "off".equals(fontSizeOption.getText().toLowerCase())) ||
                        (!alwaysOn && "on".equals(fontSizeOption.getText().toLowerCase()))) {
                    fontSizeOption.clickAndWaitForNewWindow();
                    UiObject yesButton = device.findObject(new UiSelector().description("Yes").
                            packageName(Res.WEAR_SETTINGS));

                    if (yesButton.waitForExists(3L)) {
                        yesButton.clickAndWaitForNewWindow();
                    }
                }
            }
        }
    }
}