package com.android.devtools.systemimage.uitest.smoke.api31;

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
    public Timeout globalTimeout = Timeout.seconds(1200);

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
     *   3. Launch Chrome app. and signIn to Chrome
     *   Verify:
     *      1. Verify that there is user can sign in via Chrome.
     *   </pre>
     */
    @Test
    @TestInfo(id = "XXXX")
    public void loginYouTube() throws Exception {
        Instrumentation instrumentation = testFramework.getInstrumentation();
        GoogleAppUtil.logoutGoogleChrome(instrumentation);
        boolean logInSuccess = GoogleAppUtil.loginGoogleApp(instrumentation, true);
        assertTrue("Google log in was unsuccessful", logInSuccess);

        assertTrue("YouTube log in was unsuccessful",
                isTestUserLoggedIn(instrumentation));

        GoogleAppUtil.logoutGoogleChrome(instrumentation);

        assertFalse("YouTube log out was unsuccessful",
                isTestUserLoggedIn(instrumentation));
    }

    private boolean isTestUserLoggedIn(Instrumentation instrumentation) throws Exception {
        final UiDevice device = UiDevice.getInstance(instrumentation);
        AppLauncher.launch(instrumentation, "YouTube");

        UiObject mobileAvatar = device.findObject(
                new UiSelector().resourceId(Res.YOUTUBE_TOPBAR_AVATAR_RES)
                        .packageName(Res.YOUTUBE_PACKAGE));
        if (mobileAvatar.waitForExists(5L)) {
            mobileAvatar.clickAndWaitForNewWindow();
        }

        if (mobileAvatar.waitForExists(30000L)) {
            mobileAvatar.clickAndWaitForNewWindow();
        }

        UiObject testUserLoggedIn = device.findObject(
                new UiSelector().resourceId(Res.YOUTUBE_EMAIL_ACCOUNT_RES)
                        .text(GoogleAppUtil.getUserEmail()));

        return testUserLoggedIn.waitForExists(1000L);
    }
}