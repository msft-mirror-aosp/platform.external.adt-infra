package com.android.tools.e2etests.ui

import com.android.tradefed.config.Option
import com.android.tradefed.log.LogUtil.CLog
import com.android.tradefed.testtype.DeviceJUnit4ClassRunner
import java.io.StringReader
import javax.xml.parsers.DocumentBuilderFactory
import org.junit.After
import org.junit.Assert
import org.junit.Test
import org.junit.runner.RunWith
import org.w3c.dom.Element
import org.xml.sax.InputSource

private const val GMS_PACKAGE = "com.google.android.gms"
private const val MAPS_PID = "maps_pid"

/**
 * Part of the screen that only shows the map: below the search box and above the bottom sheet,
 * which can cover the lower half of the screen.
 */
private val MAP_AREA = RenderingUiTestBase.Region(0.1, 0.15, 0.9, 0.45)

/** Buttons of Maps' first run, permission and promo dialogs that get the map out of the way. */
private val DISMISS_BUTTONS =
  listOf(
    "skip",
    "accept & continue",
    "accept",
    "agree",
    "got it",
    "no thanks",
    "not now",
    "maybe later",
    "later",
    "while using the app",
    "only this time",
    "allow",
    "use without an account",
    "dismiss",
    "continue",
    "ok",
  )

/**
 * Google Maps rendering test across emulator snapshot boots (see [SnapshotUiTestBase]), driven
 * through the Android Device Hub UI:
 * 1. `cold_boot`: open Maps at the device location (GPS fix), search for a place (drops a pin and
 *    loads the area), interact with the map while recording, verify, and leave Maps in the
 *    foreground; the emulator is then shut down through gRPC, which saves its snapshot.
 * 2. `load_<N>` (after each relaunch from the snapshot): check that the snapshot brought back the
 *    same Maps process showing the map, interact with the map while recording and verify, use
 *    other apps (Home, Settings), switch back to Maps and check the map again, and leave Maps in
 *    the foreground for the next shutdown.
 *
 * Each interaction:
 * - Pans (swipes) and zooms (double tap, one finger zoom out) the map through the Device Hub UI
 *   (`swipeScreen`, `tapScreen`) for a few seconds while recording an on-device video
 *   (`screenrecord`), attached as `maps_ui_<phase>_device_video.mp4` and checked with ffmpeg
 *   `blackdetect`.
 * - Checks that the map is rendered (not black or blank) before and after the gestures and that the
 *   gestures changed what is drawn, and that the device screen and the Device Hub display are not
 *   black.
 * - Checks that Maps is still in the foreground and did not crash or stop responding.
 *
 * Needs Google Maps on the system image and internet access from the emulator for the map data.
 * Enables Google Play services, which the ETS device setup disables, for the duration of the test
 * (of the whole snapshot sequence when run in one).
 */
@RunWith(DeviceJUnit4ClassRunner::class)
class MapsUiTest : RenderingUiTestBase() {
  override val logPrefix: String = "maps_ui"

  @Option(name = "maps_package", description = "Package name of Google Maps on the device.")
  private var mMapsPackage: String = "com.google.android.apps.maps"

  @Option(name = "latitude", description = "Latitude of the device location and the map.")
  private var mLatitude: String = "37.4220"

  @Option(name = "longitude", description = "Longitude of the device location and the map.")
  private var mLongitude: String = "-122.0841"

  @Option(name = "search_query", description = "Place searched in Maps to load the map around it.")
  private var mSearchQuery: String = "Googleplex"

  private var mGmsWasDisabled = false

  @After
  fun stopMaps() {
    // In the snapshot sequence Maps keeps running, so that it is part of the snapshot.
    if (inSnapshotSequence) return
    runCatching { shell("am force-stop $mMapsPackage") }
    if (mGmsWasDisabled) {
      runCatching { shell("pm disable-user --user 0 $GMS_PACKAGE") }
      mGmsWasDisabled = false
    }
  }

  @Test
  fun mapRendersAcrossColdBootAndSnapshotBoots() {
    if (beginPhase()) {
      // The snapshot brought back Maps showing the map.
      keepScreenOn()
      eventually("[$phase] Maps in the foreground after the snapshot boot", timeoutMs = 30_000) {
        mapsInForeground()
      }
      assertSameMapsProcess(phase)
      exerciseMap(phase = phase)
      // Use other apps, then switch back to Maps.
      doOtherActivity(phase)
      shell(
        "am start -W -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -p $mMapsPackage"
      )
      eventually("[$phase] Maps back in the foreground", timeoutMs = 30_000) { mapsInForeground() }
      dismissDialogs(phase)
      eventually("[$phase] map rendered after switching back to Maps", timeoutMs = 60_000) {
        mapLooksRendered()
      }
      attachPng("${phase}_map_after_other_activity", deviceScreenshot())
      assertSameMapsProcess(phase)
      assertNoCrash(phase, mMapsPackage)
    } else {
      if (isSnapshotBoot) {
        CLog.i("%s: [%s] Another test ran last before the shutdown, reopening Maps", TAG, phase)
      }
      CLog.i("%s: [%s] Opening Maps and searching for %s...", TAG, phase, mSearchQuery)
      setUpMaps()
      openMaps()
      exerciseMap(phase = phase)
    }
    val mapsPid = pidOf(mMapsPackage)
    Assert.assertTrue("[$phase] Maps is not running", mapsPid.isNotEmpty())
    storeState(MAPS_PID, mapsPid)
    endPhase()
  }

