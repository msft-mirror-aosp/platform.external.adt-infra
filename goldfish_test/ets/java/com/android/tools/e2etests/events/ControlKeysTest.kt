package com.android.tools.e2etests.events

import android.util.Log
import androidx.test.platform.app.InstrumentationRegistry
import com.android.emulator.control.InputEvent
import com.android.emulator.control.KeyboardEvent
import com.android.tools.e2etests.grpc.EmulatorController
import com.android.tools.testlib.emu.Adb
import com.android.tools.testlib.emu.eventually
import com.google.protobuf.Empty
import io.grpc.Status
import io.grpc.stub.StreamObserver
import java.io.FileInputStream
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import org.junit.Assert
import org.junit.Test

val TAG = "ControlKeysTest"

// TODO(kmagic): Add the volume key tests once they can be deflaked.
class ControlKeysTest {

  val adb = Adb(InstrumentationRegistry.getInstrumentation().getUiAutomation())

  @Test
  fun powerButton() {
    sendKeypress("Power")
    Assert.assertTrue(eventually(10, 100) { isAsleep() })

    sendKeypress("Power")
    Assert.assertTrue(eventually(10, 100) { isAwake() })
  }

  @Test
  fun screenshot() {
    adb.shell("rm -rf /storage/emulated/0/Pictures/Screenshots/*")
    adb.shell("input keyevent 120")
    Assert.assertTrue(
      eventually(10, 100) {
        var screenshotCreated = false
        for (file in adb.shell("ls /storage/emulated/0/Pictures/Screenshots/")) {
          if (file.contains("Screenshot_")) {
            screenshotCreated = true
          }
        }
        screenshotCreated
      }
    )
  }

  fun getWakefulnessLine(): String {
    for (line in adb.shell("dumpsys power")) {
      if (line.contains("mWakefulness=")) {
        return line.trim()
      }
    }
    return ""
  }

  fun isAwake(): Boolean {
    return getWakefulnessLine() == "mWakefulness=Awake"
  }

  fun isAsleep(): Boolean {
    var line = getWakefulnessLine()
    return line == "mWakefulness=Asleep" || line == "mWakefulness=Dozing"
  }

  fun sendKeypress(key: String) {
    val finishLatch = CountDownLatch(1)

    val responseObserver = InputEventObserver(finishLatch)
    val requestObserver =
      EmulatorController.asyncDefaultDeadline().streamInputEvent(responseObserver)
    try {
      Log.i(TAG, "Sending keypress ${key}")

      // 100 ms for keypress duration should be ok. See fig 2 in:
      // https://userinterfaces.aalto.fi/136Mkeystrokes/resources/chi-18-analysis.pdf
      val downReq =
        InputEvent.newBuilder()
          .setKeyEvent(
            KeyboardEvent.newBuilder()
              .setKey(key)
              .setEventType(KeyboardEvent.KeyEventType.keydown)
              .build()
          )
          .build()
      requestObserver.onNext(downReq)
      Thread.sleep(100)
      val upReq =
        InputEvent.newBuilder()
          .setKeyEvent(
            KeyboardEvent.newBuilder()
              .setKey(key)
              .setEventType(KeyboardEvent.KeyEventType.keyup)
              .build()
          )
          .build()
      requestObserver.onNext(upReq)
    } catch (e: RuntimeException) {
      // Cancel RPC
      requestObserver.onError(e)
      throw e
    }
    // Mark the end of requests
    requestObserver.onCompleted()

    // Receiving happens asynchronously
    finishLatch.await(10, TimeUnit.SECONDS)
  }
}

class InputEventObserver(val finishLatch: CountDownLatch) : StreamObserver<Empty> {
  override fun onNext(empty: Empty) {}

  override fun onError(t: Throwable) {
    val status = Status.fromThrowable(t)
    Log.e(TAG, "StreamInputEvent Failed: ${status.toString()}")
    finishLatch.countDown()
  }

  override fun onCompleted() {
    finishLatch.countDown()
  }
}
