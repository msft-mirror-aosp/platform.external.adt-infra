package com.android.devtools.systemimage.uitest.utils;

import android.app.Instrumentation;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiScrollable;
import android.support.test.uiautomator.UiSelector;
import android.widget.ScrollView;

import com.android.devtools.systemimage.uitest.common.Res;

import java.util.concurrent.TimeUnit;
import static org.junit.Assert.assertTrue;

public class YouTubeUtil {

    private YouTubeUtil() {
        throw new AssertionError();
    }

    public static void openYouTubeSettings(Instrumentation instrumentation) throws Exception {
        UiDevice device = UiDevice.getInstance(instrumentation);

        UiObject mobileAvatar = device.findObject(
                new UiSelector().resourceId(Res.YOUTUBE_TOPBAR_AVATAR_RES)
                        .packageName(Res.YOUTUBE_PACKAGE));
        if (mobileAvatar.waitForExists(5L)) {
            mobileAvatar.clickAndWaitForNewWindow();
        }

        UiScrollable scrollView = new UiScrollable(new UiSelector().
                resourceId(Res.YOUTUBE_LIST_RES).
                packageName(Res.YOUTUBE_PACKAGE));
        scrollView.setAsVerticalList();

        UiObject settingsTitle = device.findObject(
                new UiSelector().resourceId(Res.YOUTUBE_TITLE_RES)
                        .packageName(Res.YOUTUBE_PACKAGE).text("Switch account"));
        scrollView.scrollIntoView(settingsTitle);

        assertTrue("Settings not found", settingsTitle.waitForExists(5L));
        settingsTitle.clickAndWaitForNewWindow();
    }
}