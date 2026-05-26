package com.android.tools.e2etests.input

import android.content.Intent
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.UiDevice
import androidx.test.uiautomator.Until
import com.android.emulator.control.AndroidEvent
import com.android.emulator.control.InputEvent
import com.android.emulator.control.Pen
import com.android.emulator.control.PenEvent
import com.android.emulator.control.Touch
import com.android.tools.e2etests.grpc.EmulatorController
import com.google.protobuf.Empty
import io.grpc.stub.StreamObserver
import java.util.concurrent.TimeUnit
import org.junit.AfterClass
import org.junit.Assert
import org.junit.Before
import org.junit.BeforeClass
import org.junit.Ignore
import org.junit.Test

@Ignore("Bug: 515725062")
class PenInputTest {

  companion object {
    @JvmStatic lateinit var sharedObserver: EventObserver

    @BeforeClass
    @JvmStatic
    fun setUpClass() {
      sharedObserver = EventObserver.observer("virtio_input_multi_touch_1")
      sharedObserver.start()

      // Launch the activity once for all tests in this class
      val context = InstrumentationRegistry.getInstrumentation().getTargetContext()
      val intent =
          Intent(context, InputTestActivity::class.java).apply {
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP)
          }
      InputTestActivity.focusLatch = java.util.concurrent.CountDownLatch(1)
      context.startActivity(intent)

      // Wait for activity to be visible
      val device = UiDevice.getInstance(InstrumentationRegistry.getInstrumentation())
      Assert.assertTrue(
          device.wait(
              Until.hasObject(By.pkg(context.packageName).depth(0)),
              TestConstants.DEFAULT_TIMEOUT_MS,
          )
      )

      // Wait for window focus
      val hasFocus =
          InputTestActivity.focusLatch.await(
              TestConstants.DEFAULT_TIMEOUT_SECONDS,
              TimeUnit.SECONDS,
          )
      Assert.assertTrue("Timed out waiting for window focus", hasFocus)
    }

    @AfterClass
    @JvmStatic
    fun tearDownClass() {
      sharedObserver.stop()
      InputTestActivity.finishActivity()
    }
  }

  @Before
  fun setUp() {
    InputTestActivity.clearEvents()
  }

  private fun pen(
      x: Int,
      y: Int,
      pressure: Int,
      rubber: Boolean = false,
      button: Boolean = false,
  ): Pen {
    return Pen.newBuilder()
        .setLocation(
            Touch.newBuilder().setX(x).setY(y).setIdentifier(1).setPressure(pressure).build()
        )
        .setButtonPressed(button)
        .setRubberPointer(rubber)
        .build()
  }

  private fun penEvent(vararg pens: Pen): InputEvent {
    val builder = PenEvent.newBuilder()
    pens.forEach { builder.addEvents(it) }
    return InputEvent.newBuilder().setPenEvent(builder.build()).build()
  }

  private fun createRequestObserver(): StreamObserver<InputEvent> {
    val responseObserver =
        object : StreamObserver<Empty> {
          override fun onNext(value: Empty?) {}

          override fun onError(t: Throwable?) {}

          override fun onCompleted() {}
        }
    return EmulatorController.asyncDefaultDeadline().streamInputEvent(responseObserver)
  }

  /** Verifies that sending a pen event results in a stylus tool type in Android. */
  @Test
  fun testPenTouch() {
    val targetX = 100
    val targetY = 200

    sharedObserver
        .waitForEvents(2, TestConstants.DEFAULT_TIMEOUT_MS) {
          val requestObserver = createRequestObserver()
          requestObserver.onNext(penEvent(pen(targetX, targetY, 1)))
          requestObserver.onNext(penEvent(pen(targetX, targetY, 0)))
          requestObserver.onCompleted()
        }
        .assertSizeAtLeast(2, "Should receive raw events for pen touch")

    val receivedEvents = InputTestActivity.touchEvents
    Assert.assertTrue("Should receive at least one event", receivedEvents.isNotEmpty())

    val lastEvent = receivedEvents.last()
    // TOOL_TYPE_STYLUS is 2
    Assert.assertEquals("Tool type should be stylus", 2, lastEvent.toolType)
  }

  /** Verifies that sending a pen event with rubber pointer results in eraser tool type. */
  @Test
  fun testPenRubber() {
    val targetX = 100
    val targetY = 200

    sharedObserver
        .waitForEvents(2, TestConstants.DEFAULT_TIMEOUT_MS) {
          val requestObserver = createRequestObserver()
          requestObserver.onNext(penEvent(pen(targetX, targetY, 1, rubber = true, button = true)))
          requestObserver.onNext(penEvent(pen(targetX, targetY, 0, rubber = true, button = false)))
          requestObserver.onCompleted()
        }
        .assertSizeAtLeast(2, "Should receive raw events for pen rubber")

    val receivedEvents = InputTestActivity.touchEvents
    Assert.assertTrue("Should receive at least one event", receivedEvents.isNotEmpty())

    val lastEvent = receivedEvents.last()
    // TOOL_TYPE_ERASER is 4
    Assert.assertEquals("Tool type should be eraser", 4, lastEvent.toolType)
  }

  private fun androidEvent(type: Int, code: Int, value: Int): InputEvent {
    return InputEvent.newBuilder()
        .setAndroidEvent(
            AndroidEvent.newBuilder().setType(type).setCode(code).setValue(value).build()
        )
        .build()
  }

  /** Debug test to send raw events logged by the emulator for rubber pen. */
  @Test
  fun testPenRubberRaw() {
    sharedObserver
        .waitForEvents(2, TestConstants.DEFAULT_TIMEOUT_MS) {
          val requestObserver = createRequestObserver()

          // Down sequence
          requestObserver.onNext(androidEvent(EvDev.EV_ABS, EvDev.ABS_MT_SLOT, 0))
          requestObserver.onNext(androidEvent(EvDev.EV_ABS, EvDev.ABS_MT_TRACKING_ID, 0))
          requestObserver.onNext(androidEvent(EvDev.EV_ABS, EvDev.ABS_MT_POSITION_X, 3033))
          requestObserver.onNext(androidEvent(EvDev.EV_ABS, EvDev.ABS_MT_POSITION_Y, 2730))
          requestObserver.onNext(androidEvent(EvDev.EV_SYN, EvDev.SYN_REPORT, 0))

          // Up sequence
          requestObserver.onNext(androidEvent(EvDev.EV_ABS, EvDev.ABS_MT_SLOT, 0))
          requestObserver.onNext(androidEvent(EvDev.EV_ABS, EvDev.ABS_MT_TRACKING_ID, -1))
          requestObserver.onNext(androidEvent(EvDev.EV_SYN, EvDev.SYN_REPORT, 0))

          requestObserver.onCompleted()
        }
        .assertSizeAtLeast(2, "Should receive raw events for pen rubber raw")
  }
}
