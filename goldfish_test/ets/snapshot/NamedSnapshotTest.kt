package com.android.tools.e2etests.snapshot

import com.android.emulator.v2.CreateSnapshotRequest
import com.android.emulator.v2.DeleteSnapshotRequest
import com.android.emulator.v2.GetVmStateRequest
import com.android.emulator.v2.HypervisorServiceGrpc
import com.android.emulator.v2.ListSnapshotsRequest
import com.android.emulator.v2.RestoreSnapshotRequest
import com.android.emulator.v2.Snapshot
import com.android.emulator.v2.VmState
import com.android.tools.e2etests.grpc.getHostGrpcChannel
import com.android.tools.testlib.emu.Discovery
import com.android.tools.testlib.emu.findEmulator
import com.android.tradefed.config.Option
import com.android.tradefed.log.LogUtil.CLog
import com.android.tradefed.testtype.DeviceJUnit4ClassRunner
import com.android.tradefed.testtype.junit4.BaseHostJUnit4Test
import com.google.longrunning.Operation
import io.grpc.ManagedChannel
import io.grpc.Status
import io.grpc.StatusRuntimeException
import java.io.File
import java.util.concurrent.TimeUnit
import org.junit.After
import org.junit.Assert
import org.junit.Assume
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

/**
 * End-to-end host tests for snapshots saved under a name other than `default_boot` at runtime
 * through `HypervisorService` v2 (b/574891578). Every snapshot owns `<avd>/snapshots/<name>/`
 * with its `version.txt` and the renderer state under `renderer/`, next to the qcow2 internal
 * snapshot tagged `<name>`.
 *
 * The round-trip tests run in any phase. [namedSnapshotSurvivesRelaunch] spans the snapshot
 * relaunch sequence: in `cold_boot` it creates [RELAUNCH_SNAPSHOT] over gRPC and leaves it behind
 * (the emulator is then shut down, which saves `default_boot` as usual); in `load_1` the sequence
 * relaunched the emulator with `-snapshot ets_named` (`--relaunch_emulator_args`) and the test
 * checks that the guest is the one captured by `CreateSnapshot`, not by the later shutdown.
 *
 * Whether the emulator accepts snapshots is probed from the emulator itself (see
 * [snapshotsDisabled]); when it was started with `-no-snapshot` only
 * [saveAndLoadAreRejectedWhenSnapshotsAreDisabled] applies. The test only talks to the emulator
 * over gRPC and adb and touches the AVD directory through `java.io.File`, so it runs unchanged on
 * Linux, macOS and Windows hosts (including against an external emulator).
 */
@RunWith(DeviceJUnit4ClassRunner::class)
class NamedSnapshotTest : BaseHostJUnit4Test() {
  @Option(
    name = "snapshot_phase",
    description =
      "Phase of the snapshot sequence: cold_boot, or load_<N> after the emulator was relaunched.",
  )
  private var mSnapshotPhase: String = ""

  @Option(
    name = "snapshots_disabled",
    description =
      "Set by plans that launch the emulator with -no-snapshot, to assert that the emulator " +
        "really rejects snapshots. Whether snapshots are disabled is otherwise detected from the " +
        "emulator itself, so the module also runs against external emulators on any host OS.",
  )
  private var mSnapshotsDisabled: Boolean = false

  private lateinit var discovery: Discovery
  private lateinit var avdDir: File
  private lateinit var channel: ManagedChannel
  private lateinit var hypervisor: HypervisorServiceGrpc.HypervisorServiceBlockingStub

  private val phase: String
    get() = mSnapshotPhase.ifEmpty { COLD_BOOT }

  /**
   * Whether this emulator rejects snapshot operations (started with -no-snapshot, or a legacy
   * system image the sequence boots that way). Probed once per run with a throw-away snapshot.
   */
  private fun snapshotsDisabled(): Boolean {
    probedSnapshotsDisabled?.let {
      return it
    }
    val op = create(PROBE_SNAPSHOT)
    val disabled =
      op.hasError() &&
        op.error.code == Status.Code.FAILED_PRECONDITION.value() &&
        op.error.message.contains("-no-snapshot")
    if (!disabled) {
      assertDone("CreateSnapshot($PROBE_SNAPSHOT)", op)
      delete(PROBE_SNAPSHOT)
    }
    if (mSnapshotsDisabled) {
      Assert.assertTrue(
        "Plan declares snapshots_disabled but the emulator accepted CreateSnapshot",
        disabled,
      )
    }
    CLog.i("%s: snapshots %s on this emulator", TAG, if (disabled) "disabled" else "enabled")
    probedSnapshotsDisabled = disabled
    return disabled
  }

