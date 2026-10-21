package com.android.tools.e2etests.foldable

import com.android.emulator.control.EmulatorControllerGrpc
import com.android.emulator.control.Image
import com.android.emulator.control.ImageFormat
import com.android.emulator.control.ParameterValue
import com.android.emulator.control.PhysicalModelValue
import com.android.tools.e2etests.grpc.getHostGrpcChannel
import com.android.tools.testlib.emu.findEmulator
import com.android.tradefed.config.Option
import com.android.tradefed.log.LogUtil.CLog
import com.android.tradefed.result.ByteArrayInputStreamSource
import com.android.tradefed.result.LogDataType
import com.android.tradefed.testtype.DeviceJUnit4ClassRunner
import com.android.tradefed.testtype.DeviceJUnit4ClassRunner.TestLogData
import com.android.tradefed.testtype.junit4.BaseHostJUnit4Test
import io.grpc.Grpc
import io.grpc.InsecureChannelCredentials
import io.grpc.ManagedChannel
import java.awt.Color
import java.awt.image.BufferedImage
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.io.File
import java.nio.file.Files
import java.util.concurrent.TimeUnit
import javax.imageio.ImageIO
import kotlin.math.abs
import kotlin.math.sqrt
import org.junit.After
import org.junit.Assert
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

private const val UNFOLDED_ANGLE = 180f
private const val FOLDED_ANGLE = 15f
private const val ANGLE_TOLERANCE = 1.0f
private const val FOLDED_WIDTH = 1080
private const val UNFOLDED_MIN_WIDTH = 1800
private const val VIDEO_CANVAS_WIDTH = 1038
private const val VIDEO_CANVAS_HEIGHT = 1182

/**
 * End-to-end host test for embedded foldable emulator display rendering (`-qt-hide-window`).
 *
 * Verifies that host gRPC screenshots (`PNG` and `RGBA8888`) and guest screenshots render
 * properly across:
 * 1. Unfolded inner display (`hinge_angle0 = 180°`).
 * 2. Folding to the outer display (`hinge_angle0 = 15°`), ensuring the outer display does not
 *    inherit the powered-off inner display's zero color transform (b/571840024).
 * 3. Repeated unfold (`180°`) and re-fold (`15°`) transitions.
 * 4. Display power off (`KEYCODE_SLEEP`) and power on (`KEYCODE_WAKEUP`) while folded (`15°`),
 *    ensuring HWC display 1 maps to host display 6 in `rcSetDisplayPowerMode` /
 *    `rcGetDisplayPowerMode` and 4-byte `RGBA8888` (`GL_RGBA`) screenshots apply the power-off
 *    color transform across the full frame without stride corruption (b/571840024).
 * 5. Unfolding back to the inner display (`180°`) after the folded power cycle.
 */
@RunWith(DeviceJUnit4ClassRunner::class)
class FoldableDisplayTest : BaseHostJUnit4Test() {
  @get:Rule val mLogs = TestLogData()

  @Option(
    name = "display_dir",
    description = "Directory containing ffmpeg for recording a full-test MP4 video",
  )
  private var mDisplayDir: String = ""

  private val TAG: String = javaClass.simpleName
  private val logPrefix: String = "foldable_display"
  private var mChannel: ManagedChannel? = null
  private var mFfmpeg: Process? = null
  private var mVideoFile: File? = null
  private var mFfmpegLog: File? = null
  private var mVideoEncoder: String? = null
  @Volatile private var mVideoRunning: Boolean = false
  private var mVideoThread: Thread? = null

  @Before
  fun setUp() {
    mChannel = openGrpcChannel(getDevice().getSerialNumber())
    startVideoRecording()
    clearCrashLog()
    // Disable Always-On Display so KEYCODE_SLEEP transitions display power mode to OFF (0).
    shell("settings put secure doze_always_on 0")
    // Keep display awake across fold transitions and disable window/transition animations
    // (keep animator_duration_scale=1 so DisplayPowerController's ColorFade off-animation draws a
    // black frame before SurfaceFlinger powers off the display).
    shell("settings put system fold_lock_behavior_setting stay_awake_on_fold_key")
    shell("settings put global window_animation_scale 0")
    shell("settings put global transition_animation_scale 0")
    shell("settings put global animator_duration_scale 1")
    shell("locksettings set-disabled true")
    wakeAndUnlock()
    setHingeAngle(UNFOLDED_ANGLE)
  }

