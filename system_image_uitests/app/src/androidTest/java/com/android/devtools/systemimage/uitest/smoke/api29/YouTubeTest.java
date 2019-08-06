package com.android.devtools.systemimage.uitest.smoke.api29;

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
import com.android.devtools.systemimage.uitest.utils.Wait;
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
        GoogleAppUtil.deleteAccount(instrumentation);

        boolean logInSuccess = GoogleAppUtil.loginGoogleApp(instrumentation, true);
        assertTrue("YouTube log in was unsuccessful", logInSuccess);

        final UiDevice device = UiDevice.getInstance(instrumentation);
        AppLauncher.launch(instrumentation, "YouTube");

        UiObject updateLaterButton = device.findObject(
                new UiSelector().resourceId(Res.YOUTUBE_UPDATE_LATER_BUTTON_RES));
        if (updateLaterButton.waitForExists(5L)) {
            updateLaterButton.clickAndWaitForNewWindow();
        }

        YouTubeUtil.openYouTubeSettings(instrumentation, "Account");
        UiObject signInLabel = device.findObject(new UiSelector().text("SIGN IN"));
        assertFalse("YouTube log in was unsuccessful", signInLabel.waitForExists(5L));

        GoogleAppUtil.deleteAccount(instrumentation);

        AppLauncher.launch(instrumentation, "YouTube");
        YouTubeUtil.openYouTubeSettings(instrumentation, "Account");
        signInLabel = device.findObject(new UiSelector().text("SIGN IN"));
        assertTrue("YouTube log out was unsuccessful", signInLabel.waitForExists(5L));
    }
}
