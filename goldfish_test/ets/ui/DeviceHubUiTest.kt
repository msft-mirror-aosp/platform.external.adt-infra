package com.android.tools.e2etests.ui

import com.android.tools.testlib.emu.findEmulator
import com.android.tradefed.config.Option
import com.android.tradefed.log.LogUtil.CLog
import com.android.tradefed.result.ByteArrayInputStreamSource
import com.android.tradefed.result.LogDataType
import com.android.tradefed.testtype.DeviceJUnit4ClassRunner
import com.android.tradefed.testtype.DeviceJUnit4ClassRunner.TestLogData
import com.android.tradefed.testtype.junit4.BaseHostJUnit4Test
import java.io.File
import java.net.ServerSocket
import java.net.URI
import java.net.http.HttpClient
import java.net.http.HttpRequest
import java.net.http.HttpResponse
import java.net.http.WebSocket
import java.nio.file.Files
import java.util.Base64
import java.util.concurrent.CompletableFuture
import java.util.concurrent.CompletionStage
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger
import org.json.JSONArray
import org.json.JSONObject
import org.junit.After
import org.junit.Assert
import org.junit.Before
import org.junit.Ignore
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

import java.nio.file.StandardCopyOption
import kotlin.random.Random

/**
 * End to end test of the Android Device Hub UI (Electron) connected to the emulator under test.
 *
 * The device hub is launched with Chromium's remote debugging enabled (and inside a hermetic Xvfb
 * virtual X11 display with ffmpeg video recording when `display_dir` is provided). Toolbar buttons
 * and touch screen gestures are driven via the Chrome DevTools Protocol (CDP), and their effects
 * are verified on the live emulator through adb.
 */
@RunWith(DeviceJUnit4ClassRunner::class)
class DeviceHubUiTest : BaseHostJUnit4Test() {
  @Option(
    name = "device_hub_path",
    description =
      "Path to the android-device-hub launcher. If empty, it is located via the emulator " +
        "discovery file (<launcher.dir>/android-device-hub/android-device-hub).",
  )
  private var mDeviceHubPath: String = ""

  @Option(
    name = "display_dir",
    description =
      "Path to the hermetic display directory containing launch_xvfb.sh, lib/, fonts/, and ffmpeg.",
  )
  private var mDisplayDir: String = ""

  @Option(name = "protocol", description = "Device hub emulator protocol: v1 (gRPC) or v2 (WebRTC)")
  private var mProtocol: String = "v1"

  @Option(
    name = "cdp_video",
    description =
      "Use CDP-piped screenshots for video recording even when Xvfb (x11grab) is active.",
  )
  private var mCdpVideo: Boolean = false

  @get:Rule val mLogs = TestLogData()

  private val TAG = "DeviceHubUiTest"
  private val mResolution = "1280x1024"
  private var mDisplay: String? = null
  private var mXvfb: Process? = null
  private var mXvfbLog: File? = null
  private var mFontConfigFile: File? = null
  private var mFontCacheDir: File? = null
  private var mFfmpeg: Process? = null
  private var mFfmpegLog: File? = null
  private var mVideoFile: File? = null
  @Volatile private var mCdpVideoRunning: Boolean = false
  private var mCdpVideoThread: Thread? = null
  private var mHub: Process? = null
  @Volatile private var mCdp: Cdp? = null
  private var mHubLog: File? = null

  @Before
  fun launchDeviceHub() {
    startXvfbIfNeeded()
    startVideoRecording()
    startDeviceHub(waitForStream = true)
  }

  @After
  fun tearDown() {
    runCatching { attachScreenshot("final") }
    stopDeviceHub()
    stopVideoRecording()
    stopXvfb()
  }

  @Test
  fun windowTitleShowsProtocol() {
    Assert.assertEquals(
      "Android Device Hub (Emu ${mProtocol.uppercase()} API)",
      cdp().eval("document.title"),
    )
  }

  @Test
  fun homeButtonGoesToLauncher() {
    getDevice().executeShellCommand("am start -W -a android.settings.SETTINGS")
    eventually("Settings in foreground") { resumedActivity().contains("settings", ignoreCase = true) }
    click("Home")
    eventually("launcher in foreground") { resumedActivity().contains("launcher", ignoreCase = true) }
  }

