package com.android.tools.e2etests.input

import android.content.Intent
import android.util.Log
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.UiDevice
import androidx.test.uiautomator.Until
import com.android.emulator.control.InputEvent
import com.android.emulator.control.Touch
import com.android.emulator.control.TouchEvent
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

@Ignore(
    "Bug: 515773679. Fails on phone profiles due to event delivery issues, despite baseline work."
)
class TouchInputTest {

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

  /** Verifies that a sequence of touch events is delivered in order and measures jitter. */
  @Test
  fun testSequenceDeliveryAndJitter() {
    val numEvents = 10
    val intervalMs = 50L

    sharedObserver
        .waitForEvents(10, TestConstants.DEFAULT_TIMEOUT_MS) {
          val requestObserver = createRequestObserver()
          for (i in 0 until numEvents) {
            requestObserver.onNext(touchEvent(touch(100 + i * 10, 100 + i * 10)))
            Thread.sleep(intervalMs)
          }
          requestObserver.onCompleted()
        }
        .assertSizeAtLeast(10, "Should receive raw events for sequence")

    val receivedEvents = InputTestActivity.touchEvents
    Assert.assertEquals("Should receive all events", numEvents, receivedEvents.size)

    // Verify jitter
    for (i in 0 until numEvents - 1) {
      val receivedInterval = receivedEvents[i + 1].timeNanos - receivedEvents[i].timeNanos
      val receivedIntervalMs = receivedInterval / 1_000_000
      Log.d("TouchInputTest", "Received interval $i: $receivedIntervalMs ms")
      // Verify it's close to intervalMs (e.g. within 20ms tolerance)
      Assert.assertTrue(
          "Jitter too high: $receivedIntervalMs ms",
          Math.abs(receivedIntervalMs - intervalMs) < 20,
      )
    }
  }

  /** Verifies that touch events at specific coordinates arrive correctly in Android. */
  @Test
  fun testCoordinateValidation() {
    val targetX = 100
    val targetY = 200

    sharedObserver
        .waitForEvents(2, TestConstants.DEFAULT_TIMEOUT_MS) {
          val requestObserver = createRequestObserver()
          requestObserver.onNext(touchEvent(touch(targetX, targetY, 1, 1)))
          requestObserver.onNext(touchEvent(touch(targetX, targetY, 1, 0)))
          requestObserver.onCompleted()
        }
        .assertSizeAtLeast(2, "Should receive raw events for coordinate validation")

    val receivedEvents = InputTestActivity.touchEvents
    Assert.assertTrue("Should receive at least one event", receivedEvents.isNotEmpty())

    val lastEvent = receivedEvents.last()
    // Verify coordinates within a delta of 5 pixels
    Assert.assertEquals("X coordinate should match", targetX.toFloat(), lastEvent.x, 5.0f)
    Assert.assertEquals("Y coordinate should match", targetY.toFloat(), lastEvent.y, 5.0f)
  }

  /**
   * Verifies that the emulator correctly handles and delivers multi-touch events with multiple
   * fingers.
   */
  @Test
  fun testMultiFingerTouch() {
    sharedObserver
        .waitForEvents(2, TestConstants.DEFAULT_TIMEOUT_MS) {
          val requestObserver = createRequestObserver()
          requestObserver.onNext(touchEvent(touch(100, 200, 1, 1), touch(200, 300, 2, 1)))
          requestObserver.onNext(touchEvent(touch(100, 200, 1, 0), touch(200, 300, 2, 0)))
          requestObserver.onCompleted()
        }
        .assertSizeAtLeast(2, "Should receive raw events for multi-finger touch")

    val receivedEvents = InputTestActivity.touchEvents
    Assert.assertTrue("Should receive at least one event", receivedEvents.isNotEmpty())

    // Find an event with pointerCount == 2
    val hasMultiTouch = receivedEvents.any { it.pointerCount == 2 }
    Assert.assertTrue("Should detect multi-touch with 2 pointers", hasMultiTouch)
  }

