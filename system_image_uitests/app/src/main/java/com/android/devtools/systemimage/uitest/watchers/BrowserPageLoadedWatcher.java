package com.android.devtools.systemimage.uitest.watchers;

import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiSelector;
import android.support.test.uiautomator.UiWatcher;

/**
 * Monitors the visibility of the browser loading bar.
 * <p>
 * When the web page is done loading, the loading bar is invisible.
 */
public class BrowserPageLoadedWatcher implements UiWatcher {
    private final UiDevice mDevice;
    private static final String BROWSER_SEARCH_ICON_RES = "com.android.browser:/id/progress";

    public BrowserPageLoadedWatcher(UiDevice device) {
        this.mDevice = device;
    }

    @Override
    public boolean checkForCondition() {
        UiObject progress = mDevice.findObject(
                new UiSelector().resourceId(BROWSER_SEARCH_ICON_RES));

        // While the loading bar is still visible.
        while (progress.exists()) {
            try {
                Thread.sleep(100);
            } catch (InterruptedException e) {
                e.printStackTrace();
            }
        }

        return true;
    }
}
