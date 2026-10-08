@echo off
REM Runs the cold boot part of the Android Device Hub UI ETS sequence (@goldfish_test//ets/ui:ui)
REM locally on Windows the way run_local.sh does on gLinux and macOS (android_ets_cfg.py):
REM builds the emulator from this checkout, cold boots it on the same system image with the same
REM AVD, flags and device setup, runs DeviceHubUiTest, SnapshotUiTest, WebGlAquariumUiTest and
REM MapsUiTest through run_external.bat (which launches the Android Device Hub UI against it), and closes it
REM with CloseEmulatorTest. It does not relaunch the emulator from its snapshot afterwards, so the
REM snapshot phases of the sequence (--snapshot_relaunch_rounds) do not run.
REM
REM Extra arguments are passed on to Tradefed, e.g.
REM   run_local.bat --module-arg SnapshotUiTest:set-option:cdp_video:true
REM Set EMULATOR_PORT to pick the console port instead of the first free one.
REM The emulator log and the Tradefed logs and results (videos, screenshots) are written to
REM out\ets_ui\<timestamp> under the repo root and, like run_local.sh's, reported to Sponge.
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..\..\..\..\..") do set "REPO_ROOT=%%~fI"
set "BAZEL=%REPO_ROOT%\prebuilts\bazel\windows-x86_64\bazel.exe"
REM @goldfish//emulator/libs/grpc_security:unsecure-emulator-access, the allowlist the sequence uses.
set "ALLOWLIST=%REPO_ROOT%\hardware\generic\goldfish\emulator\libs\grpc_security\testdata\test_allow_list.json"

REM The emulator and Tradefed look for adb on PATH; Tradefed also needs java.
where adb >nul 2>&1 || (
  for %%A in ("%ANDROID_SDK_ROOT%\platform-tools" "%LOCALAPPDATA%\Android\Sdk\platform-tools" "%REPO_ROOT%\prebuilts\android\android-sdk\windows\platform-tools") do (
    if not defined ADB_DIR if exist "%%~A\adb.exe" set "ADB_DIR=%%~A"
  )
  if not defined ADB_DIR (
    echo adb not found. Add platform-tools to PATH or set ANDROID_SDK_ROOT.
    exit /b 1
  )
  set "PATH=!ADB_DIR!;!PATH!"
)
where java >nul 2>&1 || (
  echo java not found. Tradefed needs Java 17 or newer on PATH.
  exit /b 1
)

REM Boot on the first free console port like the sequencer does, unless EMULATOR_PORT is set.
if not defined EMULATOR_PORT for /f %%P in ('powershell -NoProfile -Command "for ($p = 5554; $p -le 5682; $p += 2) { $free = $true; foreach ($q in $p, ($p + 1)) { try { $l = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, $q); $l.Start(); $l.Stop() } catch { $free = $false } }; if ($free) { $p; break } }"') do set "EMULATOR_PORT=%%P"
if not defined EMULATOR_PORT (
  echo No free emulator console port found between 5554 and 5682.
  exit /b 1
)
set "SERIAL=emulator-%EMULATOR_PORT%"

REM Like the goldfish_fetch and avd steps: build an optimized emulator from this checkout and
REM fetch the system image :ui boots on gLinux. The outputs live under configuration specific
REM directories, so ask bazel where they are instead of going through bazel-bin.
echo === Building the emulator and fetching the system image
pushd "%REPO_ROOT%"
"%BAZEL%" build -c opt @goldfish//emulator:release @goldfish_test//ets/ui:system_image
if errorlevel 1 (
  popd
  exit /b 1
)
for /f "delims=" %%I in ('call "%BAZEL%" info execution_root 2^>nul') do set "EXEC_ROOT=%%I"
for /f "delims=" %%I in ('call "%BAZEL%" info output_base 2^>nul') do set "OUTPUT_BASE=%%I"
for /f "delims=" %%F in ('call "%BAZEL%" cquery -c opt --output=files @goldfish//emulator:release 2^>nul') do set "EMULATOR_ZIP=%EXEC_ROOT%/%%F"
for /f "delims=" %%F in ('call "%BAZEL%" cquery -c opt --output=files @goldfish_test//ets/ui:system_image 2^>nul') do (
  set "LINE=%%F"
  if /i "!LINE:~-11!"=="/system.img" set "SYSTEM_IMG=%OUTPUT_BASE%/%%F"
)
popd
if not defined EMULATOR_ZIP (
  echo Could not locate the output of @goldfish//emulator:release with bazel cquery.
  exit /b 1
)
if not defined SYSTEM_IMG (
  echo Could not locate system.img in @goldfish_test//ets/ui:system_image with bazel cquery.
  exit /b 1
)
set "EMULATOR_ZIP=%EMULATOR_ZIP:/=\%"
set "SYSTEM_IMG=%SYSTEM_IMG:/=\%"
for %%F in ("%SYSTEM_IMG%") do set "SYSDIR=%%~dpF"

set "WORK_DIR=%TEMP%\ets_local_%RANDOM%"
mkdir "%WORK_DIR%\avd\ets.avd"
echo === Extracting %EMULATOR_ZIP% into %WORK_DIR%
"%SystemRoot%\System32\tar.exe" -xf "%EMULATOR_ZIP%" -C "%WORK_DIR%"
if not exist "%WORK_DIR%\emulator\emulator.exe" (
  echo Could not extract the emulator.
  rmdir /s /q "%WORK_DIR%"
  exit /b 1
)

REM The AVD agent_common.avd_ets creates for the //ets/ui plans: a UTF-8 display name, 8G of RAM and
REM the phone sized screen of --avd_ini in ets/ui/BUILD.bazel.
set "ANDROID_AVD_HOME=%WORK_DIR%\avd"
> "%ANDROID_AVD_HOME%\ets.ini" echo path=%ANDROID_AVD_HOME%\ets.avd
powershell -NoProfile -Command "[IO.File]::WriteAllLines('%ANDROID_AVD_HOME%\ets.avd\config.ini', @(('avd.ini.displayname=UTF8' + [char]::ConvertFromUtf32(0x1F916)), 'hw.ramSize=8192', 'hw.lcd.width=1080', 'hw.lcd.height=2400', 'hw.lcd.density=420', 'image.sysdir.1=%SYSDIR%'))"

for /f %%T in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss"') do set "OUT_DIR=%REPO_ROOT%\out\ets_ui\%%T"
mkdir "%OUT_DIR%"
REM run_external.bat extracts the ETS and device hub into WORK_DIR and collects its outputs in OUT_DIR.
set "ETS_WORK_DIR=%WORK_DIR%"
set "ETS_UI_OUT_DIR=%OUT_DIR%"

REM Matches the emulator launcher and its QEMU process, but not helpers such as netsimd, which
REM can be shared with other emulators and outlive this one.
set "EMU_PROCS=Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -like '%WORK_DIR%\emulator\*' -and ($_.Name -eq 'emulator.exe' -or $_.Name -like 'qemu-system-*') }"

REM Like the goldfish_grpc step: cold boot with the same emulator flags.
set "EMULATOR_ARGS=-avd ets -port %EMULATOR_PORT% -verbose -show-kernel -qt-hide-window -not-in-bazel -verbose-grpc -grpc-allowlist "%ALLOWLIST%""
echo === Booting %SERIAL%: emulator.exe %EMULATOR_ARGS%
echo     log: %OUT_DIR%\emulator.log
start "" /b "%WORK_DIR%\emulator\emulator.exe" %EMULATOR_ARGS% > "%OUT_DIR%\emulator.log" 2>&1
set "EXIT_CODE=0"
powershell -NoProfile -Command "$end = (Get-Date).AddMinutes(10); while ((Get-Date) -lt $end) { if (((adb -s %SERIAL% shell getprop sys.boot_completed 2>$null) -join '').Trim() -eq '1') { exit 0 }; if (-not (%EMU_PROCS%)) { exit 2 }; Start-Sleep -Seconds 2 }; exit 1"
if errorlevel 1 (
  echo The emulator did not boot, see %OUT_DIR%\emulator.log
  set "EXIT_CODE=1"
)

if "!EXIT_CODE!"=="0" (
  REM The same device setup android_ets_cfg.py applies before running the tests.
  echo === Setting up %SERIAL%
  for %%C in (
    "settings put global device_provisioned 1"
    "settings put secure user_setup_complete 1"
    "pm disable-user --user 0 com.android.vending"
    "pm disable-user --user 0 com.google.android.configupdater"
    "pm disable-user --user 0 com.google.android.gms"
    "pm disable-user --user 0 com.google.android.gsf"
    "am force-stop com.android.settings"
    "am force-stop com.google.android.bluetooth"
    "am force-stop com.android.phone"
    "am force-stop com.google.android.gms"
    "settings put global hide_error_dialogs 1"
    "settings put global window_animation_scale 0.0"
    "settings put global transition_animation_scale 0.0"
    "settings put global animator_duration_scale 0.0"
    "am kill-all"
    "am wait-for-broadcast-barrier"
    "am wait-for-broadcast-idle"
  ) do adb -s %SERIAL% shell %%~C

  REM The ets step: the same Tradefed arguments agent_common.ets passes, plus the UI test modules.
  echo === Running DeviceHubUiTest, SnapshotUiTest, WebGlAquariumUiTest and MapsUiTest on %SERIAL%
  call "%SCRIPT_DIR%run_external.bat" -s %SERIAL% --abi x86_64 --retry-strategy RETRY_ANY_FAILURE --max-testcase-run-count 3 %*
  if errorlevel 1 set "EXIT_CODE=1"
)

REM The ets_close step: CloseEmulatorTest shuts the emulator down over gRPC, which saves its
REM snapshot, and checks that it and netsimd exit. Fall back to the console if the ETS is missing.
echo === Closing %SERIAL%
if exist "%WORK_DIR%\ets\android-ets\tools\ets-tradefed.bat" (
  pushd "%REPO_ROOT%"
  call "%WORK_DIR%\ets\android-ets\tools\ets-tradefed.bat" run commandAndExit ets -m CloseEmulatorTest --suite-name ETS-CLOSE --abi x86_64 --null-device --module-arg=CloseEmulatorTest:set-option:emu_serial:%SERIAL%
  popd
  REM Tradefed's exit code is meaningless here (see run_external.bat): require the results of both
  REM invocations, the UI tests and CloseEmulatorTest, to be present and passed.
  powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%check_tradefed_results.ps1" "%WORK_DIR%\ets\android-ets\results" 2
  if errorlevel 1 set "EXIT_CODE=1"
) else (
  adb -s %SERIAL% emu kill >nul 2>&1
)
REM Give the emulator two minutes to exit, then stop whatever is left of this install.
powershell -NoProfile -Command "$end = (Get-Date).AddMinutes(2); while ((Get-Date) -lt $end -and (%EMU_PROCS%)) { Start-Sleep -Seconds 1 }; Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -like '%WORK_DIR%\emulator\*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"

REM Collect the CloseEmulatorTest results next to the ones run_external.bat already copied.
if exist "%WORK_DIR%\ets\android-ets\logs" robocopy "%WORK_DIR%\ets\android-ets\logs" "%OUT_DIR%\logs" /E >nul
if exist "%WORK_DIR%\ets\android-ets\results" robocopy "%WORK_DIR%\ets\android-ets\results" "%OUT_DIR%\results" /E >nul
rmdir /s /q "%WORK_DIR%"

REM run_local.sh is a Bazel test, so Bazel reports it to Sponge. Report this run the same way
REM (both Tradefed invocations, the emulator log and the test outputs); see report_to_sponge.bat.
REM The verdict above does not depend on this step.
echo === Reporting the results to Sponge
call "%SCRIPT_DIR%report_to_sponge.bat" "%OUT_DIR%" 2
echo Emulator log and test outputs: %OUT_DIR%
exit /b %EXIT_CODE%
