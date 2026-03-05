package com.android.tools.e2etests.events

import com.android.tools.testlib.netsim.netsimdIsLaunched
import com.android.emulator.control.VmRunState
import com.android.emulator.control.EmulatorControllerGrpc
import com.android.tradefed.config.Option
import com.android.tradefed.testtype.DeviceJUnit4ClassRunner
import com.android.tradefed.testtype.junit4.BaseHostJUnit4Test
import io.grpc.Grpc
import io.grpc.InsecureChannelCredentials
import java.lang.Thread
import java.time.Clock
import org.junit.Assert
import org.junit.Assume
import org.junit.Test
import org.junit.runner.RunWith
import java.util.concurrent.TimeUnit
import org.junit.runner.OrderWith
import org.junit.runner.manipulation.Alphanumeric
import java.nio.file.Paths
import oshi.SystemInfo

@OrderWith(Alphanumeric::class)
@RunWith(DeviceJUnit4ClassRunner::class)
public class CloseEmulatorTest : BaseHostJUnit4Test() {
  @Option(name = "grpc_port", description = "Port to use for grpc calls. If empty test is skipped")
  private var mGrpcPort: String = ""

  @Option(name = "emu_pid", description = "Emulator process id. If empty test is skipped")
  private var mEmuPid: String = ""

  private val mTimeoutMillis = 20000

  // Tests are ordered alphanumerically, hence the a, b, c prefix.
  @Test
  fun aCloseEmulator() {
    Assume.assumeFalse(mGrpcPort.isEmpty())
    Assume.assumeFalse(mEmuPid.isEmpty())

    val channel =
      Grpc.newChannelBuilder("localhost:" + mGrpcPort, InsecureChannelCredentials.create()).build()
    val stub = EmulatorControllerGrpc.newBlockingStub(channel)

    val req = VmRunState.newBuilder().setState(VmRunState.RunState.SHUTDOWN).build()
    stub!!.withDeadlineAfter(10, TimeUnit.SECONDS).setVmState(req)
  }

  @Test
  fun bEmulatorProcessExitsAfterClose() {
    Assume.assumeFalse(mGrpcPort.isEmpty())
    Assume.assumeFalse(mEmuPid.isEmpty())

    val timeout = Clock.systemUTC().millis() + mTimeoutMillis 
    val os = SystemInfo().getOperatingSystem()
    val pid = Integer.parseInt(mEmuPid)
    while (Clock.systemUTC().millis() < timeout) {
        if (os.getProcess(mEmuPid.toInt()) == null) {
            return
        }
    }
    Assert.fail("emulator never exited")
  }

  @Test
  fun cNetsimdExitsWithEmulator() {
    Assume.assumeFalse(mGrpcPort.isEmpty())
    Assume.assumeFalse(mEmuPid.isEmpty())

    val timeout = Clock.systemUTC().millis() + mTimeoutMillis
    while (Clock.systemUTC().millis() < timeout) {
        if (!netsimdIsLaunched()) {
            return
        }
    }
    Assert.fail("netsimd never exited")
  }
}