  private fun assertSameMapsProcess(phase: String) {
    Assert.assertEquals(
      "[$phase] Maps process changed across the snapshot boot (Maps crashed?)",
      loadState(MAPS_PID),
      pidOf(mMapsPackage),
    )
  }

  // --- Maps -------------------------------------------------------------------------------------

  private fun mapsInForeground(): Boolean = resumedActivity().contains(mMapsPackage)

  private fun setUpMaps() {
    Assert.assertTrue(
      "Google Maps ($mMapsPackage) is not installed on the device",
      shell("pm path $mMapsPackage").contains("package:"),
    )
    keepScreenOn()
    // The ETS device setup disables Google Play services, which Maps needs to load map data.
    mGmsWasDisabled =
      shell("pm list packages -d $GMS_PACKAGE").lines().any { it.trim() == "package:$GMS_PACKAGE" }
    if (mGmsWasDisabled) {
      CLog.i("%s: enabling %s for Maps", TAG, GMS_PACKAGE)
      shell("pm enable --user 0 $GMS_PACKAGE")
    }
    shell("am force-stop $mMapsPackage")
    // Pre-grant the runtime permissions Maps asks for so their dialogs do not cover the map.
    for (permission in
      listOf("ACCESS_FINE_LOCATION", "ACCESS_COARSE_LOCATION", "POST_NOTIFICATIONS")) {
      shell("pm grant $mMapsPackage android.permission.$permission")
    }
    // Give the device a current location (the emulator console takes longitude first).
    shell("cmd location set-location-enabled true")
    getDevice().executeAdbCommand("emu", "geo", "fix", mLongitude, mLatitude)
    clearCrashLog()
  }

  private fun openMaps() {
    val geoUri = "geo:$mLatitude,$mLongitude?z=16"
    shell("am start -W -a android.intent.action.VIEW -p $mMapsPackage -d '$geoUri'")
    eventually("Maps in foreground", timeoutMs = 30_000) { mapsInForeground() }

    // Get past first run and promo dialogs until the search box shows up.
    var searchBox: Pair<Int, Int>? = null
    val dialogsEnd = System.currentTimeMillis() + 90_000
    while (searchBox == null && System.currentTimeMillis() < dialogsEnd) {
      if (!dismissDialogs("open")) {
        searchBox = findNode(dumpUi()) { text, _ -> text.equals("Search here", ignoreCase = true) }
      }
      if (searchBox == null) Thread.sleep(2_000)
    }

    // A geo: URI only moves the camera; searching for a place drops a pin and loads the area.
    searchPlace(searchBox)
    attachPng("open_after_search", deviceScreenshot())

    val end = System.currentTimeMillis() + 120_000
    while (System.currentTimeMillis() < end) {
      val dismissed = dismissDialogs("open")
      if (!dismissed && mapsInForeground() && mapLooksRendered()) {
        CLog.i("%s: map is rendered", TAG)
        return
      }
      Thread.sleep(2_000)
    }
    attachPng("open_timeout_device_screen", deviceScreenshot())
    Assert.fail("Maps never rendered the map. UI: ${dumpUi().take(4_000)}")
  }

