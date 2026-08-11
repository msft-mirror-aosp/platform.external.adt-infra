package com.android.tools.e2etests.clock

import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.UiDevice
import androidx.test.uiautomator.UiSelector
import com.android.tools.testlib.verifier.CtsVerifierResource
import com.android.tools.testlib.verifier.startTest
import com.android.tools.testlib.verifier.takeScreenshot
import org.junit.Assert
import org.junit.Rule
import org.junit.Test

val TAG = "ClockTest"

class ClockTest {
  val inst = InstrumentationRegistry.getInstrumentation()
  val device = UiDevice.getInstance(inst)

  @get:Rule val ctsVerifierRule = CtsVerifierResource()

  @Test
  fun alarmsAndTimersShowAlarmsTest() {
    startTest(device, "Alarms and Timers Tests")

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
