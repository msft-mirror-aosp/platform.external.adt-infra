package com.android.tools.e2etests.snapshot

import com.android.tools.testlib.emu.Discovery
import com.android.tools.testlib.emu.findEmulator
import com.android.tradefed.config.Option
import com.android.tradefed.log.LogUtil.CLog
import com.android.tradefed.testtype.DeviceJUnit4ClassRunner
import com.android.tradefed.testtype.junit4.BaseHostJUnit4Test
import java.io.File
import java.nio.file.Paths
import org.junit.Assert
import org.junit.Before
import org.junit.FixMethodOrder
import org.junit.Test
import org.junit.runner.RunWith
import org.junit.runners.MethodSorters

/**
 * End-to-end host tests verifying `<avd_dir>/snapshots/default_boot/version.txt` handling across
 * real emulator launches:
 * 1. [loadFromSnapshotWhenVersionMatches]: Launch emulator, save snapshot, launch emulator again ->
 *    it loads from the snapshot (preserving guest kernel `boot_id` and volatile RAM state).
 * 2. [coldBootWhenSnapshotVersionMismatches]: Launch emulator, save snapshot, switch `version.txt`
 *    back a bit (`version - 1`), launch emulator again -> it does not load from the snapshot and
 *    performs a cold boot instead (new guest kernel `boot_id` and cleared volatile RAM state).
 */
@RunWith(DeviceJUnit4ClassRunner::class)
@FixMethodOrder(MethodSorters.NAME_ASCENDING)
class SnapshotVersionTest : BaseHostJUnit4Test() {
  @Option(
    name = "snapshot_phase",
    description =
      "Phase of the snapshot sequence: cold_boot, or load_<N> after the emulator was shut down " +
        "(saving its snapshot) and relaunched.",
  )
  private var mSnapshotPhase: String = ""

  @Option(
    name = "booted_from_snapshot",
    description = "If true, indicates the ETS_SNAPSHOT pass when snapshot_relaunch_rounds is unset.",
  )
  private var mBootedFromSnapshot: Boolean = false

  @Option(
    name = "downgrade_version_in_phase",
    description =
      "Phase in which coldBootWhenSnapshotVersionMismatches switches version.txt back by 1 " +
        "before shutdown so the next launch performs a cold boot (default: load_1 for the " +
        "2-round combined sequence, or cold_boot for a 1-round standalone run).",
  )
  private var mDowngradeVersionInPhase: String = LOAD_1

  private lateinit var discovery: Discovery
  private lateinit var avdDir: File
  private lateinit var versionFile: File

  private val phase: String
    get() =
      when {
        mSnapshotPhase.isNotEmpty() -> mSnapshotPhase
        mBootedFromSnapshot -> LOAD_1
        else -> COLD_BOOT
      }

  @Before
  fun setUp() {
    val found = findEmulator(device.serialNumber)
    Assert.assertNotNull(
      "Could not find discovery file for emulator serial ${device.serialNumber}",
      found,
    )
    discovery = found!!
    val avdDirPath = discovery.discoveryIni["avd.dir"]
    Assert.assertTrue("avd.dir is missing in discovery file", !avdDirPath.isNullOrEmpty())
    avdDir = File(avdDirPath!!)
    versionFile = Paths.get(avdDirPath, "snapshots", DEFAULT_BOOT_SNAPSHOT, "version.txt").toFile()
  }

