package com.android.tools.e2etests.avd

import com.android.emulation.control.incubating.AvdServiceGrpc
import com.android.tools.e2etests.grpc.getHostGrpcChannel
import com.android.tools.testlib.emu.Discovery
import com.android.tools.testlib.emu.findEmulator
import com.android.tradefed.testtype.DeviceJUnit4ClassRunner
import com.android.tradefed.testtype.junit4.BaseHostJUnit4Test
import com.google.protobuf.Empty
import io.grpc.ManagedChannel
import java.util.concurrent.TimeUnit
import org.junit.After
import org.junit.Assert
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(DeviceJUnit4ClassRunner::class)
public class AvdTest : BaseHostJUnit4Test() {

  lateinit var avdService: AvdServiceGrpc.AvdServiceBlockingStub
  lateinit var discovery: Discovery
  lateinit var channel: ManagedChannel
  val tracePath = "/sys/kernel/tracing/trace_marker"

  @Before
  fun setUp() {
    discovery = findEmulator(device.getSerialNumber())!!
    val port = discovery.discoveryIni["grpc.port"]
    channel = getHostGrpcChannel(discovery)
    avdService = AvdServiceGrpc.newBlockingStub(channel).withDeadlineAfter(10, TimeUnit.SECONDS)
  }

  @Test
  fun avdCanonicalPath() {
    val resp = avdService.getAvdInfo(Empty.getDefaultInstance())
    Assert.assertEquals(resp.getContentPath(), discovery.discoveryIni["avd.dir"])
  }

  @Test
  fun snapshotPathNormalized() {
    val resp = avdService.getAvdInfo(Empty.getDefaultInstance())
    Assert.assertFalse(resp.getSnapshotLockPath().contains(".."))
  }

  @Test
  fun avdTracingIsMounted() {
    val traceMarker = device.executeShellCommand("ls ${tracePath}")
    Assert.assertTrue(traceMarker.contains(tracePath))
  }

  @After
  fun tearDown() {
    channel.shutdown()
  }
}