  @After
  fun tearDown() {
    runCatching {
      setHingeAngle(UNFOLDED_ANGLE)
      wakeAndUnlock()
      shell("svc power stayon false")
    }
    stopVideoRecording()
    mChannel?.let { ch ->
      runCatching {
        ch.shutdown().awaitTermination(5, TimeUnit.SECONDS)
        if (!ch.isTerminated) ch.shutdownNow()
      }
    }
    mChannel = null
  }

  @Test
  fun foldUnfoldAndPowerToggleRendersDisplay() {
    // 1. Start unfolded (180 degrees) with Settings in the foreground and verify inner display.
    waitForDisplayRendered("step1_unfolded", expectedFolded = false)
    verifyRenderedScreenshots("step1_unfolded", expectedFolded = false)

    // 2. Fold the device (15 degrees) and verify the outer display renders and is not black.
    CLog.i("%s: Folding device to %.1f degrees...", TAG, FOLDED_ANGLE)
    setHingeAngle(FOLDED_ANGLE)
    waitForDisplayRendered("step2_folded", expectedFolded = true)
    verifyRenderedScreenshots("step2_folded", expectedFolded = true)

    // 3. Unfold (180 degrees) and re-fold (15 degrees) to verify repeated display transitions.
    CLog.i("%s: Unfolding device to %.1f degrees...", TAG, UNFOLDED_ANGLE)
    setHingeAngle(UNFOLDED_ANGLE)
    waitForDisplayRendered("step3_unfolded", expectedFolded = false)
    verifyRenderedScreenshots("step3_unfolded", expectedFolded = false)

    CLog.i("%s: Re-folding device to %.1f degrees...", TAG, FOLDED_ANGLE)
    setHingeAngle(FOLDED_ANGLE)
    waitForDisplayRendered("step3_refolded", expectedFolded = true)
    verifyRenderedScreenshots("step3_refolded", expectedFolded = true)

    // 4. Turn screen OFF (KEYCODE_SLEEP) while folded and verify host PNG & RGBA8888 are black
    // across the full frame (testing rcSetDisplayPowerMode HWC 1 -> host 6 and 4-byte GL_RGBA
    // color transform stride), then wake up (KEYCODE_WAKEUP) and verify outer display recovers.
    CLog.i("%s: Putting folded display to sleep (KEYCODE_SLEEP)...", TAG)
    shell("svc power stayon false")
    shell("input keyevent KEYCODE_SLEEP")
    var sleepPollCount = 0
    eventually("folded outer display turns black after KEYCODE_SLEEP", timeoutMs = 15_000) {
      sleepPollCount++
      val (_, pngImg) = hostPngScreenshot("step4_folded_sleep_poll", attach = false)
      if (regionLuma(pngImg, Region.FULL).isBlack()) {
        true
      } else {
        if (sleepPollCount % 10 == 0) {
          shell("input keyevent KEYCODE_WAKEUP")
          Thread.sleep(300)
          shell("input keyevent KEYCODE_SLEEP")
        }
        false
      }
    }
    val (sleepPngProto, sleepPngImg) = hostPngScreenshot("step4_folded_sleep_png")
    assertDisplayDimensions("step4_folded_sleep_png", sleepPngProto, expectedFolded = true)
    assertBlack("step4_folded_sleep_png", sleepPngImg, Region.FULL)

    val (sleepRgbaProto, sleepRgbaImg) = hostRgbaScreenshot("step4_folded_sleep_rgba")
    assertDisplayDimensions("step4_folded_sleep_rgba", sleepRgbaProto, expectedFolded = true)
    assertBlack("step4_folded_sleep_rgba", sleepRgbaImg, Region.FULL)
    assertRgbaBlackWithOpaqueAlpha("step4_folded_sleep_rgba", sleepRgbaProto)

    CLog.i("%s: Waking folded display back up (KEYCODE_WAKEUP)...", TAG)
    wakeAndUnlock()
    waitForDisplayRendered("step4_folded_wakeup", expectedFolded = true)
    verifyRenderedScreenshots("step4_folded_wakeup", expectedFolded = true)

    // 5. Unfold back to 180 degrees and verify the inner display renders cleanly.
    CLog.i("%s: Unfolding device to %.1f degrees after folded power cycle...", TAG, UNFOLDED_ANGLE)
    setHingeAngle(UNFOLDED_ANGLE)
    waitForDisplayRendered("step5_unfolded_final", expectedFolded = false)
    verifyRenderedScreenshots("step5_unfolded_final", expectedFolded = false)

    assertNoCrash("com.android.settings")
  }