  @Before
  fun setUp() {
    val found = findEmulator(device.serialNumber)
    Assert.assertNotNull("Could not find discovery file for emulator ${device.serialNumber}", found)
    discovery = found!!
    val avdDirPath = discovery.discoveryIni["avd.dir"]
    Assert.assertNotNull("Discovery file has no avd.dir", avdDirPath)
    avdDir = File(avdDirPath!!)
    channel = getHostGrpcChannel(discovery)
    hypervisor = HypervisorServiceGrpc.newBlockingStub(channel)
  }

  @After
  fun tearDown() {
    channel.shutdownNow()
    channel.awaitTermination(5, TimeUnit.SECONDS)
  }

  // --- helpers -------------------------------------------------------------------------------

  private fun shell(cmd: String): String = (device.executeShellCommand(cmd) ?: "").trim()

  private fun bootId(): String = shell("cat /proc/sys/kernel/random/boot_id")

  private fun setMarker(value: String) {
    shell("mkdir -p $STATE_DIR && echo '$value' > $STATE_DIR/marker && sync")
    Assert.assertEquals("Guest marker was not written", value, marker())
  }

  private fun marker(): String = shell("cat $STATE_DIR/marker 2>/dev/null")

  // Host paths are built with File.resolve so they work on Linux, macOS and Windows alike.
  private fun snapshotDir(name: String): File = avdDir.resolve("snapshots").resolve(name)

  private fun versionFile(name: String): File = snapshotDir(name).resolve("version.txt")

  private fun rendererDir(name: String): File = snapshotDir(name).resolve("renderer")

  private fun rendererIds(name: String): List<String> =
    rendererDir(name).list()?.sorted() ?: emptyList()

  private fun create(name: String): Operation =
    hypervisor
      .withDeadlineAfter(SNAPSHOT_DEADLINE_SEC, TimeUnit.SECONDS)
      .createSnapshot(CreateSnapshotRequest.newBuilder().setSnapshotId(name).build())

  private fun restore(name: String): Operation =
    hypervisor
      .withDeadlineAfter(SNAPSHOT_DEADLINE_SEC, TimeUnit.SECONDS)
      .restoreSnapshot(RestoreSnapshotRequest.newBuilder().setSnapshotId(name).build())

  private fun delete(name: String) {
    hypervisor
      .withDeadlineAfter(SNAPSHOT_DEADLINE_SEC, TimeUnit.SECONDS)
      .deleteSnapshot(DeleteSnapshotRequest.newBuilder().setSnapshotId(name).build())
  }

  private fun list(compatibleOnly: Boolean = false): List<Snapshot> =
    hypervisor
      .withDeadlineAfter(30, TimeUnit.SECONDS)
      .listSnapshots(ListSnapshotsRequest.newBuilder().setCompatibleOnly(compatibleOnly).build())
      .snapshotsList

  private fun find(name: String, compatibleOnly: Boolean = false): Snapshot? =
    list(compatibleOnly).firstOrNull { it.snapshotId == name }

  private fun vmState(): VmState.State =
    hypervisor.withDeadlineAfter(30, TimeUnit.SECONDS).getVmState(GetVmStateRequest.getDefaultInstance()).state

  private fun assertDone(what: String, op: Operation) {
    Assert.assertTrue("$what: operation not done: $op", op.done)
    Assert.assertFalse("$what failed: ${op.error}", op.hasError())
  }

  private fun assertFailed(what: String, op: Operation, code: Status.Code, messagePart: String) {
    Assert.assertTrue("$what: operation not done: $op", op.done)
    Assert.assertTrue("$what: expected an error, got $op", op.hasError())
    // google.rpc.Status.code uses the canonical gRPC code numbers.
    Assert.assertEquals("$what: wrong error code: ${op.error}", code.value(), op.error.code)
    Assert.assertTrue(
      "$what: error '${op.error.message}' does not mention '$messagePart'",
      op.error.message.contains(messagePart),
    )
  }

