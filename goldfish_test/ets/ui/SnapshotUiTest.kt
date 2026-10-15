package com.android.tools.e2etests.ui

import com.android.tradefed.config.Option
import com.android.tradefed.log.LogUtil.CLog
import com.android.tradefed.testtype.DeviceJUnit4ClassRunner
import java.io.StringReader
import javax.xml.parsers.DocumentBuilderFactory
import org.junit.Assert
import org.junit.Test
import org.junit.runner.RunWith
import org.w3c.dom.Element
import org.xml.sax.InputSource

private const val ITEMS_TO_TOUCH = 4
private const val DEFAULT_MIN_Y = 400

/**
 * [UiTestBase] plus the phase handling shared by the UI tests that check the emulator across
 * snapshot boots (SnapshotUiTest, WebGlAquariumUiTest, MapsUiTest).
 *
 * The emulator saves its quickboot snapshot when it exits, so the tests do not save or load
 * snapshots themselves. Instead the test sequence (android_ets_cfg.py with
 * `--snapshot_relaunch_rounds`) runs them once per phase:
 * 1. `cold_boot`: the emulator cold boots, the test sets up its app and exercises it, and leaves the
 *    app in the foreground. Then CloseEmulatorTest shuts the emulator down through gRPC
 *    (`setVmState(SHUTDOWN)`), which saves the snapshot.
 * 2. `load_<N>`: the sequence relaunches the emulator, which boots from that snapshot, and runs the
 *    test again with `snapshot_phase` set to `load_<N>`. The test checks that the emulator resumed
 *    from the snapshot saved at the end of the previous phase and that its app came back, exercises
 *    it again and leaves it in the foreground for the next shutdown.
 *
 * Without `snapshot_phase` (e.g. against an external emulator) only the cold boot phase runs.
 *
 * Whatever has to survive from one phase to the next (the guest boot id, process ids, ...) is kept
 * on the device under [STATE_DIR], so it is saved and restored together with the snapshot.
 */
abstract class SnapshotUiTestBase : UiTestBase() {
  @Option(
    name = "snapshot_phase",
    description =
      "Phase of the snapshot sequence: cold_boot, or load_<N> after the emulator was shut down " +
        "(saving its snapshot) and relaunched from the snapshot for the N-th time. Empty runs " +
        "only the cold boot phase.",
  )
  private var mSnapshotPhase: String = ""

  /** `cold_boot` or `load_<N>`. */
  protected val phase: String
    get() = mSnapshotPhase.ifEmpty { COLD_BOOT }

  /** Whether the emulator booted from the snapshot it saved when the previous phase shut it down. */
  protected val isSnapshotBoot: Boolean
    get() = phase != COLD_BOOT

  /**
   * Whether the test sequence shuts the emulator down after this run and relaunches it from its
   * snapshot. The tests then leave their app running, so that it is part of the snapshot.
   */
  protected val inSnapshotSequence: Boolean
    get() = mSnapshotPhase.isNotEmpty()

  protected fun shell(cmd: String): String = getDevice().executeShellCommand(cmd) ?: ""

  /** Value [key] of this test that an earlier phase stored on the device, or "". */
  protected fun loadState(key: String): String =
    shell("cat $STATE_DIR/$logPrefix.$key 2>/dev/null").trim()

  /** Stores [value] on the device for the following phases, which see it through the snapshot. */
  protected fun storeState(key: String, value: String) {
    shell("mkdir -p $STATE_DIR && echo '$value' > $STATE_DIR/$logPrefix.$key")
  }

  private fun bootId(): String = shell("cat /proc/sys/kernel/random/boot_id").trim()

  private fun previousPhase(): String {
    val round = phase.removePrefix(LOAD_PREFIX).toIntOrNull()
    Assert.assertNotNull("Unknown snapshot_phase '$phase'", round)
    return if (round!! <= 1) COLD_BOOT else "$LOAD_PREFIX${round - 1}"
  }

  /** Test sequencer agent that ran the emulator during [phase] (see sequence/agent_common.py). */
  private fun emulatorAgent(phase: String): String =
    if (phase == COLD_BOOT) "goldfish" else "goldfish_$phase"

