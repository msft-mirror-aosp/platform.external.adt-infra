# Foldable Display E2E Tests (`//ets/foldable`)

End-to-end host tests under `//ets/foldable` for embedded foldable emulator display rendering (`-qt-hide-window`):
- **[`FoldableDisplayTest.kt`](FoldableDisplayTest.kt)** (`ets_host_test`): Tradefed host test that connects to the running emulator over gRPC (`EmulatorController`) and `adb` and verifies display rendering across:
  1. **Unfolded inner display (`hinge_angle0 = 180°`)**: Verifies unfolded display dimensions and non-black host gRPC (`PNG`, `RGBA8888`) and guest screenshots.
  2. **Folded outer display (`hinge_angle0 = 15°`)**: Folds the device via gRPC `setPhysicalModel(HINGE_ANGLE0)` and verifies that the outer display (`1080x2364`) renders non-black frames in host gRPC (`PNG`, `RGBA8888`) and guest screenshots, guarding against applying the powered-off inner display's color transform to the outer display's `ColorBuffer` (`b/571840024`).
  3. **Repeated unfold (`180°`) and re-fold (`15°`) transitions**: Verifies both displays continue rendering across repeated posture changes.
  4. **Screen off (`KEYCODE_SLEEP`) and screen on (`KEYCODE_WAKEUP`) while folded (`15°`)**: Verifies that turning the screen off while folded turns the host gRPC `PNG` and `RGBA8888` screenshots completely black across the entire frame with intact opaque alpha (`255`)—testing `rcSetDisplayPowerMode` / `rcGetDisplayPowerMode` HWC display 1 to host display 6 mapping and 4-byte `GL_RGBA` pixel stride in `ColorBufferGl::readPixelsScaled` (`b/571840024`)—and that waking the device back up while folded restores non-black rendering on the outer display.
  5. **Unfold (`180°`) after folded power cycle**: Verifies the inner display renders cleanly after unfolding.
  6. **Full-test video & screenshot artifacts**: Records a full-test `.mp4` video (`foldable_display_video_*.mp4`, `LogDataType.MP4`) across all fold/unfold/sleep/wakeup transitions in addition to per-step host (`PNG`, `RGBA8888`) and guest screenshot attachments.

## Running the Tests

### 1. Run on Linux RBE (`run_rbe.sh`)
```bash
./third_party/adt-infra/goldfish_test/ets/foldable/run_rbe.sh
```

### 2. Run Full Sequence Locally (`run_local.sh` / `run_local.bat`)
- **gLinux / macOS**:
  ```bash
  ./third_party/adt-infra/goldfish_test/ets/foldable/run_local.sh
  ```
- **Windows (`cmd.exe` / PowerShell)**:
  ```cmd
  third_party\adt-infra\goldfish_test\ets\foldable\run_local.bat
  ```

### 3. Run Against an Already-Running Foldable Emulator (`run_external.sh` / `run_external.bat`)
- **gLinux / macOS / Windows (Git Bash)**:
  ```bash
  ./third_party/adt-infra/goldfish_test/ets/foldable/run_external.sh
  ```
- **Windows (`cmd.exe` / PowerShell)**:
  ```cmd
  third_party\adt-infra\goldfish_test\ets\foldable\run_external.bat
  ```
