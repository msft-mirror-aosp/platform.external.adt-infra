package com.android.tools.e2etests.animatebox

import android.app.Instrumentation
import android.content.Intent
import android.util.Log
import android.view.KeyEvent
import androidx.test.uiautomator.By
import androidx.test.uiautomator.UiDevice
import androidx.test.uiautomator.Until
import com.android.tools.testlib.emu.Adb
import com.android.tools.testlib.emu.LogcatWatcher
import com.android.tools.testlib.emu.eventually
import org.junit.Assert

val TAG = "AnimateBox"
val FILTER = "aemu:I"
val PACKAGE_NAME = "com.google.AnimateBox"

class AnimateBox(val inst: Instrumentation) {
  val adb = Adb(inst.getUiAutomation())
  val context = inst.getTargetContext()
  val device = UiDevice.getInstance(inst)
  var watcher = LogcatWatcher(adb, FILTER)

  fun start() {
    Log.i(TAG, "Starting animation app")

    // Stop the animation app if it is already running so we start from a clean state.
    adb.shell("am force-stop $PACKAGE_NAME")

    // Reset the logcat watcher to clear out any previous messages.
    watcher = LogcatWatcher(adb, FILTER)

    device.pressHome()
    val launchIntent = context.getPackageManager().getLaunchIntentForPackage(PACKAGE_NAME)
    launchIntent!!.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TASK)
    context.startActivity(launchIntent)

    Assert.assertNotNull(device.wait(Until.hasObject(By.pkg(PACKAGE_NAME).depth(0)), 5000))
    // The animation app can sometimes take a while to start.
    Assert.assertTrue(eventually(300, 100) { watcher.containsNewLine("--STARTED--") })

    // There may be a dialog indicating the app is full screen. Click it.
    val fullScreenDialog = device.wait(Until.findObject(By.text("Got it")), 500)
    fullScreenDialog?.click()
  }

  fun pause() {
    // Keycodes can sometimes get lost so try to pause multiple times.
    Assert.assertTrue(
      eventually(5, 500) {
        device.pressKeyCode(KeyEvent.KEYCODE_P)
        watcher.containsNewLine("Pausing animation")
      }
    )
  }
}
