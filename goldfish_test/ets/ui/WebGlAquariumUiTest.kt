package com.android.tools.e2etests.ui

import com.android.tradefed.config.Option
import com.android.tradefed.log.LogUtil.CLog
import com.android.tradefed.testtype.DeviceJUnit4ClassRunner
import java.net.ServerSocket
import java.util.Base64
import org.json.JSONObject
import org.junit.After
import org.junit.Assert
import org.junit.Test
import org.junit.runner.RunWith

private const val DEFAULT_AQUARIUM_URL = "https://webglsamples.org/aquarium/aquarium.html?numFish=100"
private const val CHROME_DEVTOOLS_SOCKET = "chrome_devtools_remote"
private const val CHROME_COMMAND_LINE_FILE = "/data/local/tmp/chrome-command-line"
private const val CHROME_PID = "chrome_pid"
private const val PAGE_ID = "page_id"
private const val CHROME_FLAGS =
  "--disable-fre --no-default-browser-check --no-first-run --ignore-gpu-blocklist"

/**
 * Installs a probe into the aquarium page, once per page load: counts `gl.drawElements` calls (the
 * aquarium issues one per fish), animation frames, and `webglcontextlost` events, and tags the page
 * with a random id so a reload (renderer or GPU process crash) is detected across snapshot loads.
 */
private val INSTALL_PROBE_JS =
  """
  (() => {
    if (typeof gl === 'undefined' || !gl || typeof canvas === 'undefined' || !canvas) return null;
    if (!window.__etsProbe) {
      const p = {id: Math.random().toString(36).slice(2), draws: 0, frames: 0, contextLost: 0};
      const drawElements = gl.drawElements;
      gl.drawElements = function() { p.draws++; return drawElements.apply(this, arguments); };
      canvas.addEventListener('webglcontextlost', () => { p.contextLost++; });
      const tick = () => { p.frames++; requestAnimationFrame(tick); };
      requestAnimationFrame(tick);
      window.__etsProbe = p;
    }
    return window.__etsProbe.id;
  })()
  """
    .trimIndent()

/** Rendering state of the aquarium page as JSON (null until the aquarium has initialized). */
private val AQUARIUM_STATE_JS =
  """
  (() => {
    if (typeof gl === 'undefined' || !gl || typeof g_fishTable === 'undefined') return null;
    const setting = g.globals.fishSetting;
    const p = window.__etsProbe;
    return JSON.stringify({
      fish: g_fishTable.reduce((n, f) => n + ((f.num && f.num[setting]) || 0), 0),
      fishLoaded: g_fishTable.every(f => {
        const s = g_scenes[f.name];
        return !!s && !!s.loaded && !s.bad;
      }),
      contextLost: gl.isContextLost(),
      fps: Number(g_fpsTimer && g_fpsTimer.averageFPS) || 0,
      hidden: document.hidden,
      probe: p ? p.id : null,
      draws: p ? p.draws : 0,
      frames: p ? p.frames : 0,
      probeContextLost: p ? p.contextLost : 0,
    });
  })()
  """
    .trimIndent()

/**
 * WebGL rendering test across emulator snapshot boots (see [SnapshotUiTestBase]), driven while the
 * Android Device Hub UI streams the emulator display:
 * 1. `cold_boot`: open the WebGL Aquarium in Chrome on the device, verify it, and leave it in the
 *    foreground; the emulator is then shut down through gRPC, which saves its snapshot.
 * 2. `load_<N>` (after each relaunch from the snapshot): check that the snapshot brought back the
 *    same Chrome process with the same aquarium page (not reloaded), verify it again and leave it in
 *    the foreground for the next shutdown.
 *
 * Each verification:
 * - Records a 5 second on-device video of the aquarium (`screenrecord`), attached as
 *   `webgl_aquarium_<phase>_device_video.mp4`, and checks it with ffmpeg `blackdetect`.
 * - Checks through Chrome DevTools (`adb forward` of `chrome_devtools_remote`) that all fish models
 *   are loaded, the WebGL context is not lost, frames keep being rendered and every frame issues at
 *   least one draw call per fish.
 * - Checks that the Chrome page screenshot, the device screenshot and the Device Hub display are
 *   not black, that the aquarium is animating, and that nothing crashed (logcat crash buffer).
 *
 * Needs Chrome on the system image and internet access from the emulator; point `aquarium_url` at
 * a mirror of webglsamples.org/aquarium otherwise.
 */
