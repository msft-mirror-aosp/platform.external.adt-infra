package com.android.tools.e2etests.events

import com.android.emulator.control.EmulatorControllerGrpc
import com.android.emulator.control.VmRunState
import com.android.emulator.v2.HypervisorServiceGrpc
import com.android.emulator.v2.SnapshotOperationMetadata
import com.android.emulator.v2.StopVmRequest
import com.android.emulator.v2.StreamVmStateRequest
import com.android.emulator.v2.VmState
import com.android.tools.e2etests.grpc.getHostGrpcChannel
import com.android.tools.testlib.emu.Discovery
import com.android.tools.testlib.emu.eventually
import com.android.tools.testlib.emu.findEmulator
import com.android.tools.testlib.netsim.netsimdIsLaunched
import com.android.tradefed.config.Option
import com.android.tradefed.log.Log
import com.android.tradefed.testtype.DeviceJUnit4ClassRunner
import com.android.tradefed.testtype.junit4.BaseHostJUnit4Test
import io.grpc.ManagedChannel
import io.grpc.StatusRuntimeException
import io.grpc.stub.StreamObserver
import java.util.concurrent.LinkedBlockingQueue
import java.util.concurrent.TimeUnit
import org.junit.After
import org.junit.Assert
import org.junit.Assume
import org.junit.Test
import org.junit.runner.RunWith
import oshi.SystemInfo
import oshi.software.os.OSProcess
import oshi.software.os.OperatingSystem

@RunWith(DeviceJUnit4ClassRunner::class)
public class CloseEmulatorTest : BaseHostJUnit4Test() {
  // NOTE: The emulator process will exit during this test, so tradefed cannot connect to it via
  // adb or an error
  @Option(name = "emu_serial", description = "Emulator serial number. If empty test is skipped")
  private var mEmuSerial: String = ""

  // Wait up to 60 seconds (120 attempts x 500ms delay) for netsimd exit and fallback poll
  private val mPollCount = 120
  private val mPollDelayMs = 500L

  private var mActiveStream: VmStateStreamMonitor? = null

  @After
  fun tearDown() {
    mActiveStream?.close()
    mActiveStream = null
  }

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
    if (mEmuSerial.isEmpty()) return

    val channel = getHostGrpcChannel(mEmuSerial)
    // Start streaming VmState transitions before sending the shutdown request so snapshot progress
    // events are captured from the very beginning.
    val monitor = VmStateStreamMonitor(channel)
    monitor.start()
    mActiveStream = monitor

