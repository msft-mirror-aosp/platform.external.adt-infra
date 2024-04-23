package com.android.devtools.systemimage.uitest.utils;

import android.app.Instrumentation;
import androidx.test.uiautomator.UiDevice;
import androidx.test.uiautomator.UiObject;
import androidx.test.uiautomator.UiScrollable;
import androidx.test.uiautomator.UiSelector;

import com.android.devtools.systemimage.uitest.common.Res;

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


    /* Decline YouTubeTV sign up prompt */
    public static void declineYouTubeTV(UiDevice device) throws Exception {
        UiObject closeButton = device.findObject(
                new UiSelector()
                        .className("android.view.ViewGroup")
                        .packageName("com.google.android.youtube")
                        .description("Close"));

        boolean hasCloseButton = closeButton.waitForExists(5L);
        if (hasCloseButton) {
            closeButton.clickAndWaitForNewWindow();
        }
    }

    /* Decline YouTube TV cast prompt */
    public static void declineYouTubeCast(UiDevice device) throws Exception {
        UiObject cancelTVCastButton = device.findObject(
                new UiSelector()
                        .className("android.widget.Button")
                        .resourceId("com.google.android.youtube:id/secondary_action_button")
                        .text("Cancel"));

        boolean hasCancelButton = cancelTVCastButton.waitForExists(5L);
        if (hasCancelButton) {
            cancelTVCastButton.clickAndWaitForNewWindow();
        }
    }

    /* Decline Update YouTube prompt */
    public static void declineYouTubeUpdate(UiDevice device) throws Exception {
        UiObject noThanksButton = device.findObject(
                new UiSelector()
                        .className("android.widget.Button")
                        .packageName("com.android.vending")
                        .text("NO THANKS"));

        boolean hasNoThanksButton = noThanksButton.waitForExists(5L);
        if (hasNoThanksButton) {
            noThanksButton.clickAndWaitForNewWindow();
        }
    }

    /* Click YouTube Mobile Avatar */
    public static void clickMobileAvatar(UiDevice device, long timeout) throws Exception {
        UiObject mobileAvatar = device.findObject(
                new UiSelector().resourceId(Res.YOUTUBE_TOPBAR_AVATAR_RES)
                        .packageName(Res.YOUTUBE_PACKAGE));

        if (mobileAvatar.waitForExists(timeout)) {
            mobileAvatar.clickAndWaitForNewWindow();
        }

    }

    /* Launch You Tube App */
    public static void launchYouTube(Instrumentation instrumentation) throws Exception {
        final UiDevice device = UiDevice.getInstance(instrumentation);

        AppLauncher.launch(instrumentation, "YouTube");

        clickMobileAvatar(device, 30000L);

        declineYouTubeCast(device);
        declineYouTubeTV(device);
        declineYouTubeUpdate(device);

        clickMobileAvatar(device, 15000L);
    };

    /* Verify You Tube User Status */
    public static boolean isTestUserLoggedIn(Instrumentation instrumentation) throws Exception {
        UiDevice device = UiDevice.getInstance(instrumentation);

        launchYouTube(instrumentation);

        UiObject testUserLoggedIn = device.findObject(
                new UiSelector().resourceId(Res.YOUTUBE_EMAIL_ACCOUNT_RES)
                        .text(GoogleAppUtil.getUserEmail()));

        return testUserLoggedIn.waitForExists(10000L);
    }

    /* Log Out You Tube User */
    public static void logoutYouTubeAccount(Instrumentation instrumentation) throws Exception {
        UiDevice device = UiDevice.getInstance(instrumentation);
        clickMobileAvatar(device, 5000L);

        UiObject manageAccountButton = device.findObject(
                new UiSelector()
                        .resourceId(Res.MANAGE_ACCOUNT_BUTTON_RES)
                        .text("Manage your Google Account"));

        if (manageAccountButton.waitForExists(5000L)) {
            manageAccountButton.clickAndWaitForNewWindow();
        }

        UiObject getStartedButton = device.findObject(
                new UiSelector()
                        .resourceId(Res.GOOGLE_SERVICES_SKIP_BUTTON_RES)
                        .text("Get started"));

        if (getStartedButton.waitForExists(50000L)) {
            getStartedButton.clickAndWaitForNewWindow();
        }

        UiObject currentAccountButton = device.findObject(
                new UiSelector()
                        .resourceId(Res.GOOGLE_SERVICES_ACCOUNT_BUTTON_RES)
                        .descriptionContains("Current account: " + GoogleAppUtil.getUserEmail()));

        if (currentAccountButton.waitForExists(5000L)) {
            currentAccountButton.clickAndWaitForNewWindow();
        }

        UiObject manageDeviceAccountsButton = device.findObject(
                new UiSelector()
                        .resourceId(Res.GOOGLE_SERVICES_ACCOUNTS_CHIP_RES)
                        .text("Manage accounts on this device"));

        if (manageDeviceAccountsButton.waitForExists(5000L)) {
            manageDeviceAccountsButton.clickAndWaitForNewWindow();
        }

        UiObject userAccountButton = device.findObject(
                new UiSelector()
                        .resourceId("android:id/title")
                        .text(GoogleAppUtil.getUserEmail()));

        if (userAccountButton.waitForExists(5000L)) {
            userAccountButton.clickAndWaitForNewWindow();
        }

        UiObject removeAccountButton = device.findObject(
                new UiSelector()
                        .resourceId(Res.ANDROID_BUTTON)
                        .text("Remove account"));

        if (removeAccountButton.waitForExists(5000L)) {
            removeAccountButton.clickAndWaitForNewWindow();
        }

        UiObject confirmRemoveAccountButton = device.findObject(
                new UiSelector()
                        .resourceId(Res.ANDROID_BUTTON_ONE)
                        .text("Remove account"));

        if (confirmRemoveAccountButton.waitForExists(5000L)) {
            confirmRemoveAccountButton.clickAndWaitForNewWindow();
        }

        for (int i = 0; i <=1; i++) {
            UiObject navigateUpButton = device.findObject(
                    new UiSelector()
                            .className("android.widget.ImageButton")
                            .description("Navigate up"));

            if (navigateUpButton.waitForExists(5000L)) {
                navigateUpButton.clickAndWaitForNewWindow();
            }
        }

        UiObject doneButton = device.findObject(
                new UiSelector()
                        .className("android.widget.ImageButton")
                        .description("Done"));

        if (doneButton.waitForExists(5000L)) {
            doneButton.clickAndWaitForNewWindow();
        }
    }
}