  /**
   * Test 1: Launch emulator, save snapshot, launch it again -> it should load from snapshot.
   * - In `cold_boot`: records the guest kernel `boot_id` and sets a volatile RAM-only system
   *   property (`debug.ets.snapshot.match_boot_id`), verifying `version.txt` was written with a
   *   valid combined version (`(kGfxstreamSnapshotVersion << 16) | kSnapshotVersionBase`).
   *   Then `CloseEmulatorTest` shuts down the emulator via gRPC, saving `default_boot`.
   * - In `load_1`: verifies that the relaunched emulator loaded from the snapshot (guest kernel
   *   `boot_id` and volatile RAM property are identical to `cold_boot`).
   */
  @Test
  fun loadFromSnapshotWhenVersionMatches() {
    CLog.i("%s: [loadFromSnapshotWhenVersionMatches] phase=%s", TAG, phase)
    val matchBootIdFile = File(avdDir, MATCH_BOOT_ID_FILE)
    val matchVerifiedFile = File(avdDir, MATCH_VERIFIED_FILE)

    when (phase) {
      COLD_BOOT -> {
        val version = readSnapshotVersion()
        assertValidCombinedSnapshotVersion(version)

        val currentBootId = bootId()
        Assert.assertTrue("Guest boot_id must not be empty", currentBootId.isNotEmpty())
        matchBootIdFile.writeText(currentBootId)

        setProp(MATCH_RAM_PROP, currentBootId)
        Assert.assertEquals(
          "Volatile RAM property $MATCH_RAM_PROP was not set on guest",
          currentBootId,
          getProp(MATCH_RAM_PROP),
        )
        CLog.i(
          "%s: [cold_boot] Recorded boot_id=%s and verified version.txt=%d",
          TAG,
          currentBootId,
          version,
        )
      }
      LOAD_1 -> {
        Assert.assertTrue(
          "Expected saved boot_id file ${matchBootIdFile.absolutePath} from $COLD_BOOT",
          matchBootIdFile.exists(),
        )
        val expectedBootId = matchBootIdFile.readText().trim()
        val currentBootId = bootId()
        val ramPropValue = getProp(MATCH_RAM_PROP)

        CLog.i(
          "%s: [load_1] Checking snapshot boot: expected_boot_id=%s current_boot_id=%s ram_prop=%s",
          TAG,
          expectedBootId,
          currentBootId,
          ramPropValue,
        )
        Assert.assertEquals(
          "Emulator cold booted instead of loading from snapshot when version.txt matched",
          expectedBootId,
          currentBootId,
        )
        Assert.assertEquals(
          "Volatile RAM property $MATCH_RAM_PROP was lost; emulator did not restore RAM from snapshot",
          expectedBootId,
          ramPropValue,
        )
        matchVerifiedFile.writeText(currentBootId)
      }
      else -> {
        // In load_2 (which tests cold boot on version mismatch), verify that load_1 already
        // confirmed loading from snapshot with a matching version.
        Assert.assertTrue(
          "Expected loadFromSnapshotWhenVersionMatches to have verified snapshot boot in $LOAD_1",
          matchVerifiedFile.exists() && matchVerifiedFile.readText().trim().isNotEmpty(),
        )
      }
    }
  }

  /**
   * Test 2: Launch emulator, save snapshot, switch `version.txt` back a bit, and launch again ->
   * make sure it does not launch from snapshot and does a cold boot instead.
   * - In [mDowngradeVersionInPhase] (`load_1` in the 2-round suite, or `cold_boot` in the 1-round
   *   standalone target): records the current guest `boot_id` and sets a volatile RAM-only system
   *   property (`debug.ets.snapshot.mismatch_boot_id`), then switches `version.txt` back by 1
   *   (`version - 1`). When `CloseEmulatorTest` shuts down the emulator, QEMU saves `default_boot`
   *   while `version.txt` on disk remains `version - 1`.
   * - In the next phase (`load_2` or `load_1`): `SnapshotDevice::initialize()` detects the
   *   `version.txt` mismatch, omits `-loadvm`, and cold boots. The test verifies that the guest
   *   has a brand new `boot_id`, the volatile RAM property is empty, and `version.txt` was
   *   refreshed back to the current version.
   */
  @Test
  fun coldBootWhenSnapshotVersionMismatches() {
    CLog.i(
      "%s: [coldBootWhenSnapshotVersionMismatches] phase=%s downgradeIn=%s",
      TAG,
      phase,
      mDowngradeVersionInPhase,
    )
    if (mSnapshotPhase.isEmpty()) {
      CLog.i(
        "%s: Skipping version downgrade outside --snapshot_relaunch_rounds sequence",
        TAG,
      )
      return
    }

    val verifyPhase = if (mDowngradeVersionInPhase == COLD_BOOT) LOAD_1 else LOAD_2
    val prevBootIdFile = File(avdDir, MISMATCH_PREV_BOOT_ID_FILE)
    val origVersionFile = File(avdDir, MISMATCH_ORIG_VERSION_FILE)

    when (phase) {
      mDowngradeVersionInPhase -> {
        val originalVersion = readSnapshotVersion()
        assertValidCombinedSnapshotVersion(originalVersion)
        val downgradedVersion = originalVersion - 1

        val currentBootId = bootId()
        Assert.assertTrue("Guest boot_id must not be empty", currentBootId.isNotEmpty())
        prevBootIdFile.writeText(currentBootId)
        origVersionFile.writeText(originalVersion.toString())

        setProp(MISMATCH_RAM_PROP, currentBootId)
        Assert.assertEquals(
          "Volatile RAM property $MISMATCH_RAM_PROP was not set on guest",
          currentBootId,
          getProp(MISMATCH_RAM_PROP),
        )

        versionFile.writeText(downgradedVersion.toString())
        Assert.assertEquals(
          "Failed to switch version.txt back by 1",
          downgradedVersion,
          readSnapshotVersion(),
        )
        CLog.i(
          "%s: [%s] Switched %s from %d back to %d (boot_id=%s) before snapshot save",
          TAG,
          phase,
          versionFile.absolutePath,
          originalVersion,
          downgradedVersion,
          currentBootId,
        )
      }
      verifyPhase -> {
        Assert.assertTrue(
          "Expected saved boot_id file ${prevBootIdFile.absolutePath} from $mDowngradeVersionInPhase",
          prevBootIdFile.exists(),
        )
        Assert.assertTrue(
          "Expected saved original version file ${origVersionFile.absolutePath} from $mDowngradeVersionInPhase",
          origVersionFile.exists(),
        )
        val previousBootId = prevBootIdFile.readText().trim()
        val originalVersion = origVersionFile.readText().trim().toInt()
        val currentBootId = bootId()
        val ramPropValue = getProp(MISMATCH_RAM_PROP)
        val currentVersionOnDisk = readSnapshotVersion()

        CLog.i(
          "%s: [%s] Checking cold boot after version mismatch: prev_boot_id=%s current_boot_id=%s ram_prop='%s' version.txt=%d",
          TAG,
          phase,
          previousBootId,
          currentBootId,
          ramPropValue,
          currentVersionOnDisk,
        )
        Assert.assertNotEquals(
          "Emulator loaded from snapshot despite version.txt mismatch (boot_id did not change); expected a cold boot",
          previousBootId,
          currentBootId,
        )
        Assert.assertEquals(
          "Volatile RAM property $MISMATCH_RAM_PROP survived relaunch; expected cold boot to clear RAM state",
          "",
          ramPropValue,
        )
        Assert.assertEquals(
          "Expected SnapshotDevice::initialize() to write current kSnapshotVersion back to version.txt on cold boot",
          originalVersion,
          currentVersionOnDisk,
        )
      }
      else -> {
        // In cold_boot when downgrade_version_in_phase == load_1: just verify version.txt exists.
        val version = readSnapshotVersion()
        assertValidCombinedSnapshotVersion(version)
      }
    }
  }