  @Test
  fun backButtonLeavesActivity() {
    getDevice().executeShellCommand("am start -W -a android.settings.SETTINGS")
    eventually("Settings in foreground") { resumedActivity().contains("settings", ignoreCase = true) }
    click("Back")
    eventually("Settings no longer in foreground") {
      !resumedActivity().contains("settings", ignoreCase = true)
    }
  }

  @Test
  fun volumeUpRaisesMusicVolume() {
    // Make sure there is headroom (max is 15); adb key events don't go through the device hub.
    repeat(4) {
      if (musicVolume() >= 13) getDevice().executeShellCommand("input keyevent KEYCODE_VOLUME_DOWN")
    }
    val before = musicVolume()
    Assert.assertTrue("Could not read music volume", before >= 0)
    // The first volume key press only shows the volume panel; the second adjusts the volume.
    click("Volume Up")
    Thread.sleep(500)
    click("Volume Up")
    eventually("music volume increased from $before") { musicVolume() > before }
  }

  @Test
  fun rotateButtonsChangeDisplayRotation() {
    getDevice().executeShellCommand("settings put system accelerometer_rotation 1")
    // The launcher is portrait-locked; put a rotatable activity in the foreground.
    getDevice().executeShellCommand("am start -W -a android.settings.SETTINGS")
    eventually("Settings in foreground") { resumedActivity().contains("settings", ignoreCase = true) }
    val before = rotation()
    click("Rotate Right")
    eventually("display rotated from $before") { rotation() != before }
    attachScreenshot("rotated")
    click("Rotate Left")
    eventually("display rotation restored to $before") { rotation() == before }
  }

  @Test
  fun touchScreenTapsAndSwipesOnDevice() {
    getDevice().executeShellCommand("settings put system pointer_location 1")
    try {
      getDevice().executeShellCommand("am start -W -a android.settings.SETTINGS")
      eventually("Settings in foreground") {
        resumedActivity().contains("settings", ignoreCase = true)
      }
      Thread.sleep(500)
      swipeScreen(0.5, 0.75, 0.5, 0.25)
      Thread.sleep(300)
      tapScreen(0.5, 0.5)
      attachScreenshot("after_touch")
      eventually("touch MotionEvents delivered to InputDispatcher") {
        val dumpsysInput = getDevice().executeShellCommand("dumpsys input")
        dumpsysInput.contains("MotionEvent") &&
          dumpsysInput.contains("action=DOWN") &&
          dumpsysInput.contains("action=UP")
      }
    } finally {
      runCatching { getDevice().executeShellCommand("settings put system pointer_location 0") }
    }
  }

  // TODO: Current android device hub is not handling this yet, enable it afterwards.
  @Ignore("Current android device hub is not handling this yet, enable it afterwards")
  @Test
  fun uiLaunchedBeforeEmulatorConnectsWhenEmulatorAppears() {
    val serial = getDevice().getSerialNumber()
    val discoveryFile = findDiscoveryFile(serial)
    Assert.assertNotNull("Could not locate emulator discovery file for $serial", discoveryFile)

    // Stop the default UI instance so we can launch a fresh UI before any emulator is discoverable.
    stopDeviceHub()

    val iniPath = discoveryFile!!.toPath()
    val backupPath = iniPath.resolveSibling("${iniPath.fileName}.bak")
    Files.move(iniPath, backupPath, StandardCopyOption.REPLACE_EXISTING)
    try {
      startDeviceHub(waitForStream = false)
      waitForUi(
        "document.querySelector('[data-testid=\"display-panel-0\"]') != null && " +
          "[...document.querySelectorAll('canvas,video')].every(e => e.classList.contains('hidden'))",
        20_000,
      )
      attachScreenshot("ui_waiting_for_emulator")
      Thread.sleep(1000)

      // Restore the emulator discovery file to simulate the emulator starting after the UI.
      Files.move(backupPath, iniPath, StandardCopyOption.REPLACE_EXISTING)
      waitForStream()
      attachScreenshot("ui_connected_after_emulator_appeared")

      // Verify toolbar interaction works after late discovery.
      getDevice().executeShellCommand("am start -W -a android.settings.SETTINGS")
      eventually("Settings in foreground") {
        resumedActivity().contains("settings", ignoreCase = true)
      }
      click("Home")
      eventually("launcher in foreground") {
        resumedActivity().contains("launcher", ignoreCase = true)
      }
    } finally {
      if (Files.exists(backupPath) && !Files.exists(iniPath)) {
        runCatching { Files.move(backupPath, iniPath, StandardCopyOption.REPLACE_EXISTING) }
      }
    }
  }

