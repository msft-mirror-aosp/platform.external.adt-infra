package com.android.tools.e2etests.snapshot

import com.android.emulator.control.SnapshotDetails
import com.android.emulator.control.SnapshotFilter
import com.android.emulator.control.SnapshotServiceGrpc
import com.android.tools.e2etests.grpc.getHostGrpcChannel
import com.android.tools.testlib.emu.Discovery
import com.android.tools.testlib.emu.findEmulator
import com.android.tradefed.config.Option
import com.android.tradefed.log.Log
import com.android.tradefed.testtype.DeviceJUnit4ClassRunner
import com.android.tradefed.testtype.junit4.BaseHostJUnit4Test
import java.io.File
import java.nio.file.Paths
import java.util.concurrent.TimeUnit
import org.junit.Assert
import org.junit.Assume
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

val TAG = "SnapshotTest"

@RunWith(DeviceJUnit4ClassRunner::class)
class SnapshotTest : BaseHostJUnit4Test() {
  @Option(
    name = "booted_from_snapshot",
    description = "If true, make assertions that the emulator was booted from a snapshot.",
  )
  private var mBootedFromSnapshot: Boolean = false

  lateinit var snapshotService: SnapshotServiceGrpc.SnapshotServiceBlockingStub
  lateinit var discovery: Discovery

  @Before
  fun setUp() {
    discovery = findEmulator(device.getSerialNumber())!!
    snapshotService =
      SnapshotServiceGrpc.newBlockingStub(getHostGrpcChannel(discovery))
        .withDeadlineAfter(10, TimeUnit.SECONDS)
  }

  @Test
  fun snapshotWasLoaded() {
    val req =
      SnapshotFilter.newBuilder().setStatusFilter(SnapshotFilter.LoadStatus.CompatibleOnly).build()
    val response = snapshotService.listSnapshots(req)
    Log.i(TAG, "Snapshot list: $response")

    var bootedFromSnapshot = false
    for (snapshot in response.getSnapshotsList()) {
      if (snapshot.status == SnapshotDetails.LoadStatus.Loaded) {
        bootedFromSnapshot = true
        break
      }
    }
    // Querying the RPC service is useful even if it didn't boot from a
    // snapshot, so do so, just don't assert.
    if (mBootedFromSnapshot) {
      Assert.assertEquals(mBootedFromSnapshot, bootedFromSnapshot)
    } else {
      Log.i(TAG, "Not asserting the emulator booted from a snapshot.")
    }
  }

  @Test
  fun snapshotTraceFileSet() {
    // The file won't exist if the emulator wasn't booted from a snapshot.
    Assume.assumeTrue(mBootedFromSnapshot)
    val avdDir = discovery.discoveryIni["avd.dir"]
    val contents = File(Paths.get(avdDir, "snapshot.trace").toString()).readText()
    Assert.assertTrue(contents.contains("load_succeeded"))
  }
}
