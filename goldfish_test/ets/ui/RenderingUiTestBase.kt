package com.android.tools.e2etests.ui

import com.android.tradefed.config.Option
import com.android.tradefed.log.LogUtil.CLog
import com.android.tradefed.result.ByteArrayInputStreamSource
import com.android.tradefed.result.LogDataType
import java.awt.image.BufferedImage
import java.io.ByteArrayInputStream
import java.io.File
import java.util.Base64
import java.util.concurrent.TimeUnit
import javax.imageio.ImageIO
import kotlin.math.abs
import kotlin.math.sqrt
import org.json.JSONObject
import org.junit.After
import org.junit.Assert

/**
 * [SnapshotUiTestBase] plus helpers for UI tests that check guest rendering across snapshot
 * boots (WebGlAquariumUiTest, MapsUiTest): on-device video recording with ffmpeg
 * `blackdetect`, black screen checks of the device screenshot and the Device Hub display, and
 * crash checks.
 */
abstract class RenderingUiTestBase : SnapshotUiTestBase() {
  @Option(name = "video_seconds", description = "Length of the on-device video recorded per phase.")
  protected var mVideoSeconds: Int = 5

  @After
  fun restoreScreenTimeout() {
    // In the snapshot sequence the screen stays on, so that the app is still showing when the
    // emulator boots from the snapshot.
    if (!inSnapshotSequence) runCatching { shell("svc power stayon false") }
  }

  protected fun keepScreenOn() {
    shell("input keyevent KEYCODE_WAKEUP")
    shell("wm dismiss-keyguard")
    shell("svc power stayon true")
  }

  protected fun pidOf(pkg: String): String = shell("pidof $pkg").trim()

  protected fun dumpUi(): String {
    shell("uiautomator dump /data/local/tmp/uidump.xml")
    return shell("cat /data/local/tmp/uidump.xml").trim()
  }

  // --- crashes ----------------------------------------------------------------------------------

  protected fun clearCrashLog() {
    shell("logcat -b crash -c")
  }

  /** Fails if [pkg] crashed (logcat crash buffer) or shows a crash or ANR dialog. */
  protected fun assertNoCrash(phase: String, pkg: String) {
    val crashes = shell("logcat -b crash -d").lines().filter { it.contains(pkg) }
    Assert.assertTrue("[$phase] $pkg crashed:\n${crashes.joinToString("\n")}", crashes.isEmpty())
    val ui = dumpUi()
    for (dialog in listOf("keeps stopping", "isn't responding", "has stopped")) {
      Assert.assertFalse("[$phase] '$dialog' dialog is showing", ui.contains(dialog))
    }
  }

  // --- video ------------------------------------------------------------------------------------

  /**
   * Records a [mVideoSeconds] on-device video (`screenrecord`) while running [during], attaches it
   * as `<logPrefix>_<phase>_device_video` and checks it has no black segment.
   */
  protected fun recordDeviceVideo(phase: String, during: () -> Unit = {}) {
    val remote = "/data/local/tmp/${logPrefix}_$phase.mp4"
    shell("rm -f $remote")
    CLog.i("%s: [%s] Recording %ds device video...", TAG, phase, mVideoSeconds)
    val recorder =
      Thread(
          { runCatching { shell("screenrecord --time-limit $mVideoSeconds $remote") } },
          "screenrecord",
        )
        .apply {
          isDaemon = true
          start()
        }
    try {
      Thread.sleep(500)
      during()
    } finally {
      recorder.join((mVideoSeconds + 30) * 1000L)
    }
    val local = getDevice().pullFile(remote)
    shell("rm -f $remote")
    Assert.assertTrue(
      "[$phase] screenrecord did not produce a video",
      local != null && local.length() > 0,
    )
    try {
      mLogs.addTestLog(
        "${logPrefix}_${phase}_device_video",
        LogDataType.MP4,
        ByteArrayInputStreamSource(local!!.readBytes()),
      )
      verifyVideoNotBlack(phase, local)
    } finally {
      local?.delete()
    }
  }

  /** Runs ffmpeg's blackdetect over the center of [video], where the app content is. */
  protected fun verifyVideoNotBlack(phase: String, video: File) {
    val ffmpeg = mDisplayDir.takeIf { it.isNotEmpty() }?.let { findFfmpegBinary(File(it)) }
    if (ffmpeg == null) {
      CLog.w("%s: [%s] ffmpeg not found in display_dir, not analyzing the video", TAG, phase)
      return
    }
    val proc =
      ProcessBuilder(
          ffmpeg.absolutePath,
          "-hide_banner",
          "-nostats",
          "-i",
          video.absolutePath,
          "-vf",
          "crop=iw/2:ih/2:iw/4:ih/4,blackdetect=d=0.5:pix_th=0.10",
          "-an",
          "-f",
          "null",
          "-",
        )
        .redirectErrorStream(true)
        .start()
    val out = proc.inputStream.bufferedReader().readText()
    if (!proc.waitFor(60, TimeUnit.SECONDS)) proc.destroyForcibly()
    val duration =
      Regex("Duration: (\\d+):(\\d+):(\\d+(?:\\.\\d+)?)").find(out)?.destructured?.let { (h, m, s) ->
        h.toInt() * 3600 + m.toInt() * 60 + s.toDouble()
      }
    val black = out.lines().filter { it.contains("black_start") }
    CLog.i("%s: [%s] device video: %.2fs, %d black segments", TAG, phase, duration ?: -1.0, black.size)
    Assert.assertTrue(
      "[$phase] The device video shows a black screen:\n${black.joinToString("\n")}",
      black.isEmpty(),
    )
  }