  private fun assertSnapshotFilesPresent(name: String) {
    Assert.assertTrue("${versionFile(name)} missing", versionFile(name).isFile)
    Assert.assertTrue(
      "${rendererDir(name)} missing or empty; renderer state was not saved per snapshot",
      rendererIds(name).isNotEmpty(),
    )
  }

  private fun assertSnapshotFilesAbsent(name: String) {
    Assert.assertFalse("${snapshotDir(name)} still exists", snapshotDir(name).exists())
  }

  // --- tests ---------------------------------------------------------------------------------

  /**
   * Creates a named snapshot at runtime, checks its on-disk layout and that `default_boot` (when
   * present) kept its own renderer state, restores it, and deletes it.
   */
  @Test
  fun namedSnapshotRoundTrip() {
    Assume.assumeFalse("snapshots are disabled on this emulator", snapshotsDisabled())
    val name = "ets_roundtrip"
    val defaultBootRenderer = rendererIds(DEFAULT_BOOT)
    val bootIdBefore = bootId()
    setMarker("before_$name")

    assertDone("CreateSnapshot($name)", create(name))
    assertSnapshotFilesPresent(name)
    Assert.assertEquals(
      "Saving '$name' must not touch the renderer state of '$DEFAULT_BOOT'",
      defaultBootRenderer,
      rendererIds(DEFAULT_BOOT),
    )
    Assert.assertFalse(
      "Legacy <avd>/renderersave/ must not be written any more",
      avdDir.resolve("renderersave").resolve(name).exists(),
    )
    val listed = find(name)
    Assert.assertNotNull("'$name' missing from ListSnapshots", listed)
    Assert.assertTrue("'$name' must be host compatible", listed!!.compatibility.hostCompatible)
    Assert.assertNotNull("'$name' missing from ListSnapshots(compatible_only)", find(name, true))

    setMarker("after_$name")
    assertDone("RestoreSnapshot($name)", restore(name))
    Assert.assertEquals("Guest state was not restored from '$name'", "before_$name", marker())
    Assert.assertEquals("Restoring a runtime snapshot must not reboot", bootIdBefore, bootId())
    Assert.assertEquals(VmState.State.RUNNING, vmState())

    delete(name)
    assertSnapshotFilesAbsent(name)
    Assert.assertNull("'$name' still listed after DeleteSnapshot", find(name))
  }

  /** A snapshot whose recorded version does not match is listed as incompatible and not loaded. */
  @Test
  fun incompatibleSnapshotIsRejectedWithoutStoppingTheVm() {
    Assume.assumeFalse("snapshots are disabled on this emulator", snapshotsDisabled())
    val name = "ets_stale"
    assertDone("CreateSnapshot($name)", create(name))
    val version = versionFile(name).readText().trim().toInt()
    versionFile(name).writeText((version - 1).toString())

    val listed = find(name)
    Assert.assertNotNull("'$name' missing from ListSnapshots", listed)
    Assert.assertFalse("'$name' must be reported incompatible", listed!!.compatibility.hostCompatible)
    Assert.assertNull("'$name' must be filtered by compatible_only", find(name, true))

    val bootIdBefore = bootId()
    assertFailed(
      "RestoreSnapshot($name)",
      restore(name),
      Status.Code.FAILED_PRECONDITION,
      "incompatible",
    )
    Assert.assertEquals(VmState.State.RUNNING, vmState())
    Assert.assertEquals("VM must keep running after a rejected load", bootIdBefore, bootId())
    Assert.assertEquals("Guest must still respond after a rejected load", "ok", shell("echo ok"))

    delete(name)
    assertSnapshotFilesAbsent(name)
  }

  /** Snapshot ids are directory names: path separators and ".." are rejected up front. */
  @Test
  fun invalidSnapshotIdIsRejected() {
    for (bad in listOf("../escape", "a/b", "a\\b")) {
      try {
        create(bad)
        Assert.fail("CreateSnapshot('$bad') should have been rejected")
      } catch (e: StatusRuntimeException) {
        Assert.assertEquals("CreateSnapshot('$bad')", Status.Code.INVALID_ARGUMENT, e.status.code)
      }
    }
    Assert.assertFalse(avdDir.resolve("escape").exists())
    Assert.assertFalse(avdDir.parentFile.resolve("escape").exists())
  }