  /** Searches for [mSearchQuery] in the Maps search box, or with a geo: query intent without it. */
  private fun searchPlace(searchBox: Pair<Int, Int>?) {
    if (searchBox != null) {
      CLog.i("%s: searching for '%s' in the Maps search box", TAG, mSearchQuery)
      shell("input tap ${searchBox.first} ${searchBox.second}")
      val focused =
        runCatching {
            eventually("Maps search field focused", timeoutMs = 15_000) {
              Regex("""class="android.widget.EditText"[^>]*focused="true"""").containsMatchIn(dumpUi())
            }
          }
          .isSuccess
      if (focused) {
        shell("input text '${mSearchQuery.replace(" ", "%s")}'")
        Thread.sleep(1_000)
        shell("input keyevent KEYCODE_ENTER")
        Thread.sleep(5_000)
        if (mapsInForeground()) return
      }
      CLog.w("%s: searching in the search box failed, using a geo: query intent", TAG)
    }
    val query = mSearchQuery.replace(" ", "+")
    shell("am start -W -a android.intent.action.VIEW -p $mMapsPackage -d 'geo:0,0?q=$query'")
    eventually("Maps in foreground", timeoutMs = 30_000) { mapsInForeground() }
    Thread.sleep(5_000)
  }

  private fun mapLooksRendered(): Boolean =
    regionLuma(decode(deviceScreenshot(), "device screen"), MAP_AREA).looksRendered()

  /** Center of the first node in [dump] whose text or content-desc matches [matches]. */
  private fun findNode(dump: String, matches: (String, Element) -> Boolean): Pair<Int, Int>? {
    val nodes =
      runCatching {
          DocumentBuilderFactory.newInstance()
            .newDocumentBuilder()
            .parse(InputSource(StringReader(dump)))
            .getElementsByTagName("node")
        }
        .getOrNull() ?: return null
    val bounds = Regex("""\[(\d+),(\d+)\]\[(\d+),(\d+)\]""")
    for (i in 0 until nodes.length) {
      val node = nodes.item(i) as? Element ?: continue
      val text = node.getAttribute("text").ifEmpty { node.getAttribute("content-desc") }.trim()
      if (!matches(text, node)) continue
      val m = bounds.find(node.getAttribute("bounds")) ?: continue
      val (x1, y1, x2, y2) = m.destructured
      return ((x1.toInt() + x2.toInt()) / 2) to ((y1.toInt() + y2.toInt()) / 2)
    }
    return null
  }

  /** Taps the first dialog button found in [DISMISS_BUTTONS]. Returns whether one was tapped. */
  private fun dismissDialogs(phase: String): Boolean {
    val dump = dumpUi()
    for (label in DISMISS_BUTTONS) {
      val (x, y) = findNode(dump) { text, _ -> text.equals(label, ignoreCase = true) } ?: continue
      CLog.i("%s: [%s] dismissing dialog: tapping '%s' at (%d, %d)", TAG, phase, label, x, y)
      attachScreenshot("${phase}_dialog_${label.replace(Regex("\\W+"), "_")}")
      shell("input tap $x $y")
      Thread.sleep(2_000)
      return true
    }
    return false
  }

  // --- verification -----------------------------------------------------------------------------

  /** Interacts with the map while recording it and verifies it renders and does not crash. */
  private fun exerciseMap(phase: String) {
    shell("input keyevent KEYCODE_WAKEUP")
    dismissDialogs(phase)
    Assert.assertTrue("[$phase] Maps is not in the foreground", mapsInForeground())

    val beforePng = deviceScreenshot()
    attachPng("${phase}_map_before", beforePng)
    val before = decode(beforePng, "$phase map")
    assertNotBlack("$phase map before interacting", before, MAP_AREA)

    recordDeviceVideo(phase) { interactWithMap(phase) }

    // Let the tiles of the new viewport load.
    Thread.sleep(3_000)
    val afterPng = deviceScreenshot()
    attachPng("${phase}_map_after", afterPng)
    val after = decode(afterPng, "$phase map")
    // The new viewport may legitimately be sparse (e.g. a campus lawn), so only require that it is
    // not black and not a single flat color, which is what a map that failed to render looks like.
    assertNotBlack("$phase map after interacting", after, MAP_AREA) { it.notBlank() }
    val diff = meanAbsDiff(before, after, MAP_AREA)
    CLog.i("%s: [%s] map difference after the gestures: %.2f", TAG, phase, diff)
    Assert.assertTrue("[$phase] The map did not move or zoom (difference $diff)", diff > 3)

    assertDisplaysNotBlack(phase)
    assertNoCrash(phase, mMapsPackage)
    Assert.assertTrue("[$phase] Maps left the foreground", mapsInForeground())
  }

  /**
   * Pans and zooms the map through the Device Hub UI for a few seconds. The gestures zoom back out
   * after zooming in, so repeating them every round does not keep zooming in.
   */
  private fun interactWithMap(phase: String) {
    CLog.i("%s: [%s] panning and zooming the map via Device Hub UI...", TAG, phase)
    swipeScreen(0.75, 0.5, 0.25, 0.5, steps = 15)
    Thread.sleep(700)
    swipeScreen(0.5, 0.65, 0.5, 0.35, steps = 15)
    Thread.sleep(700)
    // Double tap zooms in.
    tapScreen(0.5, 0.5)
    Thread.sleep(80)
    tapScreen(0.5, 0.5)
    Thread.sleep(1_000)
    swipeScreen(0.3, 0.45, 0.6, 0.55, steps = 15)
    Thread.sleep(700)
    // Tap, then immediately drag up with the second touch: one finger zoom out.
    tapScreen(0.5, 0.55)
    Thread.sleep(80)
    swipeScreen(0.5, 0.55, 0.5, 0.35, steps = 10)
    Thread.sleep(700)
  }

  /** Uses other apps (Home, Settings), which puts Maps in the background. */
  private fun doOtherActivity(phase: String) {
    CLog.i("%s: [%s] Using other apps...", TAG, phase)
    click("Home")
    eventually("[$phase] launcher in foreground") {
      resumedActivity().contains("launcher", ignoreCase = true)
    }
    shell("am start -W --activity-clear-task -a android.settings.SETTINGS")
    eventually("[$phase] Settings in foreground") {
      resumedActivity().contains("settings", ignoreCase = true)
    }
    swipeScreen(0.5, 0.75, 0.5, 0.3)
    Thread.sleep(500)
    swipeScreen(0.5, 0.3, 0.5, 0.75)
    Thread.sleep(500)
    attachScreenshot("${phase}_other_activity")
    click("Back")
    Thread.sleep(500)
    click("Home")
    Thread.sleep(500)
  }
}
