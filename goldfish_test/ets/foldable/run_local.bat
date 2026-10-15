@echo off
REM Runs the cold boot part of the embedded foldable display ETS sequence (@goldfish_test//ets/foldable:foldable)
REM locally on Windows the way run_local.sh does on gLinux and macOS (android_ets_cfg.py):
REM builds the emulator from this checkout, cold boots a Pixel Fold AVD on the same system image
REM with -qt-hide-window, runs FoldableDisplayTest through run_external.bat, and closes the
REM emulator with CloseEmulatorTest.
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..\..\..\..\..") do set "REPO_ROOT=%%~fI"
set "BAZEL=%REPO_ROOT%\prebuilts\bazel\windows-x86_64\bazel.exe"
set "ALLOWLIST=%REPO_ROOT%\hardware\generic\goldfish\emulator\libs\grpc_security\testdata\test_allow_list.json"

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

if not defined EMULATOR_PORT for /f %%P in ('powershell -NoProfile -Command "for ($p = 5554; $p -le 5682; $p += 2) { $free = $true; foreach ($q in $p, ($p + 1)) { try { $l = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, $q); $l.Start(); $l.Stop() } catch { $free = $false } }; if ($free) { $p; break } }"') do set "EMULATOR_PORT=%%P"
if not defined EMULATOR_PORT (
  echo No free emulator console port found between 5554 and 5682.
  exit /b 1
)
set "SERIAL=emulator-%EMULATOR_PORT%"

echo === Building the emulator and fetching the system image
pushd "%REPO_ROOT%"
"%BAZEL%" build -c opt @goldfish//emulator:release @goldfish_test//ets/foldable:system_image
if errorlevel 1 (
  popd
  exit /b 1
)
for /f "delims=" %%I in ('call "%BAZEL%" info execution_root 2^>nul') do set "EXEC_ROOT=%%I"
for /f "delims=" %%I in ('call "%BAZEL%" info output_base 2^>nul') do set "OUTPUT_BASE=%%I"
for /f "delims=" %%F in ('call "%BAZEL%" cquery -c opt --output=files @goldfish//emulator:release 2^>nul') do set "EMULATOR_ZIP=%EXEC_ROOT%/%%F"
for /f "delims=" %%F in ('call "%BAZEL%" cquery -c opt --output=files @goldfish_test//ets/foldable:system_image 2^>nul') do (
  set "LINE=%%F"
  if /i "!LINE:~-11!"=="/system.img" set "SYSTEM_IMG=%OUTPUT_BASE%/%%F"
)
popd
if not defined EMULATOR_ZIP (
  echo Could not locate the output of @goldfish//emulator:release with bazel cquery.
  exit /b 1
)
if not defined SYSTEM_IMG (
  echo Could not locate system.img in @goldfish_test//ets/foldable:system_image with bazel cquery.
  exit /b 1
)
set "EMULATOR_ZIP=%EMULATOR_ZIP:/=\%"
set "SYSTEM_IMG=%SYSTEM_IMG:/=\%"
for %%F in ("%SYSTEM_IMG%") do set "SYSDIR=%%~dpF"

set "WORK_DIR=%TEMP%\ets_foldable_local_%RANDOM%"
mkdir "%WORK_DIR%\avd\ets.avd"
echo === Extracting %EMULATOR_ZIP% into %WORK_DIR%
"%SystemRoot%\System32\tar.exe" -xf "%EMULATOR_ZIP%" -C "%WORK_DIR%"
if not exist "%WORK_DIR%\emulator\emulator.exe" (
  echo Could not extract the emulator.
  rmdir /s /q "%WORK_DIR%"
  exit /b 1
)

set "ANDROID_AVD_HOME=%WORK_DIR%\avd"
> "%ANDROID_AVD_HOME%\ets.ini" echo path=%ANDROID_AVD_HOME%\ets.avd
powershell -NoProfile -Command "[IO.File]::WriteAllLines('%ANDROID_AVD_HOME%\ets.avd\config.ini', @(('avd.ini.displayname=UTF8' + [char]::ConvertFromUtf32(0x1F916)), 'hw.ramSize=8192', 'hw.device.manufacturer=Google', 'hw.device.name=pixel_10_pro_fold', 'hw.lcd.width=2076', 'hw.lcd.height=2152', 'hw.lcd.density=373', 'hw.displayRegion.0.1.xOffset=0', 'hw.displayRegion.0.1.yOffset=0', 'hw.displayRegion.0.1.width=1080', 'hw.displayRegion.0.1.height=2364', 'hw.sensor.hinge=yes', 'hw.sensor.hinge.count=1', 'hw.sensor.hinge.type=1', 'hw.sensor.hinge.sub_type=1', 'hw.sensor.hinge.ranges=0-180', 'hw.sensor.hinge.defaults=180', 'hw.sensor.hinge.areas=1038-0-0-2152', 'hw.sensor.posture_list=1,2,3', 'hw.sensor.hinge_angles_posture_definitions=0-30,30-150,150-180', 'hw.sensor.hinge.fold_to_displayRegion.0.1_at_posture=1', 'hw.initialOrientation=landscape', 'hw.keyboard.lid=yes', 'image.sysdir.1=%SYSDIR%'))"

for /f %%T in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss"') do set "OUT_DIR=%REPO_ROOT%\out\ets_foldable\%%T"
mkdir "%OUT_DIR%"
set "ETS_WORK_DIR=%WORK_DIR%"
set "ETS_FOLDABLE_OUT_DIR=%OUT_DIR%"

set "EMU_PROCS=Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -like '%WORK_DIR%\emulator\*' -and ($_.Name -eq 'emulator.exe' -or $_.Name -like 'qemu-system-*') }"

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
    "settings put global animator_duration_scale 1.0"
    "am kill-all"
    "am wait-for-broadcast-barrier"
    "am wait-for-broadcast-idle"
  ) do adb -s %SERIAL% shell %%~C

  echo === Running FoldableDisplayTest on %SERIAL%
  call "%SCRIPT_DIR%run_external.bat" -s %SERIAL% --abi x86_64 --retry-strategy RETRY_ANY_FAILURE --max-testcase-run-count 3 %*
  if errorlevel 1 set "EXIT_CODE=1"
)

