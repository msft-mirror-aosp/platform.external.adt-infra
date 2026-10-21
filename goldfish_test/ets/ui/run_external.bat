@echo off
REM Runs DeviceHubUiTest and SnapshotUiTest locally on Windows against an already-running emulator.
REM Extra arguments are passed on to Tradefed, e.g. -s emulator-5554 to pick the device.
REM The Tradefed logs and results (device_hub_video/snapshot_ui_video .mp4, screenshots, hub and
REM ffmpeg logs) are copied to %ETS_UI_OUT_DIR%, by default out\ets_ui\<timestamp> under the repo
REM root, and reported to Sponge like run_external.sh's. If ETS_WORK_DIR is set, the ETS and device
REM hub are extracted there and kept, so that run_local.bat can run CloseEmulatorTest from the same
REM ETS afterwards and report the whole run.
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..\..\..\..\..") do set "REPO_ROOT=%%~fI"

set "BAZEL=%REPO_ROOT%\prebuilts\bazel\windows-x86_64\bazel.exe"
set "HUB_ZIP=%REPO_ROOT%\prebuilts\android-emulator-build\common\android-device-hub\win32-x64\device-hub_pack_win32_x64.zip"

REM rules_android builds the .aar dependencies of the test apks with a shebang-less sh_binary named
REM "unzip" and with genrules that run "unzip -c", neither of which busybox-w32 supports, so with
REM BAZEL_SH pointing at busybox the ETS build fails ("unzip: Exec format error"). Build the ETS
REM with a full bash instead when one is installed (Git for Windows or MSYS2): --shell_executable
REM runs genrules with it and puts its directory on the PATH of every action, and --repo_env makes
REM the sh_binary launchers use it. That PATH is part of every action key, so the build tools shared
REM with the emulator build (bazel-out\windows_x64-opt-exec) would be rebuilt every time the shell
REM flips between the two builds; give the tools of this build their own output directory
REM (bazel-out\ets-opt-exec) instead. The name must stay short: with a longer one (for example
REM --host_compilation_mode=fastbuild) the hermetic python the tools use exceeds MAX_PATH and crashes.
set "ETS_BAZEL_FLAGS="
set "ETS_BUSYBOX_SH="
if defined BAZEL_SH if /i not "!BAZEL_SH:busybox=!"=="!BAZEL_SH!" set "ETS_BUSYBOX_SH=1"
if defined ETS_BUSYBOX_SH (
  for %%B in ("%ProgramFiles%\Git\usr\bin\bash.exe" "%ProgramFiles%\Git\bin\bash.exe" "%LOCALAPPDATA%\Programs\Git\usr\bin\bash.exe" "C:\msys64\usr\bin\bash.exe") do (
    if not defined ETS_BASH if exist "%%~B" set "ETS_BASH=%%~B"
  )
  if defined ETS_BASH (
    echo BAZEL_SH is busybox, which cannot run the unzip script and commands rules_android uses. Building the ETS with !ETS_BASH! instead.
    REM Quoted: the cquery below runs through "call", which splits unquoted arguments at "=".
    set "ETS_BAZEL_FLAGS="--shell_executable=!ETS_BASH!" "--repo_env=BAZEL_SH=!ETS_BASH!" "--experimental_override_name_platform_in_output_dir=@goldfish_build//platforms:windows_x64=ets""
  ) else (
    echo WARNING: BAZEL_SH is busybox and no Git Bash or MSYS2 bash was found. The ETS build may fail with "unzip: Exec format error".
  )
)

pushd "%REPO_ROOT%"
"%BAZEL%" build %ETS_BAZEL_FLAGS% @goldfish_test//ets:android_ets_zip
if errorlevel 1 (
  popd
  exit /b 1
)
REM The zip lives in a configuration specific bazel-out directory, and bazel-bin points at whichever
REM configuration was built last (run_local.bat builds the emulator with -c opt first), so ask bazel.
for /f "delims=" %%I in ('call "%BAZEL%" info execution_root 2^>nul') do set "EXEC_ROOT=%%I"
for /f "delims=" %%F in ('call "%BAZEL%" cquery %ETS_BAZEL_FLAGS% --output=files @goldfish_test//ets:android_ets_zip 2^>nul') do set "ETS_ZIP=%EXEC_ROOT%/%%F"
if not defined ETS_ZIP (
  echo Could not locate the output of @goldfish_test//ets:android_ets_zip with bazel cquery.
  popd
  exit /b 1
)
set "ETS_ZIP=%ETS_ZIP:/=\%"