  /** Verifies that touch events deliver pressure values correctly. */
  @Test
  fun testTouchPressure() {
    val targetPressure = 1

    sharedObserver
        .waitForEvents(1, TestConstants.DEFAULT_TIMEOUT_MS) {
          val requestObserver = createRequestObserver()
          requestObserver.onNext(touchEvent(touch(100, 200, 1, targetPressure)))
          requestObserver.onCompleted()
        }
        .assertSizeAtLeast(1, "Should receive raw events for touch pressure")

    val receivedEvents = InputTestActivity.touchEvents
    Assert.assertTrue("Should receive at least one event", receivedEvents.isNotEmpty())

    val lastEvent = receivedEvents.last()
    // Verify pressure is greater than 0 when we sent non-zero
    Assert.assertTrue("Pressure should be greater than 0", lastEvent.pressure > 0.0f)
  }

  /** Verifies that the emulator correctly tracks pointer IDs across multiple events. */
  @Test
  fun testMultiTouchContinuity() {
    sharedObserver
        .waitForEvents(5, TestConstants.DEFAULT_TIMEOUT_MS) {
          val requestObserver = createRequestObserver()
          // 1. Finger 1 Down
          requestObserver.onNext(touchEvent(touch(100, 100, 1, 1)))
          // 2. Finger 2 Down
          requestObserver.onNext(touchEvent(touch(100, 100, 1, 1), touch(200, 200, 2, 1)))
          // 3. Finger 1 Move
          requestObserver.onNext(touchEvent(touch(150, 150, 1, 1), touch(200, 200, 2, 1)))
          // 4. Finger 1 Up, Finger 2 stays
          requestObserver.onNext(touchEvent(touch(150, 150, 1, 0), touch(200, 200, 2, 1)))
          // 5. Finger 2 Up
          requestObserver.onNext(touchEvent(touch(200, 200, 2, 0)))
          requestObserver.onCompleted()
        }
        .assertSizeAtLeast(5, "Should receive raw events for continuity test")

    val receivedEvents = InputTestActivity.touchEvents
    val hasTwoPointers = receivedEvents.any { it.pointerCount == 2 }
    Assert.assertTrue("Should detect 2 pointers during sequence", hasTwoPointers)
  }

  /** Verifies multi-touch with up to 10 fingers (max supported by emulator). */
  @Test
  fun testMaxFingersTouch() {
    sharedObserver
        .waitForEvents(2, TestConstants.DEFAULT_TIMEOUT_MS) {
          val requestObserver = createRequestObserver()
          val touchesDown =
              (1..10).map { i -> touch(100 + i * 20, 100 + i * 20, i, 1) }.toTypedArray()
          requestObserver.onNext(touchEvent(*touchesDown))

          val touchesUp =
              (1..10).map { i -> touch(100 + i * 20, 100 + i * 20, i, 0) }.toTypedArray()
          requestObserver.onNext(touchEvent(*touchesUp))
          requestObserver.onCompleted()
        }
        .assertSizeAtLeast(2, "Should receive raw events for max fingers test")

    val receivedEvents = InputTestActivity.touchEvents
    val hasMaxPointers = receivedEvents.any { it.pointerCount == 10 }
    Assert.assertTrue("Should detect 10 pointers during sequence", hasMaxPointers)
  }

  private fun touch(x: Int, y: Int, id: Int = 1, pressure: Int = 1): Touch {
    return Touch.newBuilder().setX(x).setY(y).setIdentifier(id).setPressure(pressure).build()
  }

  private fun touchEvent(vararg touches: Touch): InputEvent {
    val builder = TouchEvent.newBuilder()
    touches.forEach { builder.addTouches(it) }
    return InputEvent.newBuilder().setTouchEvent(builder.build()).build()
  }

  private fun createEmptyObserver() =
      object : StreamObserver<Empty> {
        override fun onNext(value: Empty?) {}

        override fun onError(t: Throwable?) {}

        override fun onCompleted() {}
      }

  private fun createRequestObserver(): StreamObserver<InputEvent> {
    return EmulatorController.asyncDefaultDeadline().streamInputEvent(createEmptyObserver())
  }
}