  // --- full-test MP4 video recording ------------------------------------------------------------

  private fun findFfmpegBinary(): File? {
    val osName = System.getProperty("os.name", "")
    val names =
      when {
        osName.contains("Win", ignoreCase = true) -> listOf("ffmpeg_win64.exe", "ffmpeg.exe")
        osName.contains("Linux", ignoreCase = true) -> listOf("ffmpeg")
        else -> listOf("ffmpeg_mac64", "ffmpeg")
      }
    val candidates = mutableListOf<File>()
    if (mDisplayDir.isNotEmpty()) {
      names.forEach { candidates.add(File(mDisplayDir, it)) }
    }
    System.getenv("PATH")
      ?.split(File.pathSeparator)
      ?.filter { it.isNotEmpty() }
      ?.forEach { dir -> names.forEach { candidates.add(File(dir, it)) } }
    candidates.add(File("/usr/bin/ffmpeg"))
    return candidates.firstOrNull { it.isFile && it.canExecute() }
  }

  private fun videoEncoder(ffmpegPath: String): String {
    mVideoEncoder?.let { return it }
    val enc =
      runCatching {
          val proc =
            ProcessBuilder(ffmpegPath, "-hide_banner", "-encoders")
              .redirectErrorStream(true)
              .start()
          val out = proc.inputStream.bufferedReader().readText()
          proc.waitFor(5, TimeUnit.SECONDS)
          when {
            out.contains("libx264") -> "libx264"
            out.contains("libopenh264") -> "libopenh264"
            else -> "mpeg4"
          }
        }
        .getOrDefault("mpeg4")
    mVideoEncoder = enc
    return enc
  }

  private fun startVideoRecording() {
    val ffmpegBin = findFfmpegBinary()
    if (ffmpegBin == null) {
      CLog.w("%s: ffmpeg binary not found (display_dir=%s), skipping video recording", TAG, mDisplayDir)
      return
    }
    val videoFile = Files.createTempFile("${logPrefix}_video_", ".mp4").toFile()
    val logFile = Files.createTempFile("ffmpeg_log_", ".txt").toFile()
    val encoder = videoEncoder(ffmpegBin.absolutePath)
    val cmd =
      mutableListOf(
        ffmpegBin.absolutePath,
        "-y",
        "-nostats",
        "-f",
        "image2pipe",
        "-framerate",
        "5",
        "-c:v",
        "png",
        "-i",
        "-",
        "-threads",
        "2",
        "-c:v",
        encoder,
      )
    if (encoder == "libx264") {
      cmd.addAll(
        listOf(
          "-preset",
          "ultrafast",
          "-crf",
          "23",
          "-x264-params",
          "threads=2:lookahead_threads=1",
        )
      )
    } else if (encoder == "mpeg4") {
      cmd.addAll(listOf("-q:v", "5"))
    }
    cmd.addAll(listOf("-pix_fmt", "yuv420p", "-movflags", "faststart", videoFile.absolutePath))
    CLog.i("%s: Starting video recording with command: %s", TAG, cmd.joinToString(" "))
    val proc = ProcessBuilder(cmd).redirectErrorStream(true).redirectOutput(logFile).start()
    mFfmpeg = proc
    mVideoFile = videoFile
    mFfmpegLog = logFile
    mVideoRunning = true
    mVideoThread =
      Thread(
          {
            val out = proc.outputStream
            val fmt =
              ImageFormat.newBuilder().setFormat(ImageFormat.ImgFormat.PNG).setDisplay(0).build()
            while (mVideoRunning) {
              val startMs = System.currentTimeMillis()
              runCatching {
                val proto =
                  EmulatorControllerGrpc.newBlockingStub(mChannel!!)
                    .withMaxInboundMessageSize(64 * 1024 * 1024)
                    .withDeadlineAfter(5, TimeUnit.SECONDS)
                    .getScreenshot(fmt)
                val rawBytes = proto.image.toByteArray()
                if (rawBytes.isNotEmpty()) {
                  val src = ImageIO.read(ByteArrayInputStream(rawBytes))
                  if (src != null) {
                    val canvas =
                      BufferedImage(
                        VIDEO_CANVAS_WIDTH,
                        VIDEO_CANVAS_HEIGHT,
                        BufferedImage.TYPE_INT_RGB,
                      )
                    val g = canvas.createGraphics()
                    g.color = Color(32, 32, 32)
                    g.fillRect(0, 0, VIDEO_CANVAS_WIDTH, VIDEO_CANVAS_HEIGHT)
                    val drawW = (src.width / 2).coerceIn(1, VIDEO_CANVAS_WIDTH)
                    val drawH = (src.height / 2).coerceIn(1, VIDEO_CANVAS_HEIGHT)
                    val x = ((VIDEO_CANVAS_WIDTH - drawW) / 2).coerceAtLeast(0)
                    val y = ((VIDEO_CANVAS_HEIGHT - drawH) / 2).coerceAtLeast(0)
                    g.drawImage(src, x, y, drawW, drawH, null)
                    g.dispose()
                    val pngBuf = ByteArrayOutputStream()
                    ImageIO.write(canvas, "PNG", pngBuf)
                    out.write(pngBuf.toByteArray())
                    out.flush()
                  }
                }
              }
              val sleepMs = 200L - (System.currentTimeMillis() - startMs)
              if (sleepMs > 10L && mVideoRunning) {
                runCatching { Thread.sleep(sleepMs) }
              }
            }
          },
          "foldable-video-recorder",
        )
        .apply {
          isDaemon = true
          start()
        }
  }