  private fun bootId(): String =
    (device.executeShellCommand("cat /proc/sys/kernel/random/boot_id") ?: "").trim()

  private fun getProp(prop: String): String =
    (device.executeShellCommand("getprop $prop") ?: "").trim()

  private fun setProp(prop: String, value: String) {
    device.executeShellCommand("setprop $prop $value")
  }

  private fun readSnapshotVersion(): Int {
    Assert.assertTrue(
      "Expected snapshot version file at ${versionFile.absolutePath}",
      versionFile.exists(),
    )
    val raw = versionFile.readText().trim()
    val parsed = raw.toIntOrNull()
    Assert.assertNotNull("version.txt did not contain a valid integer: '$raw'", parsed)
    return parsed!!
  }

  private fun assertValidCombinedSnapshotVersion(version: Int) {
    val gfxstreamVersion = version ushr 16
    val baseVersion = version and 0xFFFF
    Assert.assertTrue(
      "Expected gfxstream snapshot version in bits [30..16] to be > 0, got $gfxstreamVersion (version=$version)",
      gfxstreamVersion > 0,
    )
    Assert.assertTrue(
      "Expected base snapshot version in bits [15..0] to be >= 2, got $baseVersion (version=$version)",
      baseVersion >= 2,
    )
  }

  companion object {
    private const val TAG = "SnapshotVersionTest"
    private const val DEFAULT_BOOT_SNAPSHOT = "default_boot"
    private const val COLD_BOOT = "cold_boot"
    private const val LOAD_1 = "load_1"
    private const val LOAD_2 = "load_2"

    private const val MATCH_BOOT_ID_FILE = "ets_snapshot_match_boot_id.txt"
    private const val MATCH_VERIFIED_FILE = "ets_snapshot_match_verified.txt"
    private const val MISMATCH_PREV_BOOT_ID_FILE = "ets_snapshot_mismatch_prev_boot_id.txt"
    private const val MISMATCH_ORIG_VERSION_FILE = "ets_snapshot_mismatch_orig_version.txt"

    private const val MATCH_RAM_PROP = "debug.ets.snapshot.match_boot_id"
    private const val MISMATCH_RAM_PROP = "debug.ets.snapshot.mismatch_boot_id"
  }
}
