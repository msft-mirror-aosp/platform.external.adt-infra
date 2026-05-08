// Copyright (C) 2026 The Android Open Source Project
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
// http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
package com.android.tools.e2etests.input

import android.content.Intent
import android.view.KeyEvent
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.UiDevice
import androidx.test.uiautomator.Until
import com.android.emulator.control.AndroidEvent
import com.android.emulator.control.InputEvent
import com.android.tools.e2etests.grpc.EmulatorController
import com.google.protobuf.Empty
import io.grpc.stub.StreamObserver
import java.util.concurrent.TimeUnit
import org.junit.After
import org.junit.AfterClass
import org.junit.Assert
import org.junit.Before
import org.junit.BeforeClass
import org.junit.Test

class AndroidInputTest {

  companion object {
    @JvmStatic lateinit var sharedObserver: EventObserver

    @BeforeClass
    @JvmStatic
    fun setUpClass() {
      sharedObserver = EventObserver.observer("QEMU Virtio Keyboard")
      sharedObserver.start()
    }

    @AfterClass
    @JvmStatic
    fun tearDownClass() {
      sharedObserver.stop()
    }
  }

  @Before
  fun setUp() {
    InputTestActivity.clearEvents()
    // Launch the activity
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
        InputTestActivity.focusLatch.await(TestConstants.DEFAULT_TIMEOUT_SECONDS, TimeUnit.SECONDS)
    Assert.assertTrue("Timed out waiting for window focus", hasFocus)
  }

  @After
  fun tearDown() {
    InputTestActivity.finishActivity()
  }

  /** Verifies that sending raw evdev events for a key press works. */
  @Test
  fun testRawEvdevEvent() {
    sharedObserver
        .waitForEvents(4, TestConstants.DEFAULT_TIMEOUT_MS, filter = { true }) {
          val requestObserver = createRequestObserver()
          // Key A Down
          requestObserver.onNext(
              InputEvent.newBuilder()
                  .setAndroidEvent(
                      AndroidEvent.newBuilder()
                          .setType(EvDev.EV_KEY)
                          .setCode(EvDev.KEY_A)
                          .setValue(1)
                          .build()
                  )
                  .build()
          )
          // Sync
          requestObserver.onNext(
              InputEvent.newBuilder()
                  .setAndroidEvent(
                      AndroidEvent.newBuilder()
                          .setType(EvDev.EV_SYN)
                          .setCode(EvDev.SYN_REPORT)
                          .setValue(0)
                          .build()
                  )
                  .build()
          )
          // Key A Up
          requestObserver.onNext(
              InputEvent.newBuilder()
                  .setAndroidEvent(
                      AndroidEvent.newBuilder()
                          .setType(EvDev.EV_KEY)
                          .setCode(EvDev.KEY_A)
                          .setValue(0)
                          .build()
                  )
                  .build()
          )
          // Sync
          requestObserver.onNext(
              InputEvent.newBuilder()
                  .setAndroidEvent(
                      AndroidEvent.newBuilder()
                          .setType(EvDev.EV_SYN)
                          .setCode(EvDev.SYN_REPORT)
                          .setValue(0)
                          .build()
                  )
                  .build()
          )
          requestObserver.onCompleted()
        }
        .assertSizeAtLeast(4, "Should receive at least 4 events")
        .assertContains(EvDev.KEY_A, 1, "Should contain Key A Down (code 30)")
        .assertContains(EvDev.KEY_A, 0, "Should contain Key A Up (code 30)")

    // Also verify that the activity received the event
    val receivedEvents = InputTestActivity.keyEvents
    val receivedCodes = receivedEvents.map { it.keyCode }
    Assert.assertTrue(
        "Should receive key event for A in Activity. Got events: $receivedCodes",
        receivedEvents.any { it.keyCode == android.view.KeyEvent.KEYCODE_A },
    )
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
