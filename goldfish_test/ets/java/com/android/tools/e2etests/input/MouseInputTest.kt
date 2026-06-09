package com.android.tools.e2etests.input

import android.content.Intent
import android.view.MotionEvent
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.UiDevice
import androidx.test.uiautomator.Until
import com.android.emulator.control.InputEvent
import com.android.emulator.control.MouseEvent
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

@Ignore
class MouseInputTest {

  companion object {
    @JvmStatic lateinit var sharedObserver: EventObserver

    @BeforeClass
    @JvmStatic
    fun setUpClass() {
      // We observe the multi-touch device because the emulator translates mouse events
      // to touch events in this configuration.
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

  /** Verifies that sending a mouse move event results in a hover event in Android. */
  @Ignore(
      "We currently translate mouse events to touch events, because of this we cannot send hover events. Bug: 515726317"
  )
  @Test
  fun testMouseMove() {
    val targetX = 150
    val targetY = 250

    sharedObserver
        .waitForEvents(1, 1000, filter = { true }) {
          val requestObserver = createRequestObserver()
          requestObserver.onNext(mouseEvent(targetX, targetY, 0))
          requestObserver.onCompleted()
        }
        .assertSizeAtLeast(1, "Should receive at least one raw event for mouse move")

    val receivedEvents = InputTestActivity.genericMotionEvents
    Assert.assertTrue(
        "Should receive at least one generic motion event",
        receivedEvents.isNotEmpty(),
    )
    // Find an event that is a hover move (action 7) or similar
    val hoverEvent = receivedEvents.find {
      it.action == MotionEvent.ACTION_HOVER_MOVE || it.action == MotionEvent.ACTION_HOVER_ENTER
    }
    Assert.assertNotNull("Should find a hover event", hoverEvent)
    Assert.assertEquals("X coordinate should match", targetX.toFloat(), hoverEvent!!.x, 5.0f)
    Assert.assertEquals("Y coordinate should match", targetY.toFloat(), hoverEvent.y, 5.0f)
  }

  /** Verifies that sending mouse drag (move while clicked) results in touch move events. */
  @Test
  fun testMouseDrag() {
    val startX = 150
    val startY = 250
    val endX = 200
    val endY = 300

    sharedObserver
        .waitForEvents(3, 1000) {
          val requestObserver = createRequestObserver()
          requestObserver.onNext(mouseEvent(startX, startY, 1)) // Down
          requestObserver.onNext(mouseEvent(endX, endY, 1)) // Move
          requestObserver.onNext(mouseEvent(endX, endY, 0)) // Up
          requestObserver.onCompleted()
        }
        .assertSizeAtLeast(3, "Should receive raw events for mouse drag")

    val receivedEvents = InputTestActivity.touchEvents
    Assert.assertTrue("Should receive touch events", receivedEvents.isNotEmpty())

    val hasDown = receivedEvents.any { it.action == MotionEvent.ACTION_DOWN }
    val hasMove = receivedEvents.any { it.action == MotionEvent.ACTION_MOVE }
    val hasUp = receivedEvents.any { it.action == MotionEvent.ACTION_UP }

    Assert.assertTrue("Should detect ACTION_DOWN", hasDown)
    Assert.assertTrue("Should detect ACTION_MOVE", hasMove)
    Assert.assertTrue("Should detect ACTION_UP", hasUp)

    val lastEvent = receivedEvents.last()
    Assert.assertEquals("X coordinate should match end point", endX.toFloat(), lastEvent.x, 5.0f)
    Assert.assertEquals("Y coordinate should match end point", endY.toFloat(), lastEvent.y, 5.0f)
  }

  /** Verifies that sending mouse click (button down/up) results in touch events. */
  @Test
  fun testMouseClick() {
    val targetX = 200
    val targetY = 300

    sharedObserver
        .waitForEvents(2, 1000, filter = { true }) {
          val requestObserver = createRequestObserver()
          requestObserver.onNext(mouseEvent(targetX, targetY, 1)) // Down
          requestObserver.onNext(mouseEvent(targetX, targetY, 0)) // Up
          requestObserver.onCompleted()
        }
        .assertSizeAtLeast(2, "Should receive raw events for mouse click")

    val receivedEvents = InputTestActivity.touchEvents
    Assert.assertTrue("Should receive at least one touch event", receivedEvents.isNotEmpty())
    // Should see ACTION_DOWN (0) and ACTION_UP (1)
    val hasDown = receivedEvents.any { it.action == MotionEvent.ACTION_DOWN }
    val hasUp = receivedEvents.any { it.action == MotionEvent.ACTION_UP }
    Assert.assertTrue("Should detect ACTION_DOWN", hasDown)
    Assert.assertTrue("Should detect ACTION_UP", hasUp)
  }

  private fun mouseEvent(x: Int, y: Int, buttons: Int): InputEvent {
    return InputEvent.newBuilder()
        .setMouseEvent(MouseEvent.newBuilder().setX(x).setY(y).setButtons(buttons).build())
        .build()
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