if defined ETS_WORK_DIR (set "WORK_DIR=%ETS_WORK_DIR%") else set "WORK_DIR=%TEMP%\ets_ui_%RANDOM%"
if not exist "%WORK_DIR%\ets" mkdir "%WORK_DIR%\ets"
if not exist "%WORK_DIR%\hub" mkdir "%WORK_DIR%\hub"

echo Extracting %ETS_ZIP% and the device hub into %WORK_DIR%
powershell -NoProfile -Command "Expand-Archive -Path '%ETS_ZIP%' -DestinationPath '%WORK_DIR%\ets' -Force"
powershell -NoProfile -Command "Expand-Archive -Path '%HUB_ZIP%' -DestinationPath '%WORK_DIR%\hub' -Force"

REM Tradefed's set-option splits on ":", so "C:\..." would be read as option "C".
REM Pass the paths with forward slashes and an escaped drive-letter colon instead.
REM (Done inline: cmd can fail to find "call :label" targets in a .bat with LF line endings.)
set "HUB_EXE=%WORK_DIR%\hub\android_device_hub.exe"
set "HUB_EXE=!HUB_EXE:\=/!"
set "HUB_EXE=!HUB_EXE::=\:!"
set "DISPLAY_DIR=%REPO_ROOT%\tools\emulator\testlib\display"
set "DISPLAY_DIR=!DISPLAY_DIR:\=/!"
set "DISPLAY_DIR=!DISPLAY_DIR::=\:!"

call "%WORK_DIR%\ets\android-ets\tools\ets-tradefed.bat" run commandAndExit ets ^
  --include-filter DeviceHubUiTest ^
  --include-filter SnapshotUiTest ^
  --module-arg "DeviceHubUiTest:set-option:device_hub_path:!HUB_EXE!" ^
  --module-arg "DeviceHubUiTest:set-option:display_dir:!DISPLAY_DIR!" ^
  --module-arg "SnapshotUiTest:set-option:device_hub_path:!HUB_EXE!" ^
  --module-arg "SnapshotUiTest:set-option:display_dir:!DISPLAY_DIR!" ^
  %*

REM ets-tradefed.bat changes the current directory into WORK_DIR; leave it before deleting it.
popd

REM Tradefed's exit code says nothing about the run: its Console exits with 0 when tests fail, and
REM on Windows it is always 1 because its main thread dies with "Unknown signal: TSTP". Judge the
REM run by the result XML instead, like the junit_xml_result step of the sequence does.
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%check_tradefed_results.ps1" "%WORK_DIR%\ets\android-ets\results" 1
set "EXIT_CODE=%ERRORLEVEL%"

REM Keep the test outputs like bazel-testlogs does on Linux and macOS.
if not defined ETS_UI_OUT_DIR for /f %%T in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss"') do set "ETS_UI_OUT_DIR=%REPO_ROOT%\out\ets_ui\%%T"
if exist "%WORK_DIR%\ets\android-ets\logs" robocopy "%WORK_DIR%\ets\android-ets\logs" "%ETS_UI_OUT_DIR%\logs" /E >nul
if exist "%WORK_DIR%\ets\android-ets\results" robocopy "%WORK_DIR%\ets\android-ets\results" "%ETS_UI_OUT_DIR%\results" /E >nul
echo Test outputs (videos, screenshots, logs): %ETS_UI_OUT_DIR%

if not defined ETS_WORK_DIR rmdir /s /q "%WORK_DIR%"
REM run_external.sh is a Bazel test, so Bazel reports it to Sponge; do the same here, see
REM report_to_sponge.bat. When run_local.bat calls this script, it reports the whole run itself.
REM The verdict above does not depend on this step.
if not defined ETS_WORK_DIR call "%SCRIPT_DIR%report_to_sponge.bat" "%ETS_UI_OUT_DIR%" 1
exit /b %EXIT_CODE%
