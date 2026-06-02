package com.android.tools.e2etests.events

import com.android.emulator.control.EmulatorControllerGrpc
import com.android.emulator.control.VmRunState
import com.android.tools.e2etests.grpc.getHostGrpcChannel
import com.android.tools.testlib.emu.findEmulator
import com.android.tools.testlib.netsim.netsimdIsLaunched
import com.android.tradefed.config.Option
import com.android.tradefed.testtype.DeviceJUnit4ClassRunner
import com.android.tradefed.testtype.junit4.BaseHostJUnit4Test
import io.grpc.Grpc
import io.grpc.InsecureChannelCredentials
import java.time.Clock
import java.util.concurrent.TimeUnit
import org.junit.Assert
import org.junit.Assume
import org.junit.Test
import org.junit.runner.RunWith
import oshi.SystemInfo

@RunWith(DeviceJUnit4ClassRunner::class)
public class CloseEmulatorTest : BaseHostJUnit4Test() {
  // NOTE: The emulator process will exit during this test, so tradefed cannot connect to it via
  // adb or an error
  @Option(name = "emu_serial", description = "Emulator serial number. If empty test is skipped")
  private var mEmuSerial: String = ""

  // wait 60 seconds to give snapshot more time to save
  private val mTimeoutMillis = 60000

  @Test
  fun closeEmulatorAndCheckProcesses() {
    Assume.assumeFalse(mEmuSerial.isEmpty())

    val pid = findEmulator(mEmuSerial)!!.pid.toInt()

    closeEmulator()
    emulatorProcessExitsAfterClose(pid)
    netsimdExitsWithEmulator()
  }

  fun closeEmulator() {
    val channel = getHostGrpcChannel(mEmuSerial)
    val stub = EmulatorControllerGrpc.newBlockingStub(channel)

    val req = VmRunState.newBuilder().setState(VmRunState.RunState.SHUTDOWN).build()
    stub!!.withDeadlineAfter(10, TimeUnit.SECONDS).setVmState(req)
  }

  fun emulatorProcessExitsAfterClose(pid: Int) {
    val timeout = Clock.systemUTC().millis() + mTimeoutMillis
    val os = SystemInfo().getOperatingSystem()
    while (Clock.systemUTC().millis() < timeout) {
      if (os.getProcess(pid) == null) {
        return
      }
    }
    Assert.fail("emulator never exited")
  }

  fun netsimdExitsWithEmulator() {
    Assume.assumeFalse(mEmuSerial.isEmpty())

    val timeout = Clock.systemUTC().millis() + mTimeoutMillis
    while (Clock.systemUTC().millis() < timeout) {
      if (!netsimdIsLaunched()) {
        return
      }
    }
    Assert.fail("netsimd never exited")
  }
}
