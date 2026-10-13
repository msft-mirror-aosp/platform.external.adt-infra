# Android Device Hub & Snapshot UI E2E Tests (`//ets/ui`)

End-to-end UI tests under `//ets/ui`:
- **[`DeviceHubUiTest.kt`](DeviceHubUiTest.kt)** (`ets_host_test`): Tradefed host test that launches the **Android Device Hub** Electron UI (`android-device-hub`) against a live Android Emulator, drives it over Chrome DevTools Protocol (CDP), and verifies effects via `adb`. Also defines [`UiTestBase`](DeviceHubUiTest.kt), the shared host harness for `Xvfb`, `ffmpeg` video recording, and CDP screenshots.
- **[`SnapshotUiTest.kt`](SnapshotUiTest.kt)** (`ets_host_test`): Host-driven UI responsiveness test (modeled after `profiler.py`) extending [`UiTestBase`](DeviceHubUiTest.kt). Uses `uiautomator dump` to inspect what clickable items are on the screen, issues touch events (`tapScreen`) and toolbar `Back` clicks (`click("Back")`) through the **Android Device Hub** UI on the host to touch up to 4 Settings items and verify the UI hierarchy updates across `cold boot -> interact with settings -> save snapshot -> {load snapshot -> interact with settings -> save snapshot} x 3`, and records a single combined host-side video (`snapshot_ui_video_*.mp4` via `ffmpeg`) and screenshots (`snapshot_ui_*.png` via CDP).

## How `DeviceHubUiTest` and `SnapshotUiTest` Work

Both [`DeviceHubUiTest.kt`](DeviceHubUiTest.kt) and [`SnapshotUiTest.kt`](SnapshotUiTest.kt) extend [`UiTestBase`](DeviceHubUiTest.kt) and run all of their UI checks within a single session per phase so that each test class records **one combined video** (`device_hub_video_*.mp4` and `snapshot_ui_video_*.mp4`):
1. **Virtual Display (Headless Linux RBE)**: Starts a hermetic `Xvfb` server (`launch_xvfb.sh` from `//tools/emulator/testlib/display:xvfb`) when `DISPLAY` is unset so the Electron window renders on headless RBE workers.
2. **Video & Screenshot Recording**:
   - **Headless Linux RBE (default)**: Uses `ffmpeg -f x11grab` against the `Xvfb` display, capturing the entire window including the window bar. (Pass `--cdp-video` to `run_rbe.sh` to use CDP-piped screenshots instead.)
   - **Local Desktop (gLinux, macOS, Windows)**: Pipes JPEG frames from CDP (`Page.captureScreenshot`) into `ffmpeg -f image2pipe` so only the UI window is recorded without triggering macOS Screen Recording permission prompts.
   - Attaches one combined `${logPrefix}_video` (`.mp4`), `${logPrefix}_final` and per-action `.png` screenshots, and `${logPrefix}_log` / `ffmpeg_log` / `xvfb_log` to the Tradefed test outputs.
3. **UI Automation via CDP**: Launches `android-device-hub` with `--remote-debugging-port=<port>`, connects a lightweight JDK WebSocket Chrome DevTools Protocol (CDP) client, waits for the emulator video/canvas stream to become visible, and dispatches real mouse press/move/release events (`Input.dispatchMouseEvent`) and DOM queries (`Runtime.evaluate`).
4. **Device Verification**: Verifies the resulting state changes on the emulator over `adb` (`getDevice().executeShellCommand(...)` and `uiautomator dump`).

---

## Running the Tests

### 1. Run on Linux RBE (`run_rbe.sh`)
Boots the emulator and runs all UI tests under `//ets/ui` (`DeviceHubUiTest` and `SnapshotUiTest`, including snapshot save/load) on remote Linux RBE workers:
```bash
./third_party/adt-infra/goldfish_test/ets/ui/run_rbe.sh

# Optional: use CDP-piped video recording on RBE instead of x11grab:
./third_party/adt-infra/goldfish_test/ets/ui/run_rbe.sh --cdp-video
```

### 2. Run Full Sequence Locally (`run_local.sh` / `run_local.bat`)
Boots the emulator locally, runs `DeviceHubUiTest` and `SnapshotUiTest`, and runs the snapshot sequence on the local machine:
- **gLinux / macOS**:
  ```bash
  ./third_party/adt-infra/goldfish_test/ets/ui/run_local.sh
  ```
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
  The Tradefed logs and results, including the `device_hub_video` and `snapshot_ui_video` recordings, are copied to `out\ets_ui\<timestamp>` under the repo root and reported to Sponge (see section 2). If `BAZEL_SH` points at busybox, the ETS is built with Git Bash or MSYS2 bash instead when one is installed (`--shell_executable` and `--repo_env=BAZEL_SH`): rules_android extracts `.aar` manifests with a shebang-less `unzip` script and generates the desugar configs with `unzip -c`, and busybox-w32 supports neither (`unzip: Exec format error`). Because the shell's directory is part of every action's `PATH`, the ETS build tools get their own `bazel-out\ets-opt-exec` directory so that they do not evict the emulator build's tools from the cache.

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