  // --- helpers ---------------------------------------------------------------------------------

  private fun cdp(): Cdp = mCdp!!

  private fun isLinux(): Boolean =
    System.getProperty("os.name").contains("Linux", ignoreCase = true)

  private fun isWindows(): Boolean =
    System.getProperty("os.name").contains("Win", ignoreCase = true)

  private fun startXvfbIfNeeded() {
    if (!isLinux()) return
    val existingDisplay = System.getenv("DISPLAY")?.takeIf { it.isNotEmpty() }
    if (existingDisplay != null) {
      mDisplay = existingDisplay
      CLog.i("%s: using existing DISPLAY=%s", TAG, mDisplay)
      return
    }
    val displayDir = mDisplayDir.takeIf { it.isNotEmpty() }?.let(::File)
    val launchScript = displayDir?.let { File(it, "launch_xvfb.sh") }
    if (launchScript == null || !launchScript.canExecute()) {
      return
    }

    var displayNum = 0
    for (attempt in 1..20) {
      val candidate = Random.nextInt(100, 1000)
      if (!File("/tmp/.X11-unix/X$candidate").exists() && !File("/tmp/.X$candidate-lock").exists()) {
        displayNum = candidate
        break
      }
    }
    Assert.assertTrue("Could not find a free X11 display number", displayNum > 0)
    val display = ":$displayNum"
    File("/tmp/xkboutput").mkdirs()
    val workspaceRoot =
      displayDir.parentFile?.parentFile?.parentFile?.parentFile?.takeIf {
        File(it, "tools/emulator/testlib/display").isDirectory
      } ?: displayDir
    mXvfbLog = Files.createTempFile("xvfb", ".log").toFile()
    val cmd = listOf(launchScript.absolutePath, display, workspaceRoot.absolutePath, "${mResolution}x24")
    CLog.i("%s: starting hermetic Xvfb: %s", TAG, cmd.joinToString(" "))
    mXvfb = ProcessBuilder(cmd).redirectErrorStream(true).redirectOutput(mXvfbLog).start()

    val socketFile = File("/tmp/.X11-unix/X$displayNum")
    val deadline = System.currentTimeMillis() + 15_000
    while (System.currentTimeMillis() < deadline && !socketFile.exists()) {
      if (!mXvfb!!.isAlive) {
        val logText = runCatching { mXvfbLog?.readText() }.getOrNull()
        Assert.fail("Xvfb exited prematurely with code ${mXvfb!!.exitValue()}. Log:\n$logText")
      }
      Thread.sleep(100)
    }
    Assert.assertTrue("Timed out waiting for Xvfb socket ${socketFile.path}", socketFile.exists())
    mDisplay = display

    val fontsDir = File(displayDir, "fonts/fonts_extended/truetype")
    if (fontsDir.isDirectory) {
      val cacheDir = Files.createTempDirectory("adh_fontcache").toFile()
      val fontConf = Files.createTempFile("adh_fonts", ".conf").toFile()
      fontConf.writeText(
        """
        <?xml version="1.0"?>
        <!DOCTYPE fontconfig SYSTEM "fonts.dtd">
        <fontconfig>
          <dir>${fontsDir.absolutePath}</dir>
          <cachedir>${cacheDir.absolutePath}</cachedir>
        </fontconfig>
        """.trimIndent()
      )
      mFontCacheDir = cacheDir
      mFontConfigFile = fontConf
    }
  }

  private fun stopXvfb() {
    mXvfb?.let { proc ->
      proc.descendants().forEach { it.destroy() }
      proc.destroy()
      if (!proc.waitFor(5, TimeUnit.SECONDS)) {
        proc.descendants().forEach { it.destroyForcibly() }
        proc.destroyForcibly()
      }
    }
    mXvfb = null
    mXvfbLog?.let {
      if (it.exists()) {
        mLogs.addTestLog("xvfb_log", LogDataType.TEXT, ByteArrayInputStreamSource(it.readBytes()))
        it.delete()
      }
    }
    mXvfbLog = null
    mFontConfigFile?.delete()
    mFontConfigFile = null
    mFontCacheDir?.deleteRecursively()
    mFontCacheDir = null
    mDisplay = null
  }

