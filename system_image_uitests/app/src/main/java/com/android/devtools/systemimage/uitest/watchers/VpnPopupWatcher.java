package com.android.devtools.systemimage.uitest.watchers;

import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiObjectNotFoundException;
import android.support.test.uiautomator.UiSelector;
import android.support.test.uiautomator.UiWatcher;

import junit.framework.AssertionFailedError;

/**
 * Monitors and dismisses the VPN popup dialog.
 */
public class VpnPopupWatcher implements UiWatcher {
  private UiDevice mDevice;

  public VpnPopupWatcher(UiDevice device) {
    this.mDevice = device;
  }

  @Override
  public boolean checkForCondition() {
    UiObject okButton = mDevice.findObject(new UiSelector().text("OK"));
    if (okButton.exists()) {
      try {
        okButton.click();
        return true;
      } catch (UiObjectNotFoundException e) {
        throw new AssertionFailedError("Failed to dismiss the VPN popup dialog");
      }
    }
    return false;
  }
}
