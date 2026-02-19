package com.android.tools.e2etests.netsim

import com.android.tools.testlib.netsim.NetsimController
import com.android.tradefed.log.LogUtil.CLog
import com.android.tradefed.testtype.DeviceJUnit4ClassRunner
import com.android.tradefed.testtype.junit4.BaseHostJUnit4Test
import com.google.protobuf.Empty
import java.util.concurrent.TimeUnit
import org.junit.Assert
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(DeviceJUnit4ClassRunner::class)
class NetsimSingleDeviceTest : BaseHostJUnit4Test() {

    @Test
    fun deviceAttachesToNetsimd() {
      val resp = NetsimController.stub!!.withDeadlineAfter(10, TimeUnit.SECONDS).listDevice(Empty.getDefaultInstance())

      Assert.assertTrue(resp.getDevicesCount() > 0)
    }
}