  private fun findFfmpegBinary(displayDir: File): File? {
    // The display dir ships binaries for every host; only consider the ones for this OS.
    val names =
      when {
        isWindows() -> listOf("ffmpeg_win64.exe", "ffmpeg.exe")
        isLinux() -> listOf("ffmpeg")
        else -> listOf("ffmpeg_mac64", "ffmpeg")
      }
    return names.map { File(displayDir, it) }.firstOrNull { it.isFile && it.canExecute() }
  }

  private fun startVideoRecording() {
    val displayDir = mDisplayDir.takeIf { it.isNotEmpty() }?.let(::File) ?: return
    val ffmpegBin = findFfmpegBinary(displayDir) ?: return
    mVideoFile = Files.createTempFile("device-hub-video", ".mp4").toFile()
    mFfmpegLog = Files.createTempFile("ffmpeg", ".log").toFile()

    val display = mDisplay
    if (mXvfb != null && display != null && !mCdpVideo) {
      val cmd =
        listOf(
          ffmpegBin.absolutePath,
          "-y",
          "-nostats",
          "-f",
          "x11grab",
          "-video_size",
          mResolution,
          "-framerate",
          "15",
          "-i",
          display,
          "-c:v",
          "libx264",
          "-pix_fmt",
          "yuv420p",
          "-movflags",
          "faststart",
          mVideoFile!!.absolutePath,
        )
      CLog.i("%s: starting ffmpeg x11grab recording: %s", TAG, cmd.joinToString(" "))
      mFfmpeg = ProcessBuilder(cmd).redirectErrorStream(true).redirectOutput(mFfmpegLog).start()
      return
    }

    val cmd =
      listOf(
        ffmpegBin.absolutePath,
        "-y",
        "-nostats",
        "-f",
        "image2pipe",
        "-framerate",
        "10",
        "-c:v",
        "mjpeg",
        "-i",
        "-",
        "-vf",
        "scale=trunc(iw/2)*2:trunc(ih/2)*2",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "faststart",
        mVideoFile!!.absolutePath,
      )
    CLog.i("%s: starting CDP-piped ffmpeg recording: %s", TAG, cmd.joinToString(" "))
    val proc = ProcessBuilder(cmd).redirectErrorStream(true).redirectOutput(mFfmpegLog).start()
    mFfmpeg = proc
    mCdpVideoRunning = true
    mCdpVideoThread =
      Thread(
          {
            val out = proc.outputStream
            while (mCdpVideoRunning && proc.isAlive) {
              val client = mCdp
              if (client != null) {
                runCatching {
                  val data =
                    client
                      .call(
                        "Page.captureScreenshot",
                        JSONObject().put("format", "jpeg").put("quality", 80),
                      )
                      .getJSONObject("result")
                      .getString("data")
                  val bytes = Base64.getDecoder().decode(data)
                  synchronized(out) {
                    out.write(bytes)
                    out.flush()
                  }
                }
              }
              runCatching { Thread.sleep(100) }
            }
          },
          "cdp-video-recorder",
        )
        .apply {
          isDaemon = true
          start()
        }
  }

  private fun stopVideoRecording() {
    val wasCdpVideo = mCdpVideoThread != null
    mCdpVideoRunning = false
    mCdpVideoThread?.let {
      it.interrupt()
      runCatching { it.join(3_000) }
    }
    mCdpVideoThread = null

    mFfmpeg?.let { proc ->
      if (proc.isAlive) {
        runCatching {
          if (wasCdpVideo) {
            proc.outputStream.close()
          } else {
            proc.outputStream.write("q\n".toByteArray())
            proc.outputStream.flush()
          }
        }
        if (!proc.waitFor(10, TimeUnit.SECONDS)) {
          proc.destroy()
          if (!proc.waitFor(5, TimeUnit.SECONDS)) proc.destroyForcibly()
        }
      }
    }
    mFfmpeg = null
    mVideoFile?.let {
      if (it.exists() && it.length() > 0) {
        mLogs.addTestLog(
          "device_hub_video",
          LogDataType.MP4,
          ByteArrayInputStreamSource(it.readBytes()),
        )
      }
      it.delete()
    }
    mVideoFile = null
    mFfmpegLog?.let {
      if (it.exists()) {
        mLogs.addTestLog("ffmpeg_log", LogDataType.TEXT, ByteArrayInputStreamSource(it.readBytes()))
        it.delete()
      }
    }
    mFfmpegLog = null
  }

