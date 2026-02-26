package com.android.tools.e2etests.boot

import android.util.Log
import com.android.tools.e2etests.grpc.EmulatorController
import com.google.protobuf.Empty
import java.util.concurrent.TimeUnit
import org.junit.Assert
import org.junit.Test

val TAG = "BootTest"

class BootTest {

  @Test
  fun statusIsBooted() {
    val resp =
      EmulatorController.stub!!.withDeadlineAfter(10, TimeUnit.SECONDS)
        .getStatus(Empty.getDefaultInstance())

    Assert.assertTrue(resp.getBooted())
  }

  @Test
  fun bootNotificationTime() {
    val notifications =
      EmulatorController.stub!!.withDeadlineAfter(10, TimeUnit.SECONDS)
        .streamNotification(Empty.getDefaultInstance())
    var booted = false
    for (n in notifications) {
      Log.i(TAG, "Notification type: ${n.typeCase}")
      if (n.hasBooted()) {
        booted = true
        Log.i(TAG, "Boot completed in ${n.getBooted().getTime()} ms")
        break
      }
    }

    Assert.assertTrue(booted)
  }
}