  /**
   * Starts the phase. After a snapshot boot, checks that the emulator resumed the guest from the
   * snapshot saved when the previous phase shut it down, rather than cold booting or loading an older
   * snapshot.
   *
   * The check only relies on state stored when the previous phase *started*, so a test failure in
   * the previous phase does not make the following phases fail as well: they still verify that the
   * emulator resumed from the latest snapshot. A failure here names the phase whose shutdown did not
   * produce that snapshot (e.g. because its emulator crashed), rather than blaming this phase.
   *
   * @return whether this test's app should have been restored in the foreground: this test was the
   *   last one to start before the shutdown and it finished the previous phase. False on cold boot,
   *   after another test (of the same plan) ran after it, or if it failed in the previous phase.
   */
  protected fun beginPhase(): Boolean {
    CLog.i("%s: [%s] Starting phase%s", TAG, phase, if (isSnapshotBoot) " after snapshot boot" else "")
    if (!isSnapshotBoot) {
      startPhase()
      return false
    }
    attachScreenshot("${phase}_after_snapshot_boot")
    val previous = previousPhase()
    val savedBootId = loadState(BOOT_ID)
    val started = loadState(STARTED_PHASE)
    val finished = loadState(LAST_PHASE)
    val lastTest = shell("cat $STATE_DIR/$LAST_TEST 2>/dev/null").trim()
    val isRetry = started == phase
    val snapshotBootId = if (isRetry) loadState(SNAPSHOT_BOOT_ID) else savedBootId
    val snapshotStarted = if (isRetry) loadState(SNAPSHOT_STARTED_PHASE) else started
    if (!isRetry) {
      storeState(SNAPSHOT_BOOT_ID, savedBootId)
      storeState(SNAPSHOT_STARTED_PHASE, started)
    }
    CLog.i(
      "%s: [%s] Snapshot state: started=%s finished=%s last_test=%s (retry=%b)",
      TAG,
      phase,
      snapshotStarted,
      finished,
      lastTest,
      isRetry,
    )
    startPhase()

    Assert.assertTrue(
      "[$phase] No state from earlier phases on the device: the emulator cold booted with fresh " +
        "data, or $logPrefix never ran in $COLD_BOOT",
      snapshotBootId.isNotEmpty(),
    )
    Assert.assertEquals(
      "[$phase] The emulator cold booted instead of resuming from the snapshot saved when " +
        "$previous shut it down: the snapshot is missing or failed to load. Check the " +
        "${emulatorAgent(previous)} log (did the emulator crash or fail to save on exit?) and the " +
        "${emulatorAgent(phase)} log (did it fail to load the snapshot?)",
      snapshotBootId,
      bootId(),
    )
    Assert.assertEquals(
      "[$phase] The emulator resumed from an older snapshot (taken after ${snapshotStarted.ifEmpty { "?" }} " +
        "started) instead of the one saved when $previous shut it down: the emulator did not save " +
        "its snapshot at the end of $previous. Check the ${emulatorAgent(previous)} log, e.g. for " +
        "a crash during $previous",
      previous,
      snapshotStarted,
    )
    if (isRetry) {
      CLog.w(
        "%s: [%s] Retrying %s in %s; reopening its app cleanly",
        TAG,
        phase,
        logPrefix,
        phase,
      )
      return false
    }
    if (finished != previous) {
      CLog.w(
        "%s: [%s] %s did not finish %s (it failed), so its app is not expected to be restored",
        TAG,
        phase,
        logPrefix,
        previous,
      )
      return false
    }
    return lastTest == logPrefix
  }

  /**
   * Records that this test started the phase: the guest boot id and the phase, which the next phase
   * sees through the snapshot, and that this test now owns the foreground.
   */
  private fun startPhase() {
    storeState(BOOT_ID, bootId())
    storeState(STARTED_PHASE, phase)
    shell("echo '$logPrefix' > $STATE_DIR/$LAST_TEST")
  }