  private fun stopVideoRecording() {
    mVideoRunning = false
    mVideoThread?.let { t ->
      runCatching { t.join(5_000) }
    }
    mVideoThread = null
    mFfmpeg?.let { proc ->
      runCatching { proc.outputStream.close() }
      runCatching {
        if (!proc.waitFor(15, TimeUnit.SECONDS)) {
          proc.destroyForcibly()
        }
      }
    }
    mFfmpeg = null
    mFfmpegLog?.let { f ->
      if (f.exists()) {
        mLogs.addTestLog("ffmpeg_log", LogDataType.TEXT, ByteArrayInputStreamSource(f.readBytes()))
        f.delete()
      }
    }
    mFfmpegLog = null
    mVideoFile?.let { f ->
      if (f.exists() && f.length() > 0) {
        mLogs.addTestLog(
          "${logPrefix}_video",
          LogDataType.MP4,
          ByteArrayInputStreamSource(f.readBytes()),
        )
      }
      f.delete()
    }
    mVideoFile = null
  }

  // --- foldable & gRPC helpers ------------------------------------------------------------------

  private fun stub(): EmulatorControllerGrpc.EmulatorControllerBlockingStub =
    EmulatorControllerGrpc.newBlockingStub(mChannel!!)
      .withMaxInboundMessageSize(64 * 1024 * 1024)
      .withDeadlineAfter(30, TimeUnit.SECONDS)

  private fun openGrpcChannel(serial: String): ManagedChannel {
    findEmulator(serial)?.let { return getHostGrpcChannel(it) }
    val port = grpcPortFromDiscovery(serial)
    Assert.assertNotNull("Could not find gRPC port in discovery file for $serial", port)
    return Grpc.newChannelBuilder("localhost:$port", InsecureChannelCredentials.create())
      .maxInboundMessageSize(64 * 1024 * 1024)
      .build()
  }

