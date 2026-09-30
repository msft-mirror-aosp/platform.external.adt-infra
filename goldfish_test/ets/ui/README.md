# Android Device Hub UI E2E Tests (`//ets/ui`)

End-to-end Tradefed host tests for the **Android Device Hub** Electron UI (`android-device-hub`) connected to a live Android Emulator.

## How It Works

Each test in [`DeviceHubUiTest.kt`](DeviceHubUiTest.kt):
1. **Virtual Display (Headless Linux RBE)**: Starts a hermetic `Xvfb` server (`launch_xvfb.sh` from `//tools/emulator/testlib/display:xvfb`) when `DISPLAY` is unset so the Electron window renders on headless RBE workers.
2. **Video & Screenshot Recording**:
   - **Headless Linux RBE (default)**: Uses `ffmpeg -f x11grab` against the `Xvfb` display, capturing the entire window including the window bar. (Pass `--cdp-video` to `run_rbe.sh` to use CDP-piped screenshots instead.)
   - **Local Desktop (gLinux, macOS, Windows)**: Pipes JPEG frames from CDP (`Page.captureScreenshot`) into `ffmpeg -f image2pipe` so only the UI window is recorded without triggering macOS Screen Recording permission prompts.
   - Attaches `device_hub_video` (`.mp4`), `device_hub_final` / intermediate `.png` screenshots, and `device_hub_log` / `ffmpeg_log` / `xvfb_log` to the Tradefed test outputs.
3. **UI Automation via CDP**: Launches `android-device-hub` with `--remote-debugging-port=<port>`, connects a lightweight JDK WebSocket Chrome DevTools Protocol (CDP) client, waits for the emulator video/canvas stream to become visible, and dispatches real mouse press/move/release events (`Input.dispatchMouseEvent`) and DOM queries (`Runtime.evaluate`).
4. **Device Verification**: Verifies the resulting state changes on the emulator over `adb` (`getDevice().executeShellCommand(...)`).

---

## Running the Tests

### 1. Run on Linux RBE (`run_rbe.sh`)
Boots the emulator and runs the full `DeviceHubUiTest` suite (including snapshot save/load) on remote Linux RBE workers:
```bash
./third_party/adt-infra/goldfish_test/ets/ui/run_rbe.sh

# Optional: use CDP-piped video recording on RBE instead of x11grab:
./third_party/adt-infra/goldfish_test/ets/ui/run_rbe.sh --cdp-video
```

### 2. Run Full Sequence Locally on gLinux or macOS (`run_local.sh`)
Boots the emulator locally, runs `DeviceHubUiTest`, and runs the snapshot sequence on the local machine:
```bash
./third_party/adt-infra/goldfish_test/ets/ui/run_local.sh
```

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

---

## How to Add a New UI Test

### Option A: Add a New `@Test` Method to `DeviceHubUiTest.kt` (Recommended)

For most UI features (toolbar buttons, multi-touch gestures, settings panels, window state), add a new `@Test` method directly to [`DeviceHubUiTest.kt`](DeviceHubUiTest.kt). The `@Before` / `@After` hooks automatically handle launching `Xvfb`, starting video recording, starting `android-device-hub`, waiting for the emulator display stream, and collecting logs/screenshots/videos on teardown.

#### Built-in Helpers in `DeviceHubUiTest`

| Helper | Description |
| :--- | :--- |
| `click("Button Label")` | Finds the button with `[aria-label="Button Label"]` and dispatches a real mouse move + press + release at its center. |
| `tapScreen(normX, normY)` | Taps the streamed emulator display at normalized coordinates `(0.0..1.0, 0.0..1.0)`. |
| `swipeScreen(x0, y0, x1, y1, steps)` | Drags/swipes across the streamed emulator display using normalized coordinates. |
| `cdp().eval("jsExpr")` | Evaluates a JavaScript expression in the Electron renderer and returns its value. |
| `cdp().call("Domain.method", json)` | Sends any raw Chrome DevTools Protocol command (`Input.*`, `Page.*`, `DOM.*`, etc.). |
| `waitForUi("jsBooleanExpr", timeoutMs)` | Polls until the JavaScript expression evaluates to `true` in the UI (attaches a screenshot on timeout). |
| `eventually("description") { ... }` | Polls until a host/device condition returns `true` (attaches a screenshot on timeout). |
| `attachScreenshot("tag_name")` | Captures a PNG screenshot of the UI and attaches it to Tradefed logs as `device_hub_<tag_name>`. |
| `getDevice().executeShellCommand("...")` | Runs an `adb shell` command on the connected emulator to set up or verify device state. |

#### Example: Adding a New Test Method

```kotlin
@Test
fun powerButtonTogglesInteractiveState() {
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
