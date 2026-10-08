package com.android.tools.e2etests.ui

import com.android.emulator.control.SnapshotPackage
import com.android.emulator.control.SnapshotServiceGrpc
import com.android.tools.e2etests.grpc.getHostGrpcChannel
import com.android.tools.testlib.emu.Discovery
import com.android.tools.testlib.emu.findEmulator
import com.android.tradefed.log.LogUtil.CLog
import com.android.tradefed.testtype.DeviceJUnit4ClassRunner
import java.io.StringReader
import java.util.concurrent.TimeUnit
import javax.xml.parsers.DocumentBuilderFactory
import org.junit.Assert
import org.junit.Test
import org.junit.runner.RunWith
import org.w3c.dom.Element
import org.xml.sax.InputSource

private const val ITEMS_TO_TOUCH = 4
private const val DEFAULT_MIN_Y = 400
private const val SNAPSHOT_LOAD_ROUNDS = 3
private const val SNAPSHOT_NAME = "default_boot"

/**
 * Host-driven UI responsiveness test modeled after profiler.py's single-iteration sequence:
 * 1. Cold boot once -> interact with Settings -> save snapshot
 * 2. Repeat 3 times: { load snapshot -> interact with Settings -> save snapshot }
 *
 * Like a human interacting with the Android Device Hub UI:
 * - Uses `uiautomator dump` to inspect what clickable items are currently on the screen.
 * - Issues touch events from the Android Device Hub UI on the host (`tapScreen`) to touch each
 *   item and clicks the Device Hub toolbar `Back` button (`click("Back")`) to return.
 * - Watches the screen via `uiautomator dump` to verify the UI hierarchy updates after each touch,
 *   while recording a single combined host-side video (`snapshot_ui_video_*.mp4` via ffmpeg) and
 *   screenshots (`snapshot_ui_*.png` via CDP).
 */
@RunWith(DeviceJUnit4ClassRunner::class)
class SnapshotUiTest : UiTestBase() {
  override val logPrefix: String = "snapshot_ui"

  @Test
  fun settingsItemsRespondAcrossColdBootAndSnapshotLoads() {
    // 1. Cold boot phase: interact with Settings, then save snapshot.
    CLog.i("%s: [Phase 1: Cold Boot] Interacting with Settings...", TAG)
    interactWithSettings(phase = "cold_boot")
    saveSnapshot(phase = "cold_boot")

    // 2. Snapshot Load cycles (3 times): { load snapshot, interact with Settings, save snapshot }
    for (round in 1..SNAPSHOT_LOAD_ROUNDS) {
      val phase = "load_$round"
      CLog.i(
        "%s: [Phase 2.%d: Snapshot Load Round %d/%d] Loading snapshot...",
        TAG,
        round,
        round,
        SNAPSHOT_LOAD_ROUNDS,
      )
      loadSnapshot(phase = phase)
      interactWithSettings(phase = phase)
      saveSnapshot(phase = phase)
    }
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

  private fun snapshotService(): SnapshotServiceGrpc.SnapshotServiceBlockingStub {
    val serial = getDevice().getSerialNumber()
    val discovery =
      findEmulator(serial) ?: findDiscoveryFile(serial)?.let { Discovery(it.toPath()) }
    Assert.assertNotNull("Could not find emulator discovery file for $serial", discovery)
    return SnapshotServiceGrpc.newBlockingStub(getHostGrpcChannel(discovery!!))
      .withDeadlineAfter(120, TimeUnit.SECONDS)
  }

  private fun saveSnapshot(phase: String, snapshotId: String = SNAPSHOT_NAME) {
    CLog.i("%s: [%s] Saving snapshot '%s'...", TAG, phase, snapshotId)
    val startMs = System.currentTimeMillis()
    val req = SnapshotPackage.newBuilder().setSnapshotId(snapshotId).build()
    val resp = snapshotService().saveSnapshot(req)
    val elapsedSec = (System.currentTimeMillis() - startMs) / 1000.0
    Assert.assertTrue(
      "[$phase] Failed to save snapshot '$snapshotId': ${resp.err.toStringUtf8()}",
      resp.success,
    )
    CLog.i("%s: [%s] Snapshot '%s' saved in %.2fs.", TAG, phase, snapshotId, elapsedSec)
    attachScreenshot("${phase}_after_save")
  }

  private fun loadSnapshot(phase: String, snapshotId: String = SNAPSHOT_NAME) {
    CLog.i("%s: [%s] Loading snapshot '%s'...", TAG, phase, snapshotId)
    val startMs = System.currentTimeMillis()
    val req = SnapshotPackage.newBuilder().setSnapshotId(snapshotId).build()
    val resp = snapshotService().loadSnapshot(req)
    val elapsedSec = (System.currentTimeMillis() - startMs) / 1000.0
    Assert.assertTrue(
      "[$phase] Failed to load snapshot '$snapshotId': ${resp.err.toStringUtf8()}",
      resp.success,
    )
    CLog.i(
      "%s: [%s] Snapshot '%s' loaded in %.2fs. Waiting for adb shell...",
      TAG,
      phase,
      snapshotId,
      elapsedSec,
    )
    eventually("[$phase] adb shell responsive after snapshot load", timeoutMs = 30_000) {
      getDevice().executeShellCommand("echo ready").contains("ready")
    }
    waitForStream()
    attachScreenshot("${phase}_after_load")
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