  /** Fallback scan of emulator discovery directories on Linux, macOS, and Windows. */
  private fun grpcPortFromDiscovery(serial: String): String? {
    val consolePort = serial.removePrefix("emulator-")
    val dirs = mutableListOf<File>()
    System.getenv("XDG_RUNTIME_DIR")?.takeIf { it.isNotEmpty() }?.let { dirs.add(File(it, "avd/running")) }
    runCatching { com.sun.security.auth.module.UnixSystem().getUid() }
      .getOrNull()
      ?.let { dirs.add(File("/run/user/$it/avd/running")) }
    System.getenv("LOCALAPPDATA")?.takeIf { it.isNotEmpty() }?.let {
      dirs.add(File(it, "Temp/avd/running"))
    }
    System.getProperty("user.home")?.takeIf { it.isNotEmpty() }?.let { home ->
      dirs.add(File(home, "Library/Caches/TemporaryItems/avd/running"))
      dirs.add(File(home, ".android/avd/running"))
      dirs.add(File(home, "AppData/Local/Temp/avd/running"))
    }
    for (dir in dirs) {
      val files = dir.listFiles { f -> f.name.startsWith("pid_") && f.name.endsWith(".ini") } ?: continue
      for (f in files) {
        val kv =
          f.readLines()
            .filter { "=" in it && !it.trim().startsWith(";") }
            .associate { it.substringBefore("=").trim() to it.substringAfter("=").trim() }
        if (kv["port.serial"] == consolePort && !kv["grpc.port"].isNullOrEmpty()) {
          return kv["grpc.port"]
        }
      }
    }
    return null
  }

  private fun setHingeAngle(degrees: Float) {
    stub()
      .setPhysicalModel(
        PhysicalModelValue.newBuilder()
          .setTarget(PhysicalModelValue.PhysicalType.HINGE_ANGLE0)
          .setValue(ParameterValue.newBuilder().addData(degrees))
          .build()
      )
    eventually("hinge_angle0 == $degrees") {
      val resp =
        stub()
          .getPhysicalModel(
            PhysicalModelValue.newBuilder()
              .setTarget(PhysicalModelValue.PhysicalType.HINGE_ANGLE0)
              .build()
          )
      resp.value.dataCount >= 1 && abs(resp.value.getData(0) - degrees) <= ANGLE_TOLERANCE
    }
  }

  private fun waitForDisplayRendered(stage: String, expectedFolded: Boolean) {
    val label = if (expectedFolded) "folded outer" else "unfolded inner"
    eventually("$stage $label display format", timeoutMs = 15_000) {
      val (proto, _) = hostPngScreenshot("${stage}_fmt_poll", attach = false)
      if (expectedFolded) isFoldedFormat(proto) else isUnfoldedFormat(proto)
    }
    ensureSettingsInForeground()
    var consecutiveRendered = 0
    eventually("$stage $label display rendered", timeoutMs = 20_000) {
      val (proto, img) = hostPngScreenshot("${stage}_poll", attach = false)
      val formatOk = if (expectedFolded) isFoldedFormat(proto) else isUnfoldedFormat(proto)
      if (formatOk && centerLuma(img).looksRendered()) {
        consecutiveRendered++
        consecutiveRendered >= 2
      } else {
        consecutiveRendered = 0
        shell("input keyevent KEYCODE_WAKEUP")
        shell("wm dismiss-keyguard")
        false
      }
    }
  }

  private fun isUnfoldedFormat(image: Image): Boolean {
    val fmt = image.format
    return fmt.foldedDisplay.width == 0 &&
      fmt.foldedDisplay.height == 0 &&
      fmt.width >= UNFOLDED_MIN_WIDTH &&
      fmt.height > 0
  }

  private fun isFoldedFormat(image: Image): Boolean {
    val fmt = image.format
    return fmt.foldedDisplay.width == FOLDED_WIDTH &&
      fmt.foldedDisplay.height > 0 &&
      fmt.width == FOLDED_WIDTH &&
      fmt.height == fmt.foldedDisplay.height
  }

  private fun assertDisplayDimensions(what: String, image: Image, expectedFolded: Boolean) {
    val fmt = image.format
    if (expectedFolded) {
      Assert.assertTrue(
        "$what expected folded display (${FOLDED_WIDTH}x<h>), got ${fmt.width}x${fmt.height} " +
          "(foldedDisplay=${fmt.foldedDisplay.width}x${fmt.foldedDisplay.height})",
        isFoldedFormat(image),
      )
    } else {
      Assert.assertTrue(
        "$what expected unfolded display (>=${UNFOLDED_MIN_WIDTH}x<h>), got ${fmt.width}x${fmt.height} " +
          "(foldedDisplay=${fmt.foldedDisplay.width}x${fmt.foldedDisplay.height})",
        isUnfoldedFormat(image),
      )
    }
  }