  // --- screenshots ------------------------------------------------------------------------------

  /** PNG of the emulator display, taken on the device. */
  protected fun deviceScreenshot(): ByteArray =
    getDevice().getScreenshot().createInputStream().use { it.readBytes() }

  /** PNG of the emulator display as streamed by the Android Device Hub. */
  protected fun hubDisplayScreenshot(): ByteArray {
    val b = displayBounds()
    val clip =
      JSONObject()
        .put("x", b.getDouble("x"))
        .put("y", b.getDouble("y"))
        .put("width", b.getDouble("width"))
        .put("height", b.getDouble("height"))
        .put("scale", 1)
    return Base64.getDecoder()
      .decode(
        cdp()
          .call("Page.captureScreenshot", JSONObject().put("format", "png").put("clip", clip))
          .getJSONObject("result")
          .getString("data")
      )
  }

  /** Checks that neither the device screen nor the Device Hub display is black. */
  protected fun assertDisplaysNotBlack(phase: String) {
    val device = deviceScreenshot()
    attachPng("${phase}_device_screen", device)
    assertNotBlack("$phase device screen", decode(device, "$phase device screen"))
    val hub = hubDisplayScreenshot()
    attachPng("${phase}_hub_display", hub)
    assertNotBlack("$phase Device Hub display", decode(hub, "$phase Device Hub display"))
  }

  protected fun attachPng(tag: String, png: ByteArray) {
    mLogs.addTestLog("${logPrefix}_$tag", LogDataType.PNG, ByteArrayInputStreamSource(png))
  }

  protected fun decode(png: ByteArray, what: String): BufferedImage {
    val image = ImageIO.read(ByteArrayInputStream(png))
    Assert.assertNotNull("Could not decode the $what screenshot", image)
    return image!!
  }

  // --- image analysis ---------------------------------------------------------------------------

  protected data class Luma(
    val mean: Double,
    val stdDev: Double,
    val darkFraction: Double,
    val colors: Int,
  ) {
    /** Not black, not a single flat color, and with some color detail. */
    fun looksRendered(): Boolean = mean >= 20 && darkFraction <= 0.9 && stdDev >= 6 && colors >= 16

    /**
     * Not black and not a single flat color. Looser than [looksRendered], for content that may
     * legitimately be sparse, such as a map zoomed into an area with few features.
     */
    fun notBlank(): Boolean = mean >= 20 && darkFraction <= 0.9 && stdDev >= 3 && colors >= 4
  }

  /** A rectangle of an image in fractions of its width and height. */
  data class Region(val left: Double, val top: Double, val right: Double, val bottom: Double) {
    fun xs(image: BufferedImage): IntProgression =
      (image.width * left).toInt() until (image.width * right).toInt() step 2

    fun ys(image: BufferedImage): IntProgression =
      (image.height * top).toInt() until (image.height * bottom).toInt() step 2

    companion object {
      /** The center half, where the app content is. */
      val CENTER = Region(0.25, 0.25, 0.75, 0.75)
    }
  }

  /** Luma statistics of the center half of [image], where the app content is. */
  protected fun centerLuma(image: BufferedImage): Luma = regionLuma(image, Region.CENTER)

  /** Luma statistics of [region] of [image]. */
  protected fun regionLuma(image: BufferedImage, region: Region): Luma {
    var n = 0
    var sum = 0.0
    var sumSq = 0.0
    var dark = 0
    val colors = HashSet<Int>()
    for (y in region.ys(image)) {
      for (x in region.xs(image)) {
        val rgb = image.getRGB(x, y)
        val r = (rgb shr 16) and 0xff
        val g = (rgb shr 8) and 0xff
        val b = rgb and 0xff
        val luma = 0.299 * r + 0.587 * g + 0.114 * b
        n++
        sum += luma
        sumSq += luma * luma
        if (luma < 16) dark++
        colors.add(((r shr 4) shl 8) or ((g shr 4) shl 4) or (b shr 4))
      }
    }
    val mean = sum / n
    return Luma(mean, sqrt(maxOf(0.0, sumSq / n - mean * mean)), dark.toDouble() / n, colors.size)
  }

  protected fun assertNotBlack(
    what: String,
    image: BufferedImage,
    region: Region = Region.CENTER,
    rendered: (Luma) -> Boolean = Luma::looksRendered,
  ) {
    val luma = regionLuma(image, region)
    CLog.i(
      "%s: %s: mean luma %.1f, std dev %.1f, %.0f%% dark, %d colors",
      TAG,
      what,
      luma.mean,
      luma.stdDev,
      luma.darkFraction * 100,
      luma.colors,
    )
    Assert.assertTrue("$what is black or blank: $luma", rendered(luma))
  }

  /** Mean absolute per-channel difference of [region] of two same-sized images. */
  protected fun meanAbsDiff(
    a: BufferedImage,
    b: BufferedImage,
    region: Region = Region.CENTER,
  ): Double {
    if (a.width != b.width || a.height != b.height) return Double.MAX_VALUE
    var n = 0
    var sum = 0L
    for (y in region.ys(a)) {
      for (x in region.xs(a)) {
        val p = a.getRGB(x, y)
        val q = b.getRGB(x, y)
        for (shift in intArrayOf(16, 8, 0)) {
          sum += abs(((p shr shift) and 0xff) - ((q shr shift) and 0xff))
        }
        n += 3
      }
    }
    return sum.toDouble() / n
  }
}
