package com.android.devtools.systemimage.uitest.smoke.api25;

import android.app.Instrumentation;
import android.support.test.runner.AndroidJUnit4;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiSelector;

import com.android.devtools.systemimage.uitest.annotations.TestInfo;
import com.android.devtools.systemimage.uitest.common.Res;
import com.android.devtools.systemimage.uitest.framework.SystemImageTestFramework;
import com.android.devtools.systemimage.uitest.utils.AppLauncher;
import com.android.devtools.systemimage.uitest.utils.GoogleAppUtil;
import com.android.devtools.systemimage.uitest.utils.YouTubeUtil;

import org.junit.FixMethodOrder;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.Timeout;
import org.junit.runner.RunWith;
import org.junit.runners.MethodSorters;

import static junit.framework.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

/**
 * Test to verify that YouTube is installed and working correctly on Google API images
 */

@RunWith(AndroidJUnit4.class)
/*
 *Added this annotation so that YouTube version is checked first before login happens.
 *This is done  because if login happens first, it will update the app and version check
 *test will always pass.
 */
@FixMethodOrder(MethodSorters.NAME_ASCENDING)
public class YouTubeTest {

    @Rule
    public final SystemImageTestFramework testFramework = new SystemImageTestFramework();

    @Rule
    public Timeout globalTimeout = Timeout.seconds(360);

    /**
     * Verify YouTube has the latest version or not.
     * <p>
     * TT ID: XXXX
     * <p>
     *   <pre>
     *   Test Steps:
     *   1. Start an emulator and launch home screen.
     *   2. Open Apps.
     *   3. Launch YouTube app.
     *   Verify:
     *      1. Verify that there is no YouTube update screen.
     *   </pre>
     */
    @Test
    @TestInfo(id = "XXXX")
    public void checkYouTubeVersion() throws Exception{
        Instrumentation instrumentation = testFramework.getInstrumentation();
        UiDevice device = UiDevice.getInstance(instrumentation);
        AppLauncher.launch(instrumentation, "YouTube");
        UiObject updateLaterButton = device.findObject(new UiSelector().resourceId(Res.YOUTUBE_UPDATE_LATER_BUTTON_RES));
        assertFalse("Device has older version of YouTube installed", updateLaterButton.waitForExists(5L));
    }

    /**
     * Verify YouTube login and logout are working correctly.
     * <p>
     * TT ID: XXXX
     * <p>
     *   <pre>
     *   Test Steps:
     *   1. Start an emulator and launch home screen.
     *   2. Open Apps.
     *   3. Launch Chrome app. and signIn to Chrome .
     *   4. Launch YouTube app. and signOut
     *   Verify:
     *      1. Verify that there is user can sign in via Chrome.
     *      2. Verify that user has signed out of the YouTube app.
     *   </pre>
     */
    @Test
    @TestInfo(id = "XXXX")
    public void loginYouTube() throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();
        GoogleAppUtil.logoutGoogleChrome(instrumentation);
        boolean logInSuccess = GoogleAppUtil.loginGoogleApp(instrumentation, true);
        assertTrue("YouTube log in was unsuccessful", logInSuccess);

        final UiDevice device = UiDevice.getInstance(instrumentation);
        AppLauncher.launch(instrumentation, "YouTube");

        UiObject youTubeInstall = device.findObject(
                new UiSelector().resourceId(Res.YOUTUBE_INSTALL_BUTTON_RES));
        if (youTubeInstall.waitForExists(5L)) {
            youTubeInstall.clickAndWaitForNewWindow();

            UiObject youTubeLeftButton = device.findObject(new UiSelector().
                    resourceId(Res.GOOGLE_PLAY_LEFT_BUTTON_RES).textMatches("(?i)update(?-i)"));
            if (youTubeLeftButton.waitForExists(1000L)) {
                youTubeLeftButton.clickAndWaitForNewWindow();
            }

            UiObject youTubeRightButton = device.findObject(new UiSelector().
                    resourceId(Res.GOOGLE_PLAY_RIGHT_BUTTON_RES).textMatches("(?i)open(?-i)"));
            if (youTubeRightButton.waitForExists(30000L)) {
                youTubeRightButton.clickAndWaitForNewWindow();
            }
        }

        UiObject youTubeClose = device.findObject(
                new UiSelector().packageName(Res.YOUTUBE_PACKAGE).description("Close"));
        if (youTubeClose.waitForExists(5L)) {
            youTubeClose.clickAndWaitForNewWindow();
        }

        UiObject updateLaterButton = device.findObject(
                new UiSelector().resourceId(Res.YOUTUBE_UPDATE_LATER_BUTTON_RES));
        if (updateLaterButton.waitForExists(5L)) {
            updateLaterButton.clickAndWaitForNewWindow();
        }

        UiObject mobileAvatar = device.findObject(
                new UiSelector().resourceId(Res.YOUTUBE_TOPBAR_AVATAR_RES)
                        .packageName(Res.YOUTUBE_PACKAGE));
        if (mobileAvatar.waitForExists(5L)) {
            mobileAvatar.clickAndWaitForNewWindow();
        }

        UiObject signInButton = device.findObject(
                new UiSelector().resourceId(Res.YOUTUBE_BUTTON_RES)
                        .packageName(Res.YOUTUBE_PACKAGE).text("SIGN IN"));
        if (signInButton.waitForExists(5L)) {
            signInButton.clickAndWaitForNewWindow();
        }

        UiObject youTubeSignIn = device.findObject(
                new UiSelector().resourceId(Res.YOUTUBE_SIGN_IN_FOOTER_RES)
                        .packageName(Res.YOUTUBE_PACKAGE)
                        .text("Sign in"));

        if (youTubeSignIn.waitForExists(5L)) {
            youTubeSignIn.clickAndWaitForNewWindow();
        }

        UiObject playAccount = device.findObject(
                new UiSelector().packageName(Res.YOUTUBE_PACKAGE)
                        .text("David Play"));

        if (playAccount.waitForExists(5L)) {
            playAccount.clickAndWaitForNewWindow();
        }

        if (mobileAvatar.waitForExists(5L)) {
            mobileAvatar.clickAndWaitForNewWindow();
        }

        UiObject youTubeSignOut = device.findObject(
                new UiSelector().resourceId(Res.YOUTUBE_SIGN_OUT_FOOTER_RES)
                        .packageName(Res.YOUTUBE_PACKAGE)
                        .text("Sign out"));
        if (youTubeSignOut.waitForExists(5L)) {
            youTubeSignOut.clickAndWaitForNewWindow();
        }

        UiObject noThanksButton = device.findObject(
                new UiSelector().resourceId(Res.YOUTUBE_DISMISS_RES)
                        .packageName(Res.YOUTUBE_PACKAGE).text("NO THANKS"));
        if (noThanksButton.waitForExists(5L)) {
            noThanksButton.clickAndWaitForNewWindow();
        }

        if (mobileAvatar.waitForExists(5L)) {
            mobileAvatar.clickAndWaitForNewWindow();
        }

        UiObject signInMessage = device.findObject(
                new UiSelector().resourceId(Res.YOUTUBE_SIGN_IN_BODY_TEXT_RES)
                        .packageName(Res.YOUTUBE_PACKAGE));

        assertTrue("YouTube log out was unsuccessful",
                signInMessage.waitForExists(10L));
    }
}