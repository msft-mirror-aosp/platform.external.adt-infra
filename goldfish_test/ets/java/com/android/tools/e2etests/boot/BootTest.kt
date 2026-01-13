package com.android.tools.e2etests.boot

import com.android.tools.e2etests.grpc.EmulatorController
import com.google.protobuf.Empty
import org.junit.Assert
import org.junit.Test
import java.util.concurrent.TimeUnit

class BootTest {

    @Test
    fun statusIsBooted() {
      val resp = EmulatorController.stub!!.withDeadlineAfter(10, TimeUnit.SECONDS).getStatus(Empty.getDefaultInstance())

      Assert.assertTrue(resp.getBooted())
    }
}