  /**
   * With -no-snapshot, save and load fail with FAILED_PRECONDITION while list keeps working. Runs
   * whenever the emulator reports snapshots disabled; plans launching with -no-snapshot set
   * `snapshots_disabled` so that an emulator that unexpectedly accepts snapshots fails instead of
   * skipping.
   */
  @Test
  fun saveAndLoadAreRejectedWhenSnapshotsAreDisabled() {
    Assume.assumeTrue("snapshots are enabled on this emulator", snapshotsDisabled())
    assertFailed("CreateSnapshot", create("ets_disabled"), Status.Code.FAILED_PRECONDITION, "-no-snapshot")
    assertSnapshotFilesAbsent("ets_disabled")
    // ListSnapshots works; RestoreSnapshot of anything listed is rejected, else NOT_FOUND.
    val any = list().firstOrNull()
    if (any != null) {
      assertFailed(
        "RestoreSnapshot(${any.snapshotId})",
        restore(any.snapshotId),
        Status.Code.FAILED_PRECONDITION,
        "-no-snapshot",
      )
    }
    Assert.assertEquals(VmState.State.RUNNING, vmState())
  }

  /**
   * `cold_boot`: creates [RELAUNCH_SNAPSHOT] and records the guest boot id; the sequence then shuts
   * the emulator down (saving `default_boot`) and relaunches it with `-snapshot ets_named`.
   * `load_1`: the guest must be the one captured by `CreateSnapshot`: same boot id, the marker
   * written before the snapshot, and not the one written after it.
   */
  @Test
  fun namedSnapshotSurvivesRelaunch() {
    Assume.assumeTrue("not in a snapshot relaunch sequence", mSnapshotPhase.isNotEmpty())
    Assume.assumeFalse("snapshots are disabled on this emulator", snapshotsDisabled())
    val bootIdFile = avdDir.resolve("$RELAUNCH_SNAPSHOT.boot_id")
    when (phase) {
      COLD_BOOT -> {
        val currentBootId = bootId()
        bootIdFile.writeText(currentBootId)
        setMarker("before_$RELAUNCH_SNAPSHOT")
        assertDone("CreateSnapshot($RELAUNCH_SNAPSHOT)", create(RELAUNCH_SNAPSHOT))
        assertSnapshotFilesPresent(RELAUNCH_SNAPSHOT)
        // Anything from here on must not be visible after the relaunch from the snapshot.
        setMarker("after_$RELAUNCH_SNAPSHOT")
        CLog.i("%s: [cold_boot] created %s at boot_id=%s", TAG, RELAUNCH_SNAPSHOT, currentBootId)
      }
      else -> {
        Assert.assertTrue("Expected ${bootIdFile.path} from $COLD_BOOT", bootIdFile.isFile)
        val expectedBootId = bootIdFile.readText().trim()
        val currentBootId = bootId()
        CLog.i(
          "%s: [%s] expected_boot_id=%s current_boot_id=%s marker=%s",
          TAG,
          phase,
          expectedBootId,
          currentBootId,
          marker(),
        )
        Assert.assertEquals(
          "Emulator did not resume from '$RELAUNCH_SNAPSHOT' (cold boot or other snapshot)",
          expectedBootId,
          currentBootId,
        )
        Assert.assertEquals(
          "Guest state is not the one captured by CreateSnapshot('$RELAUNCH_SNAPSHOT')",
          "before_$RELAUNCH_SNAPSHOT",
          marker(),
        )
        Assert.assertTrue(
          "'$RELAUNCH_SNAPSHOT' must still be compatible after the relaunch",
          find(RELAUNCH_SNAPSHOT)?.compatibility?.hostCompatible == true,
        )
      }
    }
  }

  companion object {
    private const val TAG = "NamedSnapshotTest"
    private const val COLD_BOOT = "cold_boot"
    private const val DEFAULT_BOOT = "default_boot"
    const val RELAUNCH_SNAPSHOT = "ets_named"
    private const val PROBE_SNAPSHOT = "ets_probe"
    // Guest (Android) path; independent of the host OS.
    private const val STATE_DIR = "/data/local/tmp/ets_named_snapshot"
    private const val SNAPSHOT_DEADLINE_SEC = 300L

    // JUnit creates one instance per test method; the probe result is shared across them.
    @Volatile private var probedSnapshotsDisabled: Boolean? = null
  }
}
