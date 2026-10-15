# Android Device Hub, Snapshot, WebGL & Maps UI E2E Tests (`//ets/ui`)

End-to-end UI tests under `//ets/ui`:
- **[`DeviceHubUiTest.kt`](DeviceHubUiTest.kt)** (`ets_host_test`): Tradefed host test that launches the **Android Device Hub** Electron UI (`android-device-hub`) against a live Android Emulator, drives it over Chrome DevTools Protocol (CDP), and verifies effects via `adb`. Also defines [`UiTestBase`](DeviceHubUiTest.kt), the shared host harness for `Xvfb`, `ffmpeg` video recording, and CDP screenshots.
- **[`SnapshotUiTest.kt`](SnapshotUiTest.kt)** (`ets_host_test`): Host-driven UI responsiveness test (modeled after `profiler.py`) extending [`UiTestBase`](DeviceHubUiTest.kt). Uses `uiautomator dump` to inspect what clickable items are on the screen, issues touch events (`tapScreen`) and toolbar `Back` clicks (`click("Back")`) through the **Android Device Hub** UI on the host to touch up to 4 Settings items and verify the UI hierarchy updates in every phase of the [snapshot sequence](#the-snapshot-sequence) (after a snapshot boot it first checks that Settings came back in the foreground), and records a host-side video (`snapshot_ui_video_*.mp4` via `ffmpeg`) and screenshots (`snapshot_ui_*.png` via CDP) per phase. Also defines [`SnapshotUiTestBase`](SnapshotUiTest.kt), which adds the snapshot sequence phase handling (`snapshot_phase` option, `beginPhase`/`endPhase`, state kept on the device) to `UiTestBase`.
- **[`RenderingUiTestBase.kt`](RenderingUiTestBase.kt)** (built into `:snapshot_ui_test`): extends `SnapshotUiTestBase` with the checks shared by the rendering tests: `recordDeviceVideo` (on-device `screenrecord` of `video_seconds`, attached as `<logPrefix>_<phase>_device_video.mp4`, checked with ffmpeg `blackdetect`), black screen checks of the device screenshot and the Device Hub display (`assertNotBlack`, `assertDisplaysNotBlack`), frame differences (`meanAbsDiff`) and crash/ANR checks (`assertNoCrash`).
- **[`WebGlAquariumUiTest.kt`](WebGlAquariumUiTest.kt)** (`ets_host_test`): WebGL rendering test extending [`RenderingUiTestBase`](RenderingUiTestBase.kt). Opens the [WebGL Aquarium](https://webglsamples.org/aquarium/aquarium.html) in Chrome on the device on cold boot and, in every phase of the [snapshot sequence](#the-snapshot-sequence), verifies:
  - a 5 second on-device video (`screenrecord`, attached as `webgl_aquarium_<phase>_device_video.mp4`) has no black segment (ffmpeg `blackdetect` over the center of the screen);
  - over Chrome DevTools (`adb forward tcp:<port> localabstract:chrome_devtools_remote`): all fish models are loaded, the WebGL context is not lost, frames keep being rendered, and each frame issues at least one `gl.drawElements` call per fish (the aquarium draws each fish separately);
  - the Chrome page screenshot, the device screenshot and the Device Hub display are not black, and the aquarium is animating;
  - after each snapshot boot: Chrome is back in the foreground in the same process, the page was not reloaded (a probe installed into the page survives), and the logcat crash buffer has no Chrome crash.

  It needs Chrome on the system image and internet access from the emulator; set `--module-arg WebGlAquariumUiTest:set-option:aquarium_url:<url>` to use a mirror. `@goldfish_test//ets/ui:webgl_ui` runs only this test.
- **[`MapsUiTest.kt`](MapsUiTest.kt)** (`ets_host_test`): Google Maps rendering test extending [`RenderingUiTestBase`](RenderingUiTestBase.kt). Gives the device a GPS fix and opens Maps there (`latitude`/`longitude` options), gets past first run and permission dialogs, searches for a place in the search box (`search_query`, default Googleplex) so Maps drops a pin and loads the area on cold boot, and in every phase of the [snapshot sequence](#the-snapshot-sequence) verifies:
  - while panning (swipes) and zooming (double tap, then one finger zoom out) the map through the Device Hub UI for a few seconds, a 5 second on-device video (`maps_ui_<phase>_device_video.mp4`) has no black segment;
  - the map is rendered (not black or blank) before and after the gestures, the gestures changed what is drawn, and the device screen and the Device Hub display are not black;
  - Maps is still in the foreground, did not crash (logcat crash buffer) and shows no crash/ANR dialog;
  - after each snapshot boot: Maps is back in the foreground in the same process; after interacting, the test uses other apps (Home, Settings), switches back to Maps and checks the map again.

  It needs Google Maps on the system image and internet access from the emulator for the map data, and enables Google Play services (disabled by the ETS device setup, but Maps needs it to load map data) for the duration of the test (of the whole snapshot sequence). The map checks look at the part of the screen between the search box and the bottom sheet. `@goldfish_test//ets/ui:maps_ui` runs only this test.

## How the UI Tests Work

[`DeviceHubUiTest.kt`](DeviceHubUiTest.kt), [`SnapshotUiTest.kt`](SnapshotUiTest.kt), [`WebGlAquariumUiTest.kt`](WebGlAquariumUiTest.kt) and [`MapsUiTest.kt`](MapsUiTest.kt) extend [`UiTestBase`](DeviceHubUiTest.kt) and run all of their UI checks within a single session per phase so that each test class records **one combined video** (`device_hub_video_*.mp4`, `snapshot_ui_video_*.mp4`, `webgl_aquarium_video_*.mp4` and `maps_ui_video_*.mp4`):
1. **Virtual Display (Headless Linux RBE)**: Starts a hermetic `Xvfb` server (`launch_xvfb.sh` from `//tools/emulator/testlib/display:xvfb`) when `DISPLAY` is unset so the Electron window renders on headless RBE workers.
2. **Video & Screenshot Recording**:
   - **Headless Linux RBE (default)**: Uses `ffmpeg -f x11grab` against the `Xvfb` display, capturing the entire window including the window bar. (Pass `--cdp-video` to `run_rbe.sh` to use CDP-piped screenshots instead.)
   - **Local Desktop (gLinux, macOS, Windows)**: Pipes JPEG frames from CDP (`Page.captureScreenshot`) into `ffmpeg -f image2pipe` so only the UI window is recorded without triggering macOS Screen Recording permission prompts.
   - Attaches one combined `${logPrefix}_video` (`.mp4`), `${logPrefix}_final` and per-action `.png` screenshots, and `${logPrefix}_log` / `ffmpeg_log` / `xvfb_log` to the Tradefed test outputs.
3. **UI Automation via CDP**: Launches `android-device-hub` with `--remote-debugging-port=<port>`, connects a lightweight JDK WebSocket Chrome DevTools Protocol (CDP) client, waits for the emulator video/canvas stream to become visible, and dispatches real mouse press/move/release events (`Input.dispatchMouseEvent`) and DOM queries (`Runtime.evaluate`).
4. **Device Verification**: Verifies the resulting state changes on the emulator over `adb` (`getDevice().executeShellCommand(...)` and `uiautomator dump`).

## The Snapshot Sequence

The emulator saves its quickboot snapshot when it exits, so `SnapshotUiTest`, `WebGlAquariumUiTest` and `MapsUiTest` do not call the gRPC `SaveSnapshot`/`LoadSnapshot` themselves. The `//ets/ui` plans pass `--snapshot_relaunch_rounds 3` to [`android_ets_cfg.py`](../android_ets_cfg.py), which runs the plan once per phase (each phase is its own Tradefed run, with its own results):

1. `cold_boot` (`ets`): the emulator cold boots; each test sets up its app, exercises it and leaves it in the foreground.
2. `ets_close`: `CloseEmulatorTest` shuts the emulator down through gRPC (`setVmState(SHUTDOWN)`); the emulator saves its snapshot on exit.
3. `load_<N>` for N = 1..3 (`goldfish_load_<N>`, `ets_load_<N>`, `ets_close_load_<N>`): the emulator is relaunched and boots from that snapshot, the tests run again with `snapshot_phase=load_<N>` (`DeviceHubUiTest` is skipped), and the emulator is shut down again (except after the last round).

After a snapshot boot each test checks that the guest was resumed (same `/proc/sys/kernel/random/boot_id` as when the previous phase started) from the snapshot saved at the end of the previous phase (the state it recorded when that phase started is there), and that its app came back in the foreground in the same process. The snapshot check only uses what a phase records when it starts, so a test failure in one phase does not make the following phases fail too; if the emulator cold boots or resumes an older snapshot (e.g. because it crashed during the previous phase and could not save), the failure names the phase and the `goldfish*` agent log to look at. What has to carry over from one phase to the next is stored on the device under `/data/local/tmp/ets_ui_snapshot`, so it is saved and restored with the snapshot. When a plan runs several of these tests, only the test that ran last before the shutdown (and finished that phase) finds its app in the foreground; the others reopen their app. Without `snapshot_phase` (`run_external.*`, `run_local.bat`) the tests only run the cold boot phase.

---

## Running the Tests

### 1. Run on Linux RBE (`run_rbe.sh`)
Boots the emulator and runs all UI tests under `//ets/ui` (`DeviceHubUiTest`, `SnapshotUiTest`, `WebGlAquariumUiTest` and `MapsUiTest`, including the [snapshot sequence](#the-snapshot-sequence)) on remote Linux RBE workers:
```bash
./third_party/adt-infra/goldfish_test/ets/ui/run_rbe.sh

# Optional: use CDP-piped video recording on RBE instead of x11grab:
./third_party/adt-infra/goldfish_test/ets/ui/run_rbe.sh --cdp-video
```

### 2. Run Full Sequence Locally (`run_local.sh` / `run_local.bat`)
Boots the emulator locally, runs `DeviceHubUiTest`, `SnapshotUiTest`, `WebGlAquariumUiTest` and `MapsUiTest`, and runs the snapshot sequence on the local machine:
- **gLinux / macOS**:
  ```bash
  ./third_party/adt-infra/goldfish_test/ets/ui/run_local.sh
  ```
  On gLinux the Device Hub window is shown on your desktop (the script passes `DISPLAY`/`XAUTHORITY` into the test). Pass `--xvfb` (or set `XVFB=1`) to run inside the hermetic Xvfb display instead, like on RBE. Other arguments are passed to `bazel test`.
- **Windows (`cmd.exe` / PowerShell)**:
  ```cmd
  third_party\adt-infra\goldfish_test\ets\ui\run_local.bat
  ```
  Bazel cannot run the `:ui` sequence on Windows, so the script replays it: it builds an optimized emulator from the checkout and fetches the same system image, cold boots the ETS AVD with the same emulator flags and device setup, runs the tests through `run_external.bat`, and closes the emulator with `CloseEmulatorTest`. Extra arguments are passed to Tradefed. The emulator log and the Tradefed logs and results (videos, screenshots) are written to `out\ets_ui\<timestamp>` under the repo root. Set `EMULATOR_PORT` to choose the console port instead of the first free one. Like the sequence's `junit_xml_result` step, both Windows scripts take pass/fail from Tradefed's result XML (`check_tradefed_results.ps1`) and exit with 1 when a test failed or did not run; Tradefed's own exit code is not usable for this (0 on test failures, and always 1 on Windows where its console dies with `Unknown signal: TSTP`).

  `run_local.sh` and `run_external.sh` are Bazel tests, so Bazel reports them to Sponge. The Windows scripts run the emulator and Tradefed outside of Bazel, so they end with [`report_to_sponge.bat`](report_to_sponge.bat) instead, which runs `bazel test --config=rcache --config=sponge --test_arg=--out_dir=<out dir> @goldfish_test//ets/ui:report_results` and prints the Fusion link (`run_local.bat` reports the whole run including `CloseEmulatorTest`; `run_external.bat` reports when it is not called from `run_local.bat`). [`report_results.py`](report_results.py) converts the Tradefed `test_result.xml` files of the run into Bazel's JUnit XML (one test case per Tradefed test, flaky passes and skips included), copies the output directory into the test's undeclared outputs (`outputs.zip` in Fusion: `emulator.log`, videos, screenshots, Tradefed logs), and fails when a test failed or an invocation is missing. `--config=rcache` is what makes Bazel upload those files rather than referencing them by local path; the test verdict and exit code of the scripts do not depend on this step.

### 3. Run Against an Already-Running Emulator (`run_external.sh` / `run_external.bat`)
Fastest workflow for local iteration on **gLinux**, **macOS**, or **Windows**. Start an emulator first, then run:
- **gLinux / macOS / Windows (Git Bash)**:
  ```bash
  ./third_party/adt-infra/goldfish_test/ets/ui/run_external.sh
  ```
- **Windows (`cmd.exe` / PowerShell)**:
  ```cmd
  third_party\adt-infra\goldfish_test\ets\ui\run_external.bat
  ```
  The Tradefed logs and results, including the `device_hub_video`, `snapshot_ui_video`, `webgl_aquarium_video` and `maps_ui_video` recordings, are copied to `out\ets_ui\<timestamp>` under the repo root and reported to Sponge (see section 2). If `BAZEL_SH` points at busybox, the ETS is built with Git Bash or MSYS2 bash instead when one is installed (`--shell_executable` and `--repo_env=BAZEL_SH`): rules_android extracts `.aar` manifests with a shebang-less `unzip` script and generates the desugar configs with `unzip -c`, and busybox-w32 supports neither (`unzip: Exec format error`). Because the shell's directory is part of every action's `PATH`, the ETS build tools get their own `bazel-out\ets-opt-exec` directory so that they do not evict the emulator build's tools from the cache.

---

## How to Add a New UI Test

### Option A: Add a New Step to `DeviceHubUiTest.kt` (Recommended)

For most UI features (toolbar buttons, multi-touch gestures, settings panels, window state), add a helper method to [`DeviceHubUiTest.kt`](DeviceHubUiTest.kt) and invoke it inside `verifyDeviceHubUiInteractions()`. All steps in `verifyDeviceHubUiInteractions()` share a single `Xvfb` + `ffmpeg` + `android-device-hub` session and are recorded into a single combined `device_hub_video_*.mp4`.

#### Built-in Helpers in `UiTestBase`

| Helper | Description |
| :--- | :--- |
| `click("Button Label")` | Finds the button with `[aria-label="Button Label"]` and dispatches a real mouse move + press + release at its center. |
| `tapScreen(normX, normY)` | Taps the streamed emulator display at normalized coordinates `(0.0..1.0, 0.0..1.0)`. |
| `swipeScreen(x0, y0, x1, y1, steps)` | Drags/swipes across the streamed emulator display using normalized coordinates. |
| `cdp().eval("jsExpr")` | Evaluates a JavaScript expression in the Electron renderer and returns its value. |
| `cdp().call("Domain.method", json)` | Sends any raw Chrome DevTools Protocol command (`Input.*`, `Page.*`, `DOM.*`, etc.). |
| `waitForUi("jsBooleanExpr", timeoutMs)` | Polls until the JavaScript expression evaluates to `true` in the UI (attaches a screenshot on timeout). |
| `eventually("description") { ... }` | Polls until a host/device condition returns `true` (attaches a screenshot on timeout). |
| `attachScreenshot("tag_name")` | Captures a PNG screenshot of the UI and attaches it to Tradefed logs as `${logPrefix}_<tag_name>`. |
| `getDevice().executeShellCommand("...")` | Runs an `adb shell` command on the connected emulator to set up or verify device state. |

#### Example: Adding a New Step

```kotlin
private fun powerButtonTogglesInteractiveState() {
  // 1. Ensure the device screen starts awake.
  getDevice().executeShellCommand("input keyevent KEYCODE_WAKEUP")
  eventually("screen is interactive") {
    getDevice().executeShellCommand("dumpsys power").contains("mWakefulness=Awake")
  }

  // 2. Drive the Android Device Hub UI.
  click("Power")
  attachScreenshot("after_power_click")

  // 3. Verify the effect on the emulator via adb.
  eventually("device entered sleep/doze state") {
    !getDevice().executeShellCommand("dumpsys power").contains("mWakefulness=Awake")
  }

  // 4. Restore awake state for subsequent tests.
  getDevice().executeShellCommand("input keyevent KEYCODE_WAKEUP")
}
```
---

### Option B: Add a New Test Class Under `ets/ui/`

If you need a separate test class (for example, `MultiDisplayUiTest.kt`):

1. **Create the Kotlin test file** under `third_party/adt-infra/goldfish_test/ets/ui/MultiDisplayUiTest.kt` in package `com.android.tools.e2etests.ui`.
2. **Register the target in [`ets/ui/BUILD.bazel`](BUILD.bazel)**:
   - Add an `ets_host_test(name = "multi_display_ui_test", srcs = ["MultiDisplayUiTest.kt"], class_name = "com.android.tools.e2etests.ui.MultiDisplayUiTest", ...)`.
   - Add `":multi_display_ui_test_config"` to `ets_pkg(name = "pkg", srcs = [...])`.
3. **Include the test jar in the ETS deploy jar** in [`ets/java/com/android/tools/e2etests/BUILD.bazel`](../java/com/android/tools/e2etests/BUILD.bazel):
   - Add `"//ets/ui:multi_display_ui_test"` to `runtime_deps`.
4. **Add the module to [`ets/java/com/android/tools/e2etests/config/config_gen.py`](../java/com/android/tools/e2etests/config/config_gen.py)**:
   - Add `"MultiDisplayUiTest"` to `ETS_MODULES`.
5. **Verify the module list test**:
   ```bash
   ./prebuilts/bazel/linux-x86_64/bazel test --config=remote @goldfish_test//testlib:ets_modules_test
   ```
