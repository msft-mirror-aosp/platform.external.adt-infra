package com.android.tools.e2etests.input

import android.content.Intent
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.UiDevice
import androidx.test.uiautomator.Until
import com.android.emulator.control.InputEvent
import com.android.emulator.control.KeyboardEvent
import com.android.tools.e2etests.grpc.EmulatorController
import com.google.protobuf.Empty
import io.grpc.stub.StreamObserver
import java.util.concurrent.TimeUnit
import org.junit.AfterClass
import org.junit.Assert
import org.junit.Before
import org.junit.BeforeClass
import org.junit.Test

class KeyboardInputTest {
  companion object {
    @JvmStatic lateinit var sharedObserver: EventObserver

    @BeforeClass
    @JvmStatic
    fun setUpClass() {
      try {
        sharedObserver = EventObserver.observer("QEMU Virtio Keyboard")
      } catch (e: IllegalArgumentException) {
        // Try the emu-now device name.
        sharedObserver = EventObserver.observer("qwerty2")
      }
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

  /**
   * Verifies that sending a string of characters via Emulator Controller results in them being
   * typed into the focused text field.
   */
  @Test
  fun testAlphabetDelivery() {
    // Use a short string to avoid SYN_DROPPED errors.
    // Sending a long string causes the kernel buffer to overflow
    // because getevent reads too slowly over the shell IPC.
    val text = "hello"

    sharedObserver
        .waitForEvents(10, 1000) {
          val requestObserver = createRequestObserver()
          val event =
              InputEvent.newBuilder()
                  .setKeyEvent(KeyboardEvent.newBuilder().setText(text).build())
                  .build()
          requestObserver.onNext(event)
          requestObserver.onCompleted()
        }
        .assertSizeAtLeast(10, "Should receive events for all characters")
        .assertContains(EvDev.KEY_H, 1, "Should contain 'h' Down")
  }

  /** Verifies that sending "GoHome" key event takes the user to the home screen. */
  @Test
  fun testGoHome() {
    sharedObserver
        .waitForEvents(2, 1000) {
          sendKeyboardEvents(keyEvent("GoHome", KeyboardEvent.KeyEventType.keypress))
        }
        .assertContains(EvDev.KEY_HOME, 1, "Should receive GoHome Down")
        .assertContains(EvDev.KEY_HOME, 0, "Should receive GoHome Up")
  }

  /** Verifies that sending "GoBack" key event closes the current activity. */
  @Test
  fun testGoBack() {
    sharedObserver
        .waitForEvents(2, 1000) {
          sendKeyboardEvents(keyEvent("GoBack", KeyboardEvent.KeyEventType.keypress))
        }
        .assertContains(EvDev.KEY_BACK, 1, "Should receive GoBack Down")
        .assertContains(EvDev.KEY_BACK, 0, "Should receive GoBack Up")
  }

  /** Verifies that sending "AppSwitch" key event shows the recent apps screen. */
  @Test
  fun testAppSwitch() {
    sharedObserver
        .waitForEvents(2, 1000) {
          sendKeyboardEvents(keyEvent("AppSwitch", KeyboardEvent.KeyEventType.keypress))
        }
        .assertContains(EvDev.KEY_APP_SWITCH, 1, "Should receive AppSwitch Down")
        .assertContains(EvDev.KEY_APP_SWITCH, 0, "Should receive AppSwitch Up")
  }

  /** Verifies that manual keyboard modifiers (Shift + key) work correctly. */
  @Test
  fun testKeyboardModifiers() {
    sharedObserver
        .waitForEvents(4, 1000) {
          sendKeyboardEvents(
              keyEvent("Shift", KeyboardEvent.KeyEventType.keydown),
              keyEvent("a", KeyboardEvent.KeyEventType.keypress), // Generates down and up event.
              keyEvent("Shift", KeyboardEvent.KeyEventType.keyup),
          )
        }
        .assertSizeAtLeast(4, "Should receive events for modifiers")
        .assertContains(EvDev.KEY_LEFTSHIFT, "Should contain Shift key")
        .assertContains(EvDev.KEY_A, "Should contain A key")
  }

  /** Verifies explicit keydown and keyup events. */
  @Test
  fun testKeyUpDownPress() {
    sharedObserver
        .waitForEvents(2, 1000) {
          sendKeyboardEvents(
              keyEvent("b", KeyboardEvent.KeyEventType.keydown),
              keyEvent("b", KeyboardEvent.KeyEventType.keyup),
          )
        }
        .assertSize(2, "Should receive exactly 2 events")
        .assertContains(EvDev.KEY_B, 1, "Should receive Key B Down")
        .assertContains(EvDev.KEY_B, 0, "Should receive Key B Up")
  }

  /** Verifies sending events with keyCode and Evdev code type. */
  @Test
  fun testKeyCodes() {
    sharedObserver
        .waitForEvents(2, 1000) {
          val requestObserver = createRequestObserver()
          // 30 is KEY_A in evdev
          val event =
              InputEvent.newBuilder()
                  .setKeyEvent(
                      KeyboardEvent.newBuilder()
                          .setKeyCode(EvDev.KEY_A)
                          .setCodeType(KeyboardEvent.KeyCodeType.Evdev)
                          .setEventType(KeyboardEvent.KeyEventType.keypress)
                          .build(),
                  )
                  .build()

          requestObserver.onNext(event)
          requestObserver.onCompleted()
        }
        .assertContains(EvDev.KEY_A, "Should receive events for key code KEY_A")
  }

  private fun sendKeyboardEvents(vararg events: KeyboardEvent) {
    val requestObserver = createRequestObserver()
    events.forEach { requestObserver.onNext(InputEvent.newBuilder().setKeyEvent(it).build()) }
    requestObserver.onCompleted()
  }

  private fun keyEvent(key: String, type: KeyboardEvent.KeyEventType): KeyboardEvent {
    return KeyboardEvent.newBuilder().setKey(key).setEventType(type).build()
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