  private fun startDeviceHub(waitForStream: Boolean) {
    val exe = locateDeviceHub()
    Assert.assertNotNull(
      "android-device-hub not found. Set --module-arg DeviceHubUiTest:set-option:device_hub_path:<path> " +
        "or make sure the emulator discovery file (XDG_RUNTIME_DIR/avd/running) has launcher.dir",
      exe,
    )

    val port = ServerSocket(0).use { it.localPort }
    val serial = getDevice().getSerialNumber()
    mHubLog = Files.createTempFile("device-hub", ".log").toFile()
    val cmd =
      listOf(
        exe!!.path,
        "--emulator",
        "--protocol=$mProtocol",
        "-s",
        serial,
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--remote-debugging-port=$port",
      )
    CLog.i("%s: launching %s", TAG, cmd.joinToString(" "))
    val pb = ProcessBuilder(cmd).redirectErrorStream(true).redirectOutput(mHubLog)
    val env = pb.environment()
    mDisplay?.let { env["DISPLAY"] = it }
    if (mDisplayDir.isNotEmpty()) {
      val libDir = File(mDisplayDir, "lib")
      if (libDir.isDirectory) {
        val existingLd = env["LD_LIBRARY_PATH"]?.takeIf { it.isNotEmpty() }
        env["LD_LIBRARY_PATH"] =
          listOfNotNull(libDir.absolutePath, existingLd).joinToString(":")
      }
    }
    mFontConfigFile?.let { env["FONTCONFIG_FILE"] = it.absolutePath }
    mHub = pb.start()

    mCdp = Cdp.connect(port)
    if (waitForStream) {
      waitForStream()
    }
  }

  private fun waitForStream() {
    // The canvas (v1) or video (v2) element becomes visible once frames are streaming.
    waitForUi(
      "[...document.querySelectorAll('canvas,video')].some(e => !e.classList.contains('hidden'))",
      60_000,
    )
  }

  private fun stopDeviceHub() {
    runCatching { mCdp?.close() }
    mCdp = null
    mHub?.let {
      it.destroy()
      if (!it.waitFor(10, TimeUnit.SECONDS)) it.destroyForcibly()
    }
    mHub = null
    mHubLog?.let {
      if (it.exists()) {
        mLogs.addTestLog(
          "device_hub_log",
          LogDataType.TEXT,
          ByteArrayInputStreamSource(it.readBytes()),
        )
        it.delete()
      }
    }
    mHubLog = null
  }

  private fun findExecutableIn(base: File): File? {
    if (base.isFile && base.canExecute()) return base
    val candidates =
      listOf(
        "android-device-hub",
        "android_device_hub.exe",
        "android-device-hub/android-device-hub",
        "android-device-hub/android_device_hub.exe",
        "Android Device Hub.app/Contents/MacOS/Android Device Hub",
      )
    return candidates.map { File(base, it) }.firstOrNull { it.isFile && it.canExecute() }
  }

  private fun locateDeviceHub(): File? {
    if (mDeviceHubPath.isNotEmpty()) {
      return findExecutableIn(File(mDeviceHubPath))
    }
    val serial = getDevice().getSerialNumber()
    val launcherDir =
      findEmulator(serial)?.discoveryIni?.get("launcher.dir") ?: launcherDirFromRunDir(serial)
    CLog.i("%s: launcher.dir=%s", TAG, launcherDir)
    return launcherDir?.let { findExecutableIn(File(it)) }
  }

  private fun findDiscoveryFile(serial: String): File? {
    findEmulator(serial)?.discoveryPath?.toFile()?.takeIf { it.exists() }?.let { return it }
    if (!isLinux()) return null
    val uid =
      runCatching { com.sun.security.auth.module.UnixSystem().getUid() }.getOrNull() ?: return null
    val port = serial.removePrefix("emulator-")
    return File("/run/user/$uid/avd/running")
      .listFiles { f -> f.name.startsWith("pid_") && f.name.endsWith(".ini") }
      ?.firstOrNull { f ->
        f.readLines()
          .filter { "=" in it }
          .associate { it.substringBefore("=") to it.substringAfter("=") }["port.serial"] == port
      }
  }

