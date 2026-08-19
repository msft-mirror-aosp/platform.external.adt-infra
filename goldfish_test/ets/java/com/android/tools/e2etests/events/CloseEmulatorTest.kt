package com.android.tools.e2etests.events

import com.android.emulator.control.EmulatorControllerGrpc
import com.android.emulator.control.VmRunState
import com.android.tools.e2etests.grpc.getHostGrpcChannel
import com.android.tools.testlib.emu.eventually
import com.android.tools.testlib.emu.findEmulator
import com.android.tools.testlib.netsim.netsimdIsLaunched
import com.android.tradefed.config.Option
import com.android.tradefed.log.Log
import com.android.tradefed.testtype.DeviceJUnit4ClassRunner
import com.android.tradefed.testtype.junit4.BaseHostJUnit4Test
import io.grpc.StatusRuntimeException
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

  // Wait up to 60 seconds (120 attempts x 500ms delay) to give snapshot more time to save
  private val mPollCount = 120
  private val mPollDelayMs = 500L

  private val TAG = "CloseEmulatorTest"

  @Test
  fun closeEmulatorAndCheckProcesses() {
    Assume.assumeFalse(mEmuSerial.isEmpty())

    val discovery = findEmulator(mEmuSerial)
    Assert.assertNotNull("Could not find discovery file for emulator serial $mEmuSerial", discovery)
    val pid = discovery!!.pid.toInt()

    closeEmulator()
    emulatorProcessExitsAfterClose(pid)
    netsimdExitsWithEmulator(discovery)
  }

  fun closeEmulator() {
    val channel = getHostGrpcChannel(mEmuSerial)
    val stub = EmulatorControllerGrpc.newBlockingStub(channel)

    val req = VmRunState.newBuilder().setState(VmRunState.RunState.SHUTDOWN).build()
    try {
      stub!!.withDeadlineAfter(10, TimeUnit.SECONDS).setVmState(req)
    } catch (e: StatusRuntimeException) {
      // Ignore the exception, as the emulator process is expected to exit.
      Log.w(TAG, "Ignoring exception as the emulator process may have exited.")
    }
  }

  fun emulatorProcessExitsAfterClose(pid: Int) {
    val os = SystemInfo().getOperatingSystem()
    val exited = eventually(count = mPollCount, delay = mPollDelayMs) {
      os.getProcess(pid) == null
    }
    Assert.assertTrue("emulator never exited", exited)
  }

  fun netsimdExitsWithEmulator(discovery: com.android.tools.testlib.emu.Discovery? = null) {
    Assume.assumeFalse(mEmuSerial.isEmpty())

    val endpoint = discovery?.discoveryIni?.get("netsim.endpoint")
    val port = endpoint?.substringAfterLast(":")?.takeIf { it.all { c -> c.isDigit() } }

    val exited = eventually(count = mPollCount, delay = mPollDelayMs) {
      !netsimdIsLaunched(port)
    }
    Assert.assertTrue("netsimd never exited", exited)
  }
}