@RunWith(DeviceJUnit4ClassRunner::class)
class WebGlAquariumUiTest : RenderingUiTestBase() {
  override val logPrefix: String = "webgl_aquarium"

  @Option(name = "aquarium_url", description = "URL of the WebGL Aquarium page to open in Chrome.")
  private var mAquariumUrl: String = DEFAULT_AQUARIUM_URL

  @Option(name = "chrome_package", description = "Package name of Chrome on the device.")
  private var mChromePackage: String = "com.android.chrome"

  private var mChrome: Cdp? = null
  private var mForwardPort: Int = 0

  @After
  fun closeChrome() {
    runCatching { mChrome?.close() }
    mChrome = null
    if (mForwardPort != 0) {
      runCatching { getDevice().executeAdbCommand("forward", "--remove", "tcp:$mForwardPort") }
      mForwardPort = 0
    }
    // In the snapshot sequence Chrome keeps running, so that it is part of the snapshot.
    if (inSnapshotSequence) return
    runCatching {
      shell("am force-stop $mChromePackage")
      shell("am clear-debug-app")
      shell("rm -f $CHROME_COMMAND_LINE_FILE")
    }
  }

  @Test
  fun aquariumRendersFishAcrossColdBootAndSnapshotBoots() {
    if (beginPhase()) {
      // The snapshot brought back Chrome showing the aquarium.
      shell("input keyevent KEYCODE_WAKEUP")
      eventually("[$phase] Chrome in the foreground after the snapshot boot", timeoutMs = 30_000) {
        resumedActivity().contains(mChromePackage)
      }
      Assert.assertEquals(
        "[$phase] Chrome process changed across the snapshot boot (Chrome crashed?)",
        loadState(CHROME_PID),
        chromePid(),
      )
      verifyAquarium(phase = phase, expectedPageId = loadState(PAGE_ID))
    } else {
      if (isSnapshotBoot) {
        CLog.i("%s: [%s] Another test ran last before the shutdown, reopening the aquarium", TAG, phase)
      }
      CLog.i("%s: [%s] Opening %s in Chrome...", TAG, phase, mAquariumUrl)
      setUpChrome()
      openAquarium()
      storeState(PAGE_ID, verifyAquarium(phase = phase, expectedPageId = null))
    }
    val chromePid = chromePid()
    Assert.assertTrue("[$phase] Chrome is not running after the aquarium", chromePid.isNotEmpty())
    storeState(CHROME_PID, chromePid)
    endPhase()
  }

  // --- Chrome -----------------------------------------------------------------------------------

  private fun chromePid(): String = pidOf(mChromePackage)

  private fun setUpChrome() {
    Assert.assertTrue(
      "Chrome ($mChromePackage) is not installed on the device",
      shell("pm path $mChromePackage").contains("package:"),
    )
    keepScreenOn()
    shell("am force-stop $mChromePackage")
    // Chrome reads its command line from this file on debuggable builds or when it is the debug
    // app. The first run experience is skipped so the page shows up right away, and
    // --ignore-gpu-blocklist makes Chrome render WebGL through the emulator GPU (ANGLE on
    // Vulkan, i.e. gfxstream and the host driver) instead of falling back to its in-guest
    // SwiftShader software renderer, which the GPU blocklist would otherwise select.
    shell("echo '_ $CHROME_FLAGS' > $CHROME_COMMAND_LINE_FILE")
    shell("chmod 644 $CHROME_COMMAND_LINE_FILE")
    shell("am set-debug-app --persistent $mChromePackage")
    shell("pm grant $mChromePackage android.permission.POST_NOTIFICATIONS")
    clearCrashLog()
  }

  private fun openAquarium() {
    shell("am start -W -a android.intent.action.VIEW -p $mChromePackage -d '$mAquariumUrl'")
    eventually("Chrome in foreground", timeoutMs = 30_000) {
      resumedActivity().contains(mChromePackage)
    }
    connectChrome()
    eventually("aquarium initialized with all fish models loaded", timeoutMs = 180_000) {
      val state = aquariumState()
      state != null && state.getInt("fish") > 0 && state.getBoolean("fishLoaded")
    }
  }

  /** (Re)connects to the aquarium tab of Chrome on the device over `adb forward`. */
  private fun connectChrome() {
    runCatching { mChrome?.close() }
    mChrome = null
    if (mForwardPort == 0) mForwardPort = ServerSocket(0).use { it.localPort }
    // Forwards do not always survive snapshot loads; setting one again is harmless.
    getDevice().executeAdbCommand(
      "forward",
      "tcp:$mForwardPort",
      "localabstract:$CHROME_DEVTOOLS_SOCKET",
    )
    mChrome =
      Cdp.connect(mForwardPort, timeoutMs = 60_000) {
        it.optString("type") == "page" && it.optString("url").contains("aquarium")
      }
  }