  /** Ends the phase with this test's app in the foreground, ready to be saved in the snapshot. */
  protected fun endPhase() {
    storeState(LAST_PHASE, phase)
    shell("echo '$logPrefix' > $STATE_DIR/$LAST_TEST")
    attachScreenshot("${phase}_before_shutdown")
    CLog.i("%s: [%s] Phase done", TAG, phase)
  }

  companion object {
    const val COLD_BOOT = "cold_boot"
    const val LOAD_PREFIX = "load_"

    /** Device directory with the state that carries over from one phase to the next. */
    const val STATE_DIR = "/data/local/tmp/ets_ui_snapshot"
    private const val BOOT_ID = "boot_id"
    private const val STARTED_PHASE = "started_phase"
    private const val SNAPSHOT_BOOT_ID = "snapshot_boot_id"
    private const val SNAPSHOT_STARTED_PHASE = "snapshot_started_phase"
    private const val LAST_PHASE = "last_phase"
    private const val LAST_TEST = "last_test"
  }
}

/**
 * Host-driven UI responsiveness test modeled after profiler.py's single-iteration sequence, across
 * snapshot boots (see [SnapshotUiTestBase]):
 * 1. `cold_boot`: interact with Settings, leave it in the foreground; the emulator is then shut
 *    down through gRPC, which saves its snapshot.
 * 2. `load_<N>` (after each relaunch from the snapshot): check that the emulator booted from the
 *    snapshot with Settings still in the foreground, interact with Settings again and leave it in
 *    the foreground for the next shutdown.
 *
 * Like a human interacting with the Android Device Hub UI:
 * - Uses `uiautomator dump` to inspect what clickable items are currently on the screen.
 * - Issues touch events from the Android Device Hub UI on the host (`tapScreen`) to touch each
 *   item and clicks the Device Hub toolbar `Back` button (`click("Back")`) to return.
 * - Watches the screen via `uiautomator dump` to verify the UI hierarchy updates after each touch,
 *   while recording a host-side video per phase (`snapshot_ui_video_*.mp4` via ffmpeg) and
 *   screenshots (`snapshot_ui_*.png` via CDP).
 */
@RunWith(DeviceJUnit4ClassRunner::class)
class SnapshotUiTest : SnapshotUiTestBase() {
  override val logPrefix: String = "snapshot_ui"

  @Test
  fun settingsItemsRespondAcrossColdBootAndSnapshotBoots() {
    val restored = beginPhase()
    if (restored) {
      shell("input keyevent KEYCODE_WAKEUP")
      eventually("[$phase] Settings in the foreground after the snapshot boot", timeoutMs = 30_000) {
        resumedActivity().contains("settings", ignoreCase = true)
      }
    }
    CLog.i("%s: [%s] Interacting with Settings...", TAG, phase)
    interactWithSettings(phase = phase)
    endPhase()
  }

