package com.android.tools.e2etests.netsim

import com.android.tools.testlib.netsim.netsimdIsLaunched
import com.android.tradefed.testtype.DeviceJUnit4ClassRunner
import com.android.tradefed.testtype.junit4.BaseHostJUnit4Test
import org.junit.Assert
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(DeviceJUnit4ClassRunner::class)
class NetsimDaemonTest : BaseHostJUnit4Test() {

  @Test
  fun netsimdIsLaunchedWithEmulator() {
    Assert.assertTrue(netsimdIsLaunched())
  }
}
