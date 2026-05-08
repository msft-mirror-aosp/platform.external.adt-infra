package com.android.tools.e2etests.input

import android.content.Intent
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.UiDevice
import androidx.test.uiautomator.Until
import com.android.emulator.control.InputEvent
import com.android.emulator.control.WheelEvent
import com.android.tools.e2etests.grpc.EmulatorController
import com.google.protobuf.Empty
import io.grpc.stub.StreamObserver
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import org.junit.Assert
import org.junit.Before
import org.junit.Ignore
import org.junit.Test

@Ignore
class WheelInputTest {

  @Before
  fun setUp() {
    InputTestActivity.clearEvents()
    // Launch the activity
    val context = InstrumentationRegistry.getInstrumentation().getTargetContext()
    val intent =
        Intent(context, InputTestActivity::class.java).apply {
          addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP)
        }
    context.startActivity(intent)

    // Wait for activity to be visible
    val device = UiDevice.getInstance(InstrumentationRegistry.getInstrumentation())
    Assert.assertTrue(
        device.wait(
            Until.hasObject(By.pkg(context.packageName).depth(0)),
            TestConstants.DEFAULT_TIMEOUT_MS,
        )
    )
  }

  /** Verifies that sending a wheel event returns OK (currently unsupported and dropped). */
  @Test
  fun testWheelScroll() {
    val responseObserver =
        object : StreamObserver<Empty> {
          val latch = CountDownLatch(1)
          var completed = false
          var error: Throwable? = null

          override fun onNext(value: Empty?) {}

          override fun onError(t: Throwable?) {
            error = t
            latch.countDown()
          }

          override fun onCompleted() {
            completed = true
            latch.countDown()
          }
        }
    val requestObserver =
        EmulatorController.asyncDefaultDeadline().streamInputEvent(responseObserver)
    val event =
        InputEvent.newBuilder().setWheelEvent(WheelEvent.newBuilder().setDy(120).build()).build()
    requestObserver.onNext(event)
    requestObserver.onCompleted()
    val success =
        responseObserver.latch.await(TestConstants.DEFAULT_TIMEOUT_MS, TimeUnit.MILLISECONDS)
    Assert.assertTrue("Timed out waiting for response", success)
    Assert.assertNull("Should not return error", responseObserver.error)
  }
}