  /** XDG_RUNTIME_DIR is not always propagated to tradefed; scan /run/user/<uid> directly. */
  private fun launcherDirFromRunDir(serial: String): String? {
    val file = findDiscoveryFile(serial) ?: return null
    return file
      .readLines()
      .filter { "=" in it }
      .associate { it.substringBefore("=") to it.substringAfter("=") }["launcher.dir"]
  }

  private fun displayBounds(): JSONObject {
    val rect =
      cdp().eval(
        "(() => { const el = [...document.querySelectorAll('canvas,video')].find(e => !e.classList.contains('hidden'));" +
          " if (!el) return null; const r = el.getBoundingClientRect();" +
          " return JSON.stringify({x: r.x, y: r.y, width: r.width, height: r.height}); })()"
      )
    Assert.assertNotNull("Visible display canvas/video not found in device hub UI", rect)
    return JSONObject(rect as String)
  }

  private fun tapScreen(normX: Double, normY: Double) {
    val b = displayBounds()
    val x = b.getDouble("x") + b.getDouble("width") * normX
    val y = b.getDouble("y") + b.getDouble("height") * normY
    dispatchMouse("mouseMoved", x, y)
    dispatchMouse("mousePressed", x, y)
    Thread.sleep(60)
    dispatchMouse("mouseReleased", x, y)
  }

  private fun swipeScreen(
    startNormX: Double,
    startNormY: Double,
    endNormX: Double,
    endNormY: Double,
    steps: Int = 10,
  ) {
    val b = displayBounds()
    val startX = b.getDouble("x") + b.getDouble("width") * startNormX
    val startY = b.getDouble("y") + b.getDouble("height") * startNormY
    val endX = b.getDouble("x") + b.getDouble("width") * endNormX
    val endY = b.getDouble("y") + b.getDouble("height") * endNormY
    dispatchMouse("mouseMoved", startX, startY)
    dispatchMouse("mousePressed", startX, startY)
    for (i in 1..steps) {
      val t = i.toDouble() / steps
      val curX = startX + (endX - startX) * t
      val curY = startY + (endY - startY) * t
      Thread.sleep(25)
      dispatchMouse("mouseMoved", curX, curY, pressed = true)
    }
    Thread.sleep(50)
    dispatchMouse("mouseReleased", endX, endY)
  }

  private fun dispatchMouse(type: String, x: Double, y: Double, pressed: Boolean = false) {
    val isDown = type == "mousePressed" || (type == "mouseMoved" && pressed)
    cdp()
      .call(
        "Input.dispatchMouseEvent",
        JSONObject()
          .put("type", type)
          .put("x", x)
          .put("y", y)
          .put("button", if (type == "mouseMoved" && !pressed) "none" else "left")
          .put("buttons", if (isDown) 1 else 0)
          .put("clickCount", if (type == "mouseMoved") 0 else 1),
      )
  }

  /**
   * Clicks a toolbar button with real mouse input (press + release at its center). Hardware keys
   * (Home, Back, Volume, Power) react to mousedown/mouseup, while others (Rotate) react to click, so
   * a synthetic element.click() is not sufficient.
   */
  private fun click(label: String) {
    val rect =
      cdp().eval(
        "(() => { const b = document.querySelector('[aria-label=\"$label\"]'); if (!b) return null;" +
          " const r = b.getBoundingClientRect(); return JSON.stringify({x: r.x + r.width / 2, y: r.y + r.height / 2}); })()"
      )
    Assert.assertNotNull("Button '$label' not found in the device hub UI", rect)
    val pos = JSONObject(rect as String)
    val x = pos.getDouble("x")
    val y = pos.getDouble("y")
    dispatchMouse("mouseMoved", x, y)
    dispatchMouse("mousePressed", x, y)
    Thread.sleep(50)
    dispatchMouse("mouseReleased", x, y)
  }

  private fun resumedActivity(): String =
    getDevice()
      .executeShellCommand(
        "dumpsys activity activities | grep -m1 -E 'topResumedActivity|mResumedActivity'"
      )

  private fun rotation(): String =
    Regex("mCurrentRotation=(\\S+)")
      .find(getDevice().executeShellCommand("dumpsys window displays"))
      ?.groupValues
      ?.get(1) ?: ""