echo === Closing %SERIAL%
if exist "%WORK_DIR%\ets\android-ets\tools\ets-tradefed.bat" (
  pushd "%REPO_ROOT%"
  call "%WORK_DIR%\ets\android-ets\tools\ets-tradefed.bat" run commandAndExit ets -m CloseEmulatorTest --suite-name ETS-CLOSE --abi x86_64 --null-device --module-arg=CloseEmulatorTest:set-option:emu_serial:%SERIAL%
  popd
  powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%..\ui\check_tradefed_results.ps1" "%WORK_DIR%\ets\android-ets\results" 2
  if errorlevel 1 set "EXIT_CODE=1"
) else (
  adb -s %SERIAL% emu kill >nul 2>&1
)
powershell -NoProfile -Command "$end = (Get-Date).AddMinutes(2); while ((Get-Date) -lt $end -and (%EMU_PROCS%)) { Start-Sleep -Seconds 1 }; Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -like '%WORK_DIR%\emulator\*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"

if exist "%WORK_DIR%\ets\android-ets\logs" robocopy "%WORK_DIR%\ets\android-ets\logs" "%OUT_DIR%\logs" /E >nul
if exist "%WORK_DIR%\ets\android-ets\results" robocopy "%WORK_DIR%\ets\android-ets\results" "%OUT_DIR%\results" /E >nul
rmdir /s /q "%WORK_DIR%"

echo === Reporting the results to Sponge
call "%SCRIPT_DIR%..\ui\report_to_sponge.bat" "%OUT_DIR%" 2
echo Emulator log and test outputs: %OUT_DIR%
exit /b %EXIT_CODE%