  private fun chrome(): Cdp = mChrome!!

  private fun aquariumState(): JSONObject? =
    (runCatching { chrome().eval(AQUARIUM_STATE_JS) }.getOrNull() as? String)?.let(::JSONObject)

  // --- verification -----------------------------------------------------------------------------

  /** Verifies the aquarium renders fish without a black screen. Returns the page's probe id. */
  private fun verifyAquarium(phase: String, expectedPageId: String?): String {
    if (expectedPageId != null) {
      // The DevTools connection does not survive the snapshot boot; Cdp.connect retries for 60s.
      connectChrome()
    }
    shell("input keyevent KEYCODE_WAKEUP")

    val pageId = chrome().eval(INSTALL_PROBE_JS) as? String
    Assert.assertNotNull("[$phase] WebGL context of the aquarium page not found", pageId)
    if (expectedPageId != null) {
      Assert.assertEquals(
        "[$phase] The aquarium page was reloaded across the snapshot boot (renderer or GPU crash?)",
        expectedPageId,
        pageId,
      )
    }

    recordDeviceVideo(phase)
    verifyRendering(phase)
    verifyScreenshots(phase)
    assertNoCrash(phase, mChromePackage)
    return pageId!!
  }

  private fun verifyRendering(phase: String) {
    val before = aquariumState()
    Assert.assertNotNull("[$phase] Could not read the aquarium state", before)
    Thread.sleep(3_000)
    val after = aquariumState()!!
    CLog.i("%s: [%s] aquarium state: %s", TAG, phase, after)

    Assert.assertFalse("[$phase] WebGL context is lost", after.getBoolean("contextLost"))
    Assert.assertEquals(
      "[$phase] WebGL context was lost and restored",
      0,
      after.getInt("probeContextLost"),
    )
    Assert.assertFalse("[$phase] Aquarium page is hidden", after.getBoolean("hidden"))
    Assert.assertTrue("[$phase] Fish models are not loaded", after.getBoolean("fishLoaded"))

    val fish = after.getInt("fish")
    Assert.assertTrue("[$phase] Aquarium has no fish", fish > 0)
    val frames = after.getLong("frames") - before!!.getLong("frames")
    val draws = after.getLong("draws") - before.getLong("draws")
    Assert.assertTrue("[$phase] Aquarium did not render any frame in 3 seconds", frames > 0)
    val drawsPerFrame = draws.toDouble() / frames
    CLog.i(
      "%s: [%s] %d frames, %.1f draw calls per frame for %d fish, %.1f fps",
      TAG,
      phase,
      frames,
      drawsPerFrame,
      fish,
      after.getDouble("fps"),
    )
    // The aquarium issues one drawElements call per fish, plus the tank, seaweed, etc.
    Assert.assertTrue(
      "[$phase] Fish are not drawn: %.1f draw calls per frame for %d fish".format(drawsPerFrame, fish),
      drawsPerFrame >= fish,
    )
  }

  private fun verifyScreenshots(phase: String) {
    // What Chrome composited for the page, twice to make sure the fish are swimming.
    val page1 = chromeScreenshot()
    Thread.sleep(1_000)
    val page2 = chromeScreenshot()
    attachPng("${phase}_chrome_page", page1)
    val pageImage1 = decode(page1, "$phase Chrome page")
    assertNotBlack("$phase Chrome page", pageImage1)
    val diff = meanAbsDiff(pageImage1, decode(page2, "$phase Chrome page"))
    CLog.i("%s: [%s] Chrome page frame difference over 1s: %.2f", TAG, phase, diff)
    Assert.assertTrue("[$phase] The aquarium is not animating (frame difference $diff)", diff > 0.5)

    // What the emulator display shows, on the device and as streamed by the Device Hub.
    assertDisplaysNotBlack(phase)
  }

  // --- images -----------------------------------------------------------------------------------

  private fun chromeScreenshot(): ByteArray =
    Base64.getDecoder()
      .decode(
        chrome()
          .call("Page.captureScreenshot", JSONObject().put("format", "png"), timeoutSec = 30)
          .getJSONObject("result")
          .getString("data")
      )
}