    val hypervisorStub = HypervisorServiceGrpc.newBlockingStub(channel)
    val stopReq = StopVmRequest.newBuilder().setSaveQuickbootSnapshot(true).build()
    try {
      hypervisorStub.withDeadlineAfter(10, TimeUnit.SECONDS).stopVm(stopReq)
      Log.i(TAG, "Successfully initiated StopVm via HypervisorService v2.")
    } catch (e: StatusRuntimeException) {
      Log.w(
        TAG,
        "HypervisorService.stopVm failed (${e.status.code}); falling back to EmulatorController.setVmState: ${e.message}",
      )
      try {
        val legacyStub = EmulatorControllerGrpc.newBlockingStub(channel)
        val legacyReq = VmRunState.newBuilder().setState(VmRunState.RunState.SHUTDOWN).build()
        legacyStub.withDeadlineAfter(10, TimeUnit.SECONDS).setVmState(legacyReq)
        Log.i(TAG, "Successfully initiated shutdown via EmulatorController legacy stub.")
      } catch (e2: StatusRuntimeException) {
        // Ignore the exception, as the emulator process may have already begun exiting.
        Log.w(TAG, "Ignoring exception as the emulator process may have exited: ${e2.message}")
      }
    }
  }

  fun emulatorProcessExitsAfterClose(pid: Int) {
    val stream = mActiveStream
    if (stream != null) {
      stream.awaitProcessExit(pid)
    } else {
      // Fallback if closeEmulator was not called or monitor was not initialized
      val os = SystemInfo().getOperatingSystem()
      val exited = eventually(count = mPollCount, delay = mPollDelayMs) {
        !isProcessAlive(os, pid)
      }
      if (!exited) {
        val failureMsg = "emulator never exited"
        if (mEmuSerial.isNotEmpty()) {
          val channel = getHostGrpcChannel(mEmuSerial)
          try {
            requestCrashReport(channel, os, pid, failureMsg)
          } finally {
            try {
              channel.shutdownNow()
              channel.awaitTermination(5, TimeUnit.SECONDS)
            } catch (ignored: Exception) {
            }
          }
        }
        Assert.fail(failureMsg)
      }
    }
  }

  companion object {
    private const val TAG = "CloseEmulatorTest"

    /**
     * Determines whether the process is actively executing.
     * On Linux, a process that has terminated enters the ZOMBIE (<defunct>) state until its parent
     * reaps it. OSHI returns a non-null OSProcess with State.ZOMBIE or State.STOPPED in that case,
     * so checking for null alone can falsely report a dead emulator as still running.
     */
    fun isProcessAlive(os: OperatingSystem, pid: Int): Boolean {
      val proc = os.getProcess(pid) ?: return false
      return proc.state != OSProcess.State.STOPPED &&
        proc.state != OSProcess.State.ZOMBIE &&
        proc.state != OSProcess.State.INVALID
    }

    /**
     * Requests the emulator to generate a crash report via HypervisorService.StopVm(CRASH) and
     * waits briefly for the process to terminate after writing the minidump.
     */
    fun requestCrashReport(
      channel: ManagedChannel,
      os: OperatingSystem,
      pid: Int,
      reason: String,
    ) {
      Log.e(
        TAG,
        "Emulator process $pid failed to exit normally. Requesting crash report: $reason",
      )
      val crashReq =
        StopVmRequest.newBuilder()
          .setMode(StopVmRequest.Mode.CRASH)
          .setReason(reason)
          .build()
      try {
        val hypervisorStub = HypervisorServiceGrpc.newBlockingStub(channel)
        hypervisorStub.withDeadlineAfter(10, TimeUnit.SECONDS).stopVm(crashReq)
      } catch (e: StatusRuntimeException) {
        // Expected: CRASH immediately aborts the emulator process, closing the gRPC transport.
        Log.i(
          TAG,
          "Crash report request completed with expected gRPC status (${e.status.code}): ${e.message}",
        )
      } catch (e: Exception) {
        Log.w(TAG, "Failed to request crash report from emulator: ${e.message}")
      }

      val exitedAfterCrash = eventually(count = 20, delay = 500L) {
        !isProcessAlive(os, pid)
      }
      if (exitedAfterCrash) {
        Log.i(TAG, "Emulator process $pid terminated after crash report generation.")
      } else {
        Log.w(TAG, "Emulator process $pid is still alive after crash report request.")
      }
    }
  }

  fun netsimdExitsWithEmulator(discovery: Discovery? = null) {
    Assume.assumeFalse(mEmuSerial.isEmpty())

    val endpoint = discovery?.discoveryIni?.get("netsim.endpoint")
    val port = endpoint?.substringAfterLast(":")?.takeIf { it.all { c -> c.isDigit() } }

    val exited = eventually(count = mPollCount, delay = mPollDelayMs) {
      !netsimdIsLaunched(port)
    }
    Assert.assertTrue("netsimd never exited", exited)
  }

  internal sealed class VmStateUpdate {
    data class Next(val state: VmState) : VmStateUpdate()

    data class Error(val error: Throwable) : VmStateUpdate()

    object Completed : VmStateUpdate()
  }

  internal class VmStateStreamMonitor(private val channel: ManagedChannel) : AutoCloseable {
    private val queue = LinkedBlockingQueue<VmStateUpdate>()
    private val TAG = "VmStateStreamMonitor"

    fun start() {
      val stub = HypervisorServiceGrpc.newStub(channel)
      stub.streamVmState(
        StreamVmStateRequest.getDefaultInstance(),
        object : StreamObserver<VmState> {
          override fun onNext(value: VmState) {
            queue.offer(VmStateUpdate.Next(value))
          }

          override fun onError(t: Throwable) {
            queue.offer(VmStateUpdate.Error(t))
          }

          override fun onCompleted() {
            queue.offer(VmStateUpdate.Completed)
          }
        },
      )
    }

    fun awaitProcessExit(pid: Int) {
      val os = SystemInfo().getOperatingSystem()
      var lastActivityTimeMs = System.currentTimeMillis()
      var isSavingSnapshot = false
      var lastProgressEventTimeMs = 0L
      var lastProgress: SnapshotOperationMetadata? = null
      var isStreamClosed = false

      val initialGracePeriodMs = 60000L
      // Fail if no snapshot progress event is received within this duration.
      // Under high CI disk I/O contention (especially during large 8+ GB RAM transfers on
      // memory-constrained macOS builders where APFS writeback can stall for tens of seconds),
      // a 60-second watchdog avoids spurious failures while still detecting deadlocks quickly.
      val progressTimeoutMs = 60000L

      fun verifyStreamClosed() {
        if (isStreamClosed) {
          Log.i(TAG, "Emulator process $pid exited and gRPC stream had already closed.")
          return
        }
        Log.i(TAG, "Emulator process $pid has exited. Awaiting gRPC stream closure...")
        val closed = eventually(count = 20, delay = 500L) {
          if (isStreamClosed) return@eventually true
          val next = queue.poll(200, TimeUnit.MILLISECONDS)
          if (next is VmStateUpdate.Error || next is VmStateUpdate.Completed) {
            isStreamClosed = true
            return@eventually true
          }
          false
        }
        Assert.assertTrue(
          "gRPC StreamVmState did not close after emulator process $pid disappeared",
          closed,
        )
        Log.i(TAG, "gRPC stream successfully closed after emulator process $pid exited.")
      }

      try {
        while (true) {
          // 1. Check if the emulator process has already exited.
          if (!isProcessAlive(os, pid)) {
            Log.i(TAG, "Emulator process $pid has exited successfully.")
            verifyStreamClosed()
            return
          }

          // 2. Poll for new VmState events from the stream.
          val update = queue.poll(100, TimeUnit.MILLISECONDS)
          if (update != null) {
            when (update) {
              is VmStateUpdate.Next -> {
                val state = update.state
                Log.d(TAG, "Received VmState: ${state.state}, hasSnapshotProgress=${state.hasSnapshotProgress()}")
                if (state.hasSnapshotProgress()) {
                  val progress = state.snapshotProgress
                  isSavingSnapshot = when (progress.phase) {
                    SnapshotOperationMetadata.Phase.PREPARING,
                    SnapshotOperationMetadata.Phase.TRANSFERRING -> true
                    else -> false
                  }
                  lastProgressEventTimeMs = System.currentTimeMillis()
                  lastActivityTimeMs = lastProgressEventTimeMs
                  lastProgress = progress
                  Log.i(
                    TAG,
                    "Snapshot progress: phase=${progress.phase}, percent=${progress.progressPercent}%, " +
                      "transferred=${progress.transferredBytes}/${progress.totalBytes} bytes, " +
                      "component='${progress.activeComponent}', " +
                      "devices=${progress.completedDevices}/${progress.totalDevices}",
                  )
                } else {
                  isSavingSnapshot = (state.state == VmState.State.SAVING_SNAPSHOT)
                  lastActivityTimeMs = System.currentTimeMillis()
                  if (isSavingSnapshot) {
                    lastProgressEventTimeMs = lastActivityTimeMs
                  }
                }
              }
              is VmStateUpdate.Error -> {
                Log.d(TAG, "StreamVmState closed with: ${update.error.message}")
                isSavingSnapshot = false
                isStreamClosed = true
                lastActivityTimeMs = System.currentTimeMillis()
              }
              is VmStateUpdate.Completed -> {
                Log.d(TAG, "StreamVmState completed.")
                isSavingSnapshot = false
                isStreamClosed = true
                lastActivityTimeMs = System.currentTimeMillis()
              }
            }
          }

          // 3. Re-check process exit right after processing the event.
          if (!isProcessAlive(os, pid)) {
            Log.i(TAG, "Emulator process $pid has exited successfully.")
            verifyStreamClosed()
            return
          }

          // 4. Progress and timeout watchdog.
          val currentTime = System.currentTimeMillis()
          if (isSavingSnapshot) {
            val timeSinceLastProgress = currentTime - lastProgressEventTimeMs
            if (timeSinceLastProgress > progressTimeoutMs) {
              // Final check if process exited right at the boundary.
              if (!isProcessAlive(os, pid)) {
                Log.i(TAG, "Emulator process $pid exited right as progress timeout elapsed.")
                verifyStreamClosed()
                return
              }
              val failureMsg =
                "Emulator snapshot save stalled: no snapshot progress event received for ${timeSinceLastProgress}ms " +
                  "(exceeded ${progressTimeoutMs}ms limit). Emulator is likely stuck. " +
                  "Last recorded progress: phase=${lastProgress?.phase}, percent=${lastProgress?.progressPercent}%, " +
                  "transferred=${lastProgress?.transferredBytes}/${lastProgress?.totalBytes} bytes, " +
                  "activeComponent='${lastProgress?.activeComponent}'"
              requestCrashReport(channel, os, pid, failureMsg)
              Assert.fail(failureMsg)
            }
            // As long as progress events arrive within progressTimeoutMs (60s), keep waiting indefinitely!
          } else {
            // Not actively saving a snapshot: wait up to initialGracePeriodMs of inactivity.
            val timeSinceActivity = currentTime - lastActivityTimeMs
            if (timeSinceActivity > initialGracePeriodMs) {
              if (!isProcessAlive(os, pid)) {
                Log.i(TAG, "Emulator process $pid exited right as inactivity timeout elapsed.")
                verifyStreamClosed()
                return
              }
              val failureMsg =
                "Emulator process $pid did not exit within ${initialGracePeriodMs}ms of inactivity."
              requestCrashReport(channel, os, pid, failureMsg)
              Assert.fail(failureMsg)
            }
          }
        }
      } finally {
        close()
      }
    }

    override fun close() {
      try {
        channel.shutdownNow()
        channel.awaitTermination(5, TimeUnit.SECONDS)
      } catch (ignored: Exception) {
      }
    }
  }
}