  private fun interactWithSettings(phase: String) {
    ensureSettingsApp()
    attachScreenshot("${phase}_initial_settings")

    CLog.i("%s: [%s] Taking initial uiautomator dump...", TAG, phase)
    val initialDump = dumpUi()
    Assert.assertTrue("[$phase] Initial uiautomator dump was empty", initialDump.isNotEmpty())

    val (screenWidth, screenHeight) = getScreenSize(initialDump)
    val minY = minOf(DEFAULT_MIN_Y, (screenHeight * 0.30).toInt())
    val maxY = (screenHeight * 0.92).toInt()
    val validCenters =
      getClickableCenters(initialDump).filter { (x, y) ->
        x in 1 until screenWidth && y in (minY + 1) until maxY
      }

    Assert.assertTrue(
      "[$phase] No clickable items found in Settings within y in ($minY, $maxY) on ${screenWidth}x${screenHeight} screen",
      validCenters.isNotEmpty(),
    )

    val count = minOf(ITEMS_TO_TOUCH, validCenters.size)
    CLog.i(
      "%s: [%s] Found %d clickable items on %dx%d screen. Starting hub tap-back sequence (%d items)...",
      TAG,
      phase,
      validCenters.size,
      screenWidth,
      screenHeight,
      count,
    )

    for (i in 0 until count) {
      val (x, y) = validCenters[i]
      val normX = x.toDouble() / screenWidth.toDouble()
      val normY = y.toDouble() / screenHeight.toDouble()
      CLog.i(
        "%s: [%s %d/%d] Touching item at (%d, %d) -> norm (%.3f, %.3f) via Device Hub UI...",
        TAG,
        phase,
        i + 1,
        count,
        x,
        y,
        normX,
        normY,
      )
      tapScreen(normX, normY)

      var changed = false
      for (attempt in 1..5) {
        Thread.sleep(3_000)
        val currentDump = dumpUi()
        if (currentDump.isNotEmpty() && currentDump != initialDump) {
          changed = true
          break
        }
        CLog.i("%s: [%s] UI unchanged, waiting longer (attempt %d/5)...", TAG, phase, attempt)
      }

      attachScreenshot("${phase}_item_${i + 1}_touched")
      Assert.assertTrue(
        "[$phase] UI did not change after touching item ${i + 1} at ($x, $y) via Device Hub within 15 seconds.",
        changed,
      )

      CLog.i("%s: [%s] Clicking Back button in Device Hub UI...", TAG, phase)
      click("Back")
      Thread.sleep(2_000)
      attachScreenshot("${phase}_item_${i + 1}_back")
    }
  }

  private fun ensureSettingsApp() {
    CLog.i("%s: Launching Settings app...", TAG)
    getDevice().executeShellCommand("input keyevent KEYCODE_WAKEUP")
    getDevice().executeShellCommand("am start -W --activity-clear-task -a android.settings.SETTINGS")
    eventually("Settings in foreground") {
      resumedActivity().contains("settings", ignoreCase = true)
    }
    Thread.sleep(3_000)
  }

  private fun dumpUi(): String {
    getDevice().executeShellCommand("uiautomator dump /data/local/tmp/uidump.xml")
    return getDevice().executeShellCommand("cat /data/local/tmp/uidump.xml").trim()
  }

  private fun getScreenSize(dump: String): Pair<Int, Int> {
    val wmOut = getDevice().executeShellCommand("wm size")
    val wmMatch = Regex("(\\d+)x(\\d+)").find(wmOut)
    if (wmMatch != null) {
      val w = wmMatch.groupValues[1].toInt()
      val h = wmMatch.groupValues[2].toInt()
      if (w > 0 && h > 0) return w to h
    }
    val boundsMatch = Regex("""bounds="\[0,0\]\[(\d+),(\d+)\]"""").find(dump)
    if (boundsMatch != null) {
      val w = boundsMatch.groupValues[1].toInt()
      val h = boundsMatch.groupValues[2].toInt()
      if (w > 0 && h > 0) return w to h
    }
    return 1080 to 2400
  }

  private fun getClickableCenters(dump: String): List<Pair<Int, Int>> {
    val centers = mutableListOf<Pair<Int, Int>>()
    val boundsRegex = Regex("""\[(\d+),(\d+)\]\[(\d+),(\d+)\]""")
    runCatching {
        val doc =
          DocumentBuilderFactory.newInstance()
            .newDocumentBuilder()
            .parse(InputSource(StringReader(dump)))
        val nodes = doc.getElementsByTagName("node")
        for (i in 0 until nodes.length) {
          val elem = nodes.item(i) as? Element ?: continue
          if (elem.getAttribute("clickable") == "true") {
            val bounds = elem.getAttribute("bounds")
            val match = boundsRegex.find(bounds)
            if (match != null) {
              val x1 = match.groupValues[1].toInt()
              val y1 = match.groupValues[2].toInt()
              val x2 = match.groupValues[3].toInt()
              val y2 = match.groupValues[4].toInt()
              if (x2 > x1 && y2 > y1) {
                centers.add(((x1 + x2) / 2) to ((y1 + y2) / 2))
              }
            }
          }
        }
      }
      .onFailure { e -> CLog.w("%s: Error parsing UI dump XML: %s", TAG, e.message) }
    return centers.distinct()
  }
}
