package com.android.tools.e2etests.netsim

import com.android.tradefed.testtype.DeviceJUnit4ClassRunner
import com.android.tradefed.testtype.junit4.BaseHostJUnit4Test
import java.nio.file.Paths
import org.junit.Assert
import org.junit.Test
import org.junit.runner.RunWith
import oshi.SystemInfo

@RunWith(DeviceJUnit4ClassRunner::class)
class NetsimDaemonTest : BaseHostJUnit4Test() {

  @Test
  fun netsimdIsLaunchedWithEmulator() {
    Assert.assertTrue(netsimdIsLaunched())
  }
}

fun netsimdIsLaunched(): Boolean {
  var netsimdName = "netsimd"
  if (System.getProperty("os.name").contains("Windows", ignoreCase = true)) {
    netsimdName += ".exe"
  }
  val os = SystemInfo().getOperatingSystem()

  for (proc in os.getProcesses()) {
    val args = proc.getArguments()
    if (!args.isEmpty() && Paths.get(args.get(0)).getFileName().toString() == netsimdName) {
      return true
    }
  }
  return false
}
