package com.android.tools.e2etests.snapshot

import com.android.tools.testlib.emu.Discovery
import com.android.tools.testlib.emu.findEmulator
import com.android.tradefed.log.LogUtil.CLog
import com.android.tradefed.testtype.DeviceJUnit4ClassRunner
import com.android.tradefed.testtype.junit4.BaseHostJUnit4Test
import java.io.File
import org.junit.Assert
import org.junit.Assume
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

/**
 * End-to-end host tests of the console snapshot commands as users run them through adb:
 *
 *     adb -s <serial> emu avd snapshot save|load|del|list [<name>]
 *
 * `adb emu` authenticates against the emulator console and forwards the command; the console
 * implements it with the legacy `SnapshotService` gRPC API, which shares `VmOperations` with
 * `HypervisorService` v2 (see [NamedSnapshotTest]). So this covers the console/adb surface of
 * b/574891578: snapshots saved by name from the console get their own
 * `<avd>/snapshots/<name>/` directory, load back, and are removed by `del`.
 *
 * Only the emulator-side behaviour is host specific: the test drives adb through Tradefed and
 * reads the AVD directory with `java.io.File`, so it runs on Linux, macOS and Windows hosts.
 */
@RunWith(DeviceJUnit4ClassRunner::class)
class AdbEmuSnapshotTest : BaseHostJUnit4Test() {
  private lateinit var discovery: Discovery
  private lateinit var avdDir: File

  @Before
  fun setUp() {
    val found = findEmulator(device.serialNumber)
    Assert.assertNotNull("Could not find discovery file for emulator ${device.serialNumber}", found)
    discovery = found!!
    val avdDirPath = discovery.discoveryIni["avd.dir"]
    Assert.assertNotNull("Discovery file has no avd.dir", avdDirPath)
    avdDir = File(avdDirPath!!)
  }

  // --- helpers -------------------------------------------------------------------------------

  /** Runs `adb emu avd snapshot <args>` and returns the console output, trimmed. */
  private fun emuSnapshot(vararg args: String): String {
    val out: String? = device.executeAdbCommand(ADB_TIMEOUT_MS, "emu", "avd", "snapshot", *args)
    Assert.assertNotNull("adb emu avd snapshot ${args.joinToString(" ")} produced no output", out)
    val text = out!!.trim()
    CLog.i("%s: adb emu avd snapshot %s -> %s", TAG, args.joinToString(" "), text)
    return text
  }

  private fun assertOk(what: String, out: String) {
    Assert.assertTrue("$what failed: $out", out.lines().last().trim() == "OK" && !out.contains("KO:"))
  }

  private fun assertKo(what: String, out: String, messagePart: String) {
    Assert.assertTrue("$what should have failed, got: $out", out.contains("KO:"))
    Assert.assertTrue("$what: '$out' does not mention '$messagePart'", out.contains(messagePart))
  }

  private fun listedSnapshots(): List<String> {
    val out = emuSnapshot("list")
    assertOk("adb emu avd snapshot list", out)
    // "List of snapshots present on all disks:" followed by one name per line, then OK; or
    // "There is no snapshot available." when there are none.
    return out.lines().map { it.trim() }.filter {
      it.isNotEmpty() && it != "OK" && !it.startsWith("List of snapshots") &&
        !it.startsWith("There is no snapshot")
    }
  }

  private fun shell(cmd: String): String = (device.executeShellCommand(cmd) ?: "").trim()

  private fun setMarker(value: String) {
    shell("mkdir -p $STATE_DIR && echo '$value' > $STATE_DIR/marker && sync")
    Assert.assertEquals("Guest marker was not written", value, marker())
  }

  private fun marker(): String = shell("cat $STATE_DIR/marker 2>/dev/null")

  private fun bootId(): String = shell("cat /proc/sys/kernel/random/boot_id")

  private fun snapshotDir(name: String): File = avdDir.resolve("snapshots").resolve(name)

  /** Whether this emulator rejects snapshots (-no-snapshot). Probed once with a save attempt. */
  private fun snapshotsDisabled(): Boolean {
    probedSnapshotsDisabled?.let {
      return it
    }
    val out = emuSnapshot("save", PROBE_SNAPSHOT)
    val disabled = out.contains("KO:") && out.contains("-no-snapshot")
    if (!disabled) {
      assertOk("adb emu avd snapshot save $PROBE_SNAPSHOT", out)
      assertOk("adb emu avd snapshot del $PROBE_SNAPSHOT", emuSnapshot("del", PROBE_SNAPSHOT))
    }
    probedSnapshotsDisabled = disabled
    return disabled
  }