  private fun verifyRenderedScreenshots(stage: String, expectedFolded: Boolean) {
    val (pngProto, pngImg) = hostPngScreenshot("${stage}_host_png")
    assertDisplayDimensions("${stage}_host_png", pngProto, expectedFolded)
    assertNotBlack("${stage}_host_png", pngImg)

    val (rgbaProto, rgbaImg) = hostRgbaScreenshot("${stage}_host_rgba")
    assertDisplayDimensions("${stage}_host_rgba", rgbaProto, expectedFolded)
    assertNotBlack("${stage}_host_rgba", rgbaImg)

    val guestImg = deviceScreenshot("${stage}_guest")
    assertNotBlack("${stage}_guest", guestImg)
  }

  // --- device & shell helpers -------------------------------------------------------------------

  private fun shell(cmd: String): String = getDevice().executeShellCommand(cmd) ?: ""

  private fun wakeAndUnlock() {
    shell("input keyevent KEYCODE_WAKEUP")
    shell("wm dismiss-keyguard")
    shell("svc power stayon true")
  }

  private fun resumedActivity(): String =
    shell("dumpsys activity activities | grep -m1 -E 'topResumedActivity|mResumedActivity'")

  private fun ensureSettingsInForeground() {
    wakeAndUnlock()
    if (!resumedActivity().contains("settings", ignoreCase = true)) {
      shell("am start -W -a android.settings.SETTINGS")
    }
    eventually("Settings in foreground", timeoutMs = 15_000) {
      val resumed = resumedActivity().contains("settings", ignoreCase = true)
      if (!resumed) {
        wakeAndUnlock()
        shell("am start -W -a android.settings.SETTINGS")
      }
      resumed
    }
  }

  private fun clearCrashLog() {
    shell("logcat -b crash -c")
  }

  private fun assertNoCrash(pkg: String) {
    val crashes = shell("logcat -b crash -d").lines().filter { it.contains(pkg) }
    Assert.assertTrue("$pkg crashed:\n${crashes.joinToString("\n")}", crashes.isEmpty())
  }

  private fun eventually(what: String, timeoutMs: Long = 10_000, cond: () -> Boolean) {
    val end = System.currentTimeMillis() + timeoutMs
    while (System.currentTimeMillis() < end) {
      if (runCatching(cond).getOrDefault(false)) return
      Thread.sleep(250)
    }
    runCatching { hostPngScreenshot("timeout_${what.replace(Regex("\\W+"), "_")}") }
    Assert.fail("Timed out after ${timeoutMs}ms waiting for: $what")
  }

  // --- screenshots & image analysis (following //ets/ui/RenderingUiTestBase.kt) -----------------

  private fun hostPngScreenshot(tag: String, attach: Boolean = true): Pair<Image, BufferedImage> {
    val resp =
      stub().getScreenshot(ImageFormat.newBuilder().setFormat(ImageFormat.ImgFormat.PNG).build())
    val bytes = resp.image.toByteArray()
    if (attach) attachPng(tag, bytes)
    return resp to decodePng(bytes, tag)
  }

  private fun hostRgbaScreenshot(tag: String, attach: Boolean = true): Pair<Image, BufferedImage> {
    val resp =
      stub()
        .getScreenshot(ImageFormat.newBuilder().setFormat(ImageFormat.ImgFormat.RGBA8888).build())
    val img = rgbaToBufferedImage(resp)
    if (attach) {
      val out = ByteArrayOutputStream()
      ImageIO.write(img, "PNG", out)
      attachPng(tag, out.toByteArray())
    }
    return resp to img
  }

  private fun deviceScreenshot(tag: String): BufferedImage {
    val bytes = getDevice().getScreenshot().createInputStream().use { it.readBytes() }
    attachPng(tag, bytes)
    return decodePng(bytes, tag)
  }

  private fun attachPng(tag: String, png: ByteArray) {
    mLogs.addTestLog("${logPrefix}_$tag", LogDataType.PNG, ByteArrayInputStreamSource(png))
  }

  private fun decodePng(png: ByteArray, what: String): BufferedImage {
    val image = ImageIO.read(ByteArrayInputStream(png))
    Assert.assertNotNull("Could not decode the $what screenshot", image)
    return image!!
  }

