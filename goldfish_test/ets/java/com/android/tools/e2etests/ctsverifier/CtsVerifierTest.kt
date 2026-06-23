package com.android.tools.e2etests.ctsverifier

import android.util.Log
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.platform.io.PlatformTestStorage
import androidx.test.platform.io.PlatformTestStorageRegistry
import androidx.test.uiautomator.UiDevice
import androidx.test.uiautomator.UiScrollable
import androidx.test.uiautomator.UiSelector
import com.android.emulator.control.ImageFormat
import com.android.tools.e2etests.grpc.EmulatorController
import com.android.tools.testlib.emu.Adb
import org.junit.AfterClass
import org.junit.Assert
import org.junit.BeforeClass
import org.junit.Test

val packageName = "com.android.cts.verifier"
val activity = "com.android.cts.verifier/com.android.cts.verifier.CtsVerifierActivity"
val TAG = "CtsVerifierTest"

class CtsVerifierTest {
  val inst = InstrumentationRegistry.getInstrumentation()
  val context = inst.getTargetContext()
  val device = UiDevice.getInstance(inst)
  val adb = Adb(inst.getUiAutomation())
  val testStorage: PlatformTestStorage = PlatformTestStorageRegistry.getInstance()

  companion object {
    @BeforeClass
    @JvmStatic
    fun setUpClass() {
      val inst = InstrumentationRegistry.getInstrumentation()
      val device = UiDevice.getInstance(inst)
      val adb = Adb(inst.getUiAutomation())
      adb.shell("am force-stop $packageName")

      device.pressHome()
      adb.shell("am start -n $activity")
    }

    @AfterClass
    @JvmStatic
    fun tearDownClass() {
      val inst = InstrumentationRegistry.getInstrumentation()
      val device = UiDevice.getInstance(inst)
      device.findObject(UiSelector().description("More options")).click()
      device.findObject(UiSelector().text("Export")).click()
      val reportPathText =
        device.findObject(UiSelector().textStartsWith("Report saved to")).getText()
      val reportPath = reportPathText.substringAfter("Report saved to: ")
      // NOTE: This process will not have permission to read the file so test
      // sequencer will need to pull it from the device.
      Log.i(TAG, "Report path: $reportPath")
    }
  }

  fun startTest(testName: String) {
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
    testStorage.openOutputFile(name).use { it.write(resp.getImage().toByteArray()) }
  }

  @Test
  fun testCtsVerifier() {
    startTest("Alarms and Timers Tests")

    device.findObject(UiSelector().text("Show Alarms Test")).click()
    device.findObject(UiSelector().text("Show Alarms")).click()
    device.waitForIdle(10000)

    // Verify we are on a page that contains the word "Alarm"
    takeScreenshot("alarms_and_timers_show_alarms_test.png")
    Assert.assertTrue(device.findObject(UiSelector().text("Alarm")).exists())

    device.pressBack()
    device.waitForIdle(10000)
    device.findObject(UiSelector().description("Pass")).click()
    device.pressBack()
    device.waitForIdle(10000)
  }
}
