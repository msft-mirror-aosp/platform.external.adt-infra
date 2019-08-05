package com.android.devtools.systemimage.uitest.utils;

import android.app.Instrumentation;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiSelector;
import java.util.concurrent.TimeUnit;
import static org.junit.Assert.assertTrue;

public class YouTubeUtil {

    private YouTubeUtil() {
        throw new AssertionError();
    }

    public static void openYouTubeSettings(Instrumentation instrumentation, String contentDescription) throws Exception {
        UiDevice device = UiDevice.getInstance(instrumentation);
        UiObject settingsButton = device.findObject(new UiSelector().descriptionContains(contentDescription));
        assertTrue("Settings not found", settingsButton.waitForExists(TimeUnit.MILLISECONDS.convert(3L, TimeUnit.SECONDS)));
        settingsButton.clickAndWaitForNewWindow();
    }
}