  private fun musicVolume(): Int {
    val out = getDevice().executeShellCommand("cmd media_session volume --stream 3 --get 2>&1")
    val v = Regex("volume is (\\d+)").find(out)?.groupValues?.get(1)?.toInt() ?: -1
    return v
  }

  private fun waitForUi(expr: String, timeoutMs: Long) {
    val end = System.currentTimeMillis() + timeoutMs
    while (System.currentTimeMillis() < end) {
      if (runCatching { cdp().eval(expr) == true }.getOrDefault(false)) return
      Thread.sleep(500)
    }
    runCatching { attachScreenshot("ui_timeout") }
    val status = runCatching { cdp().eval("document.body.innerText") }.getOrNull()
    Assert.fail("Device hub UI never satisfied `$expr`. Page text: $status")
  }

  private fun eventually(what: String, timeoutMs: Long = 10_000, cond: () -> Boolean) {
    val end = System.currentTimeMillis() + timeoutMs
    while (System.currentTimeMillis() < end) {
      if (runCatching(cond).getOrDefault(false)) return
      Thread.sleep(250)
    }
    runCatching { attachScreenshot("timeout") }
    Assert.fail("Timed out after ${timeoutMs}ms waiting for: $what")
  }

  private fun attachScreenshot(tag: String) {
    val data = cdp().call("Page.captureScreenshot").getJSONObject("result").getString("data")
    mLogs.addTestLog(
      "device_hub_$tag",
      LogDataType.PNG,
      ByteArrayInputStreamSource(Base64.getDecoder().decode(data)),
    )
  }
}

/** Minimal Chrome DevTools Protocol client using the JDK WebSocket. */
private class Cdp
private constructor(
  private val ws: WebSocket,
  private val pending: ConcurrentHashMap<Int, CompletableFuture<JSONObject>>,
) {
  private val ids = AtomicInteger()

  fun call(method: String, params: JSONObject = JSONObject()): JSONObject {
    val id = ids.incrementAndGet()
    val future = CompletableFuture<JSONObject>()
    pending[id] = future
    ws.sendText(JSONObject().put("id", id).put("method", method).put("params", params).toString(), true)
    val resp = future.get(10, TimeUnit.SECONDS)
    if (resp.has("error")) throw IllegalStateException("CDP $method failed: ${resp.get("error")}")
    return resp
  }

  fun eval(expr: String): Any? {
    val result =
      call("Runtime.evaluate", JSONObject().put("expression", expr).put("returnByValue", true))
        .getJSONObject("result")
        .getJSONObject("result")
    return if (result.has("value")) result.get("value") else null
  }

  fun close() {
    ws.sendClose(WebSocket.NORMAL_CLOSURE, "").get(5, TimeUnit.SECONDS)
  }

  companion object {
    fun connect(port: Int, timeoutMs: Long = 60_000): Cdp {
      val http = HttpClient.newHttpClient()
      val end = System.currentTimeMillis() + timeoutMs
      var wsUrl: String? = null
      while (wsUrl == null && System.currentTimeMillis() < end) {
        wsUrl =
          runCatching {
              val body =
                http
                  .send(
                    HttpRequest.newBuilder(URI("http://127.0.0.1:$port/json/list")).build(),
                    HttpResponse.BodyHandlers.ofString(),
                  )
                  .body()
              val targets = JSONArray(body)
              (0 until targets.length())
                .map { targets.getJSONObject(it) }
                .first { it.getString("type") == "page" }
                .getString("webSocketDebuggerUrl")
            }
            .getOrNull()
        if (wsUrl == null) Thread.sleep(500)
      }
      requireNotNull(wsUrl) { "CDP endpoint on port $port never came up" }

      val pending = ConcurrentHashMap<Int, CompletableFuture<JSONObject>>()
      val listener =
        object : WebSocket.Listener {
          private val buf = StringBuilder()

          override fun onText(w: WebSocket, data: CharSequence, last: Boolean): CompletionStage<*>? {
            buf.append(data)
            if (last) {
              val msg = JSONObject(buf.toString())
              buf.setLength(0)
              if (msg.has("id")) pending.remove(msg.getInt("id"))?.complete(msg)
            }
            w.request(1)
            return null
          }
        }
      val ws =
        http
          .newWebSocketBuilder()
          .buildAsync(URI(wsUrl), listener)
          .get(10, TimeUnit.SECONDS)
      return Cdp(ws, pending)
    }
  }
}
