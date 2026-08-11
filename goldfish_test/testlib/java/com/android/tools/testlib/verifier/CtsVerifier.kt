package com.android.tools.testlib.verifier

import android.util.Log
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.platform.io.PlatformTestStorageRegistry
import androidx.test.uiautomator.UiDevice
import androidx.test.uiautomator.UiScrollable
import androidx.test.uiautomator.UiSelector
import com.android.emulator.control.ImageFormat
import com.android.tools.e2etests.grpc.EmulatorController
import com.android.tools.testlib.emu.Adb
import org.junit.rules.ExternalResource

val PACKAGE_NAME = "com.android.cts.verifier"
val ACTIVITY = "com.android.cts.verifier/com.android.cts.verifier.CtsVerifierActivity"
val TAG = "CtsVerifierTest"

class CtsVerifierResource : ExternalResource() {

  override fun before() {
    val inst = InstrumentationRegistry.getInstrumentation()
    val device = UiDevice.getInstance(inst)
    val adb = Adb(inst.getUiAutomation())
    adb.shell("am force-stop $PACKAGE_NAME")

    device.pressHome()
    adb.shell("am start -n $ACTIVITY")
  }

  override fun after() {
    val inst = InstrumentationRegistry.getInstrumentation()
    val device = UiDevice.getInstance(inst)
    var moreOptions = device.findObject(UiSelector().description("More options"))
    if (!moreOptions.exists()) {
      device.pressBack()
      moreOptions = device.findObject(UiSelector().description("More options"))
      if (!moreOptions.exists()) {
        Log.e(TAG, "Failed to find More options button.")
        return
      }
    }
    moreOptions.click()
    device.findObject(UiSelector().text("Export")).click()
    val reportPathText = device.findObject(UiSelector().textStartsWith("Report saved to")).getText()
    val reportPath = reportPathText.substringAfter("Report saved to: ")
    // NOTE: This process will not have permission to read the file so test
    // sequencer will need to pull it from the device.
    Log.i(TAG, "Report path: $reportPath")
  }
}

// Scrolls to a test in the list and clicks it.
fun startTest(device: UiDevice, testName: String) {
  val listView = UiScrollable(UiSelector().scrollable(true))
  listView.scrollIntoView(UiSelector().text(testName))
  device.waitForIdle(10000)
  device.findObject(UiSelector().text(testName)).click()

  // Dismiss the dialog if it exists. It only appears the first time verifier
  // is run.
  val dialog = device.findObject(UiSelector().text("OK"))
  if (dialog.exists()) {
    dialog.click()
  }
}

fun takeScreenshot(name: String) {
  val imageFormat = ImageFormat.newBuilder().setFormat(ImageFormat.ImgFormat.PNG).build()
  val resp = EmulatorController.defaultDeadline().getScreenshot(imageFormat)
  val testStorage = PlatformTestStorageRegistry.getInstance()
  testStorage.openOutputFile(name).use { it.write(resp.getImage().toByteArray()) }
}