  // --- tests ---------------------------------------------------------------------------------

  /** save / list / load / del of a named snapshot from the console, with its on-disk layout. */
  @Test
  fun adbEmuSaveListLoadDelete() {
    Assume.assumeFalse("snapshots are disabled on this emulator", snapshotsDisabled())
    val name = "ets_adb"
    val bootIdBefore = bootId()
    setMarker("before_$name")

    assertOk("save", emuSnapshot("save", name))
    Assert.assertTrue("${snapshotDir(name)}/version.txt missing", snapshotDir(name).resolve("version.txt").isFile)
    Assert.assertTrue(
      "${snapshotDir(name)}/renderer missing or empty",
      snapshotDir(name).resolve("renderer").list()?.isNotEmpty() == true,
    )
    Assert.assertTrue("'$name' missing from list: ${listedSnapshots()}", name in listedSnapshots())

    setMarker("after_$name")
    assertOk("load", emuSnapshot("load", name))
    Assert.assertEquals("Guest state was not restored from '$name'", "before_$name", marker())
    Assert.assertEquals("Loading a runtime snapshot must not reboot", bootIdBefore, bootId())
    Assert.assertEquals("Guest must respond after the load", "ok", shell("echo ok"))

    assertOk("del", emuSnapshot("del", name))
    Assert.assertFalse("${snapshotDir(name)} still exists", snapshotDir(name).exists())
    Assert.assertFalse("'$name' still listed after del", name in listedSnapshots())
  }

  /** `delete` is an alias of `del`. */
  @Test
  fun adbEmuDeleteAlias() {
    Assume.assumeFalse("snapshots are disabled on this emulator", snapshotsDisabled())
    val name = "ets_adb_alias"
    assertOk("save", emuSnapshot("save", name))
    assertOk("delete", emuSnapshot("delete", name))
    Assert.assertFalse("${snapshotDir(name)} still exists", snapshotDir(name).exists())
  }

  /** Bad arguments fail with KO and leave nothing behind; the VM keeps running. */
  @Test
  fun adbEmuRejectsBadArguments() {
    val bootIdBefore = bootId()
    assertKo("save without a name", emuSnapshot("save"), "KO:")
    assertKo("load without a name", emuSnapshot("load"), "KO:")
    assertKo("del without a name", emuSnapshot("del"), "KO:")
    assertKo("save ../escape", emuSnapshot("save", "../escape"), "Invalid snapshot name")
    assertKo("load a/b", emuSnapshot("load", "a/b"), "Invalid snapshot name")
    assertKo("del ../x", emuSnapshot("del", "../x"), "Invalid snapshot name")
    // (A backslash does not reach the emulator through the console's tokenizer, so "a\b" is
    // only covered by NamedSnapshotTest, which talks gRPC directly.)
    Assert.assertFalse(avdDir.resolve("escape").exists())
    Assert.assertFalse(avdDir.parentFile.resolve("escape").exists())
    // Deleting a snapshot that does not exist is harmless (QEMU treats it as already gone).
    emuSnapshot("del", "ets_does_not_exist")
    if (!snapshotsDisabled()) {
      // Never saved: no version.txt, rejected before QEMU is asked to load anything.
      assertKo("load of an unknown snapshot", emuSnapshot("load", "ets_does_not_exist"), "incompatible")
    }
    Assert.assertEquals("VM must keep running after rejected commands", bootIdBefore, bootId())
    Assert.assertEquals("ok", shell("echo ok"))
  }

  /** With -no-snapshot, save and load fail with KO while list still works. */
  @Test
  fun adbEmuSaveAndLoadAreRejectedWhenSnapshotsAreDisabled() {
    Assume.assumeTrue("snapshots are enabled on this emulator", snapshotsDisabled())
    assertKo("save", emuSnapshot("save", "ets_adb_disabled"), "-no-snapshot")
    Assert.assertFalse(snapshotDir("ets_adb_disabled").exists())
    val listed = listedSnapshots()
    if (listed.isNotEmpty()) {
      assertKo("load ${listed.first()}", emuSnapshot("load", listed.first()), "-no-snapshot")
    }
    Assert.assertEquals("ok", shell("echo ok"))
  }

  companion object {
    private const val TAG = "AdbEmuSnapshotTest"
    private const val PROBE_SNAPSHOT = "ets_adb_probe"
    // Guest (Android) path; independent of the host OS.
    private const val STATE_DIR = "/data/local/tmp/ets_adb_snapshot"
    private const val ADB_TIMEOUT_MS = 300_000L

    @Volatile private var probedSnapshotsDisabled: Boolean? = null
  }
}