  private fun rgbaToBufferedImage(image: Image): BufferedImage {
    val w = image.format.width
    val h = image.format.height
    val raw = image.image
    Assert.assertEquals("RGBA8888 byte count mismatch for ${w}x${h}", 4 * w * h, raw.size())
    val buffered = BufferedImage(w, h, BufferedImage.TYPE_INT_ARGB)
    var idx = 0
    for (y in 0 until h) {
      for (x in 0 until w) {
        val r = raw.byteAt(idx).toInt() and 0xff
        val g = raw.byteAt(idx + 1).toInt() and 0xff
        val b = raw.byteAt(idx + 2).toInt() and 0xff
        val a = raw.byteAt(idx + 3).toInt() and 0xff
        buffered.setRGB(x, y, (a shl 24) or (r shl 16) or (g shl 8) or b)
        idx += 4
      }
    }
    return buffered
  }

  /**
   * Verifies that a powered-off RGBA8888 screenshot has R=0, G=0, B=0 and opaque A=255 across the
   * entire buffer (including the bottom quarter of rows, catching 3-byte vs 4-byte pixel stride
   * bugs in ColorBufferGl::readPixelsScaled).
   */
  private fun assertRgbaBlackWithOpaqueAlpha(what: String, image: Image) {
    val w = image.format.width
    val h = image.format.height
    val raw = image.image
    for (y in 0 until h step 4) {
      for (x in 0 until w step 4) {
        val idx = (y * w + x) * 4
        val r = raw.byteAt(idx).toInt() and 0xff
        val g = raw.byteAt(idx + 1).toInt() and 0xff
        val b = raw.byteAt(idx + 2).toInt() and 0xff
        val a = raw.byteAt(idx + 3).toInt() and 0xff
        Assert.assertTrue(
          "$what pixel ($x, $y) expected RGBA=(0,0,0,255), got ($r,$g,$b,$a)",
          r == 0 && g == 0 && b == 0 && a == 255,
        )
      }
    }
  }

  data class Luma(
    val mean: Double,
    val stdDev: Double,
    val darkFraction: Double,
    val colors: Int,
  ) {
    /** Not black, not a single flat color, and with some color detail. */
    fun looksRendered(): Boolean = mean >= 20 && darkFraction <= 0.9 && stdDev >= 6 && colors >= 16

    /** Completely black display (e.g. when display power mode is OFF). */
    fun isBlack(): Boolean = mean < 1.0 && darkFraction >= 0.999 && colors <= 1
  }

  data class Region(val left: Double, val top: Double, val right: Double, val bottom: Double) {
    fun xs(image: BufferedImage): IntProgression =
      (image.width * left).toInt() until (image.width * right).toInt() step 2

    fun ys(image: BufferedImage): IntProgression =
      (image.height * top).toInt() until (image.height * bottom).toInt() step 2

    companion object {
      val CENTER = Region(0.25, 0.25, 0.75, 0.75)
      val FULL = Region(0.05, 0.05, 0.95, 0.95)
    }
  }

  private fun centerLuma(image: BufferedImage): Luma = regionLuma(image, Region.CENTER)

  private fun regionLuma(image: BufferedImage, region: Region): Luma {
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

  private fun assertNotBlack(
    what: String,
    image: BufferedImage,
    region: Region = Region.CENTER,
  ) {
    val luma = regionLuma(image, region)
    CLog.i(
      "%s: %s (%dx%d): mean luma %.1f, std dev %.1f, %.0f%% dark, %d colors",
      TAG,
      what,
      image.width,
      image.height,
      luma.mean,
      luma.stdDev,
      luma.darkFraction * 100,
      luma.colors,
    )
    Assert.assertTrue("$what is black or blank: $luma", luma.looksRendered())
  }

  private fun assertBlack(
    what: String,
    image: BufferedImage,
    region: Region = Region.FULL,
  ) {
    val luma = regionLuma(image, region)
    CLog.i(
      "%s: %s (%dx%d): mean luma %.1f, std dev %.1f, %.0f%% dark, %d colors",
      TAG,
      what,
      image.width,
      image.height,
      luma.mean,
      luma.stdDev,
      luma.darkFraction * 100,
      luma.colors,
    )
    Assert.assertTrue("$what expected black screen when display is OFF, got: $luma", luma.isBlack())
  }
}
